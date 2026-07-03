// Package gateway — 知识共享 API (KSP-001)
// 三智知识共享协议 v1.0 实现
//
// 端点:
//   POST /api/v1/knowledge/put    — 写入知识
//   GET  /api/v1/knowledge/query  — 查询知识
//   POST /api/v1/knowledge/sync   — 同步知识
//   GET  /api/v1/knowledge/stats  — 知识库统计

package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// ══════════════════════════════════════════════════════════════════════
// 数据结构
// ══════════════════════════════════════════════════════════════════════

// KnowledgeEntry 知识条目（KSP-001 格式）
type KnowledgeEntry struct {
	ID         string   `json:"id"`
	Source     string   `json:"source"`
	Type       string   `json:"type"`       // skill / pattern / lesson / insight
	Title      string   `json:"title"`
	Content    string   `json:"content"`
	Tags       []string `json:"tags"`
	Confidence float64  `json:"confidence"`
	TTLDays    int      `json:"ttl_days"`
	Timestamp  string   `json:"timestamp"`
	TraceID    string   `json:"trace_id,omitempty"`
}

// KnowledgeStore 知识库存储
type KnowledgeStore struct {
	mu       sync.RWMutex
	entries  map[string]*KnowledgeEntry // key: id
	bySource map[string][]string        // source → []id
	byType   map[string][]string        // type → []id
	byTag    map[string][]string        // tag → []id
}

var globalKnowledgeStore = &KnowledgeStore{
	entries:  make(map[string]*KnowledgeEntry),
	bySource: make(map[string][]string),
	byType:   make(map[string][]string),
	byTag:    make(map[string][]string),
}

// knowledgeDataDir 知识库持久化目录
var knowledgeDataDir = ""

// SetKnowledgeDataDir 设置知识库持久化目录
func SetKnowledgeDataDir(dir string) {
	knowledgeDataDir = dir
}

// ══════════════════════════════════════════════════════════════════════
// 内部方法
// ══════════════════════════════════════════════════════════════════════

// put 写入一条知识
func (ks *KnowledgeStore) put(entry *KnowledgeEntry) (string, error) {
	if entry.ID == "" {
		entry.ID = fmt.Sprintf("kn-%d-%d", time.Now().UnixNano(), len(ks.entries))
	}
	if entry.Timestamp == "" {
		entry.Timestamp = time.Now().Format(time.RFC3339)
	}
	if entry.Confidence <= 0 {
		entry.Confidence = 0.8
	}
	if entry.TTLDays <= 0 {
		entry.TTLDays = 30
	}

	ks.mu.Lock()
	defer ks.mu.Unlock()

	// 去重：同 ID 已存在则跳过
	if existing, ok := ks.entries[entry.ID]; ok {
		// 时间戳优先（LWW）
		existingTime, _ := time.Parse(time.RFC3339, existing.Timestamp)
		newTime, _ := time.Parse(time.RFC3339, entry.Timestamp)
		if !newTime.After(existingTime) {
			return entry.ID, nil // 旧版本，跳过
		}
	}

	ks.entries[entry.ID] = entry

	// 更新索引
	ks.bySource[entry.Source] = append(ks.bySource[entry.Source], entry.ID)
	ks.byType[entry.Type] = append(ks.byType[entry.Type], entry.ID)
	for _, tag := range entry.Tags {
		tag = strings.ToLower(strings.TrimSpace(tag))
		if tag != "" {
			ks.byTag[tag] = append(ks.byTag[tag], entry.ID)
		}
	}

	// 持久化到文件
	go ks.persist(entry)

	return entry.ID, nil
}

// query 查询知识
func (ks *KnowledgeStore) query(q, typeFilter string, tags []string, limit int) []*KnowledgeEntry {
	if limit <= 0 {
		limit = 20
	}

	ks.mu.RLock()
	defer ks.mu.RUnlock()

	// 收集匹配的 ID
	idSet := make(map[string]bool)

	// 按类型过滤
	var candidates []string
	if typeFilter != "" {
		candidates = ks.byType[typeFilter]
	} else {
		for _, ids := range ks.byType {
			candidates = append(candidates, ids...)
		}
	}

	// 按标签过滤
	for _, id := range candidates {
		entry, ok := ks.entries[id]
		if !ok {
			continue
		}

		// 标签匹配
		if len(tags) > 0 {
			tagMatch := false
			for _, tag := range tags {
				tag = strings.ToLower(strings.TrimSpace(tag))
				for _, et := range entry.Tags {
					if strings.ToLower(strings.TrimSpace(et)) == tag {
						tagMatch = true
						break
					}
				}
				if tagMatch {
					break
				}
			}
			if !tagMatch {
				continue
			}
		}

		// 关键词匹配
		if q != "" {
			lowerQ := strings.ToLower(q)
			if !strings.Contains(strings.ToLower(entry.Title), lowerQ) &&
				!strings.Contains(strings.ToLower(entry.Content), lowerQ) {
				continue
			}
		}

		idSet[id] = true
	}

	// 按时间倒序
	var sorted []*KnowledgeEntry
	for id := range idSet {
		if entry, ok := ks.entries[id]; ok {
			sorted = append(sorted, entry)
		}
	}
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Timestamp > sorted[j].Timestamp
	})

	if len(sorted) > limit {
		sorted = sorted[:limit]
	}

	return sorted
}

// sync 获取指定节点的新知识
func (ks *KnowledgeStore) sync(source string, since time.Time) (newCount, updatedCount int) {
	ks.mu.RLock()
	defer ks.mu.RUnlock()

	for _, entry := range ks.entries {
		if entry.Source != source {
			continue
		}
		t, err := time.Parse(time.RFC3339, entry.Timestamp)
		if err != nil {
			continue
		}
		if t.After(since) {
			newCount++
		}
	}

	return newCount, 0
}

// persist 持久化一条知识到文件
func (ks *KnowledgeStore) persist(entry *KnowledgeEntry) {
	if knowledgeDataDir == "" {
		return
	}

	// 按类型分目录
	dir := filepath.Join(knowledgeDataDir, "knowledge", entry.Type)
	if err := os.MkdirAll(dir, 0755); err != nil {
		logWithTimestamp("⚠️ 知识持久化目录创建失败: %v", err)
		return
	}

	// 文件名：slug.md
	slug := slugify(entry.Title)
	if len(slug) > 60 {
		slug = slug[:60]
	}
	path := filepath.Join(dir, slug+".md")

	// 写入 Markdown
	content := fmt.Sprintf(`# Knowledge: %s
> Type: %s
> Source: %s
> Confidence: %.1f
> TTL: %d days
> Tags: %s
> Timestamp: %s

## Content

%s
`, entry.Title, entry.Type, entry.Source, entry.Confidence, entry.TTLDays,
		strings.Join(entry.Tags, ", "), entry.Timestamp, entry.Content)

	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		logWithTimestamp("⚠️ 知识持久化写入失败: %v", err)
	}
}

// slugify 生成 URL 友好的文件名
// load 从持久化文件加载知识到内存
// 文件结构: {knowledgeDataDir}/knowledge/{type}/{slug}.md
func (ks *KnowledgeStore) load(dir string) int {
	if dir == "" {
		return 0
	}
	loaded := 0
	// 知识文件目录: dir/knowledge/{type}/*.md
	knowledgeDir := filepath.Join(dir, "knowledge")
	typeEntries, err := os.ReadDir(knowledgeDir)
	if err != nil {
		logWithTimestamp("⚠️ 知识持久化目录读取失败: %v", err)
		return 0
	}
	for _, typeEntry := range typeEntries {
		if !typeEntry.IsDir() {
			continue
		}
		typeDir := filepath.Join(knowledgeDir, typeEntry.Name())
		files, err := os.ReadDir(typeDir)
		if err != nil {
			continue
		}
		for _, f := range files {
			if f.IsDir() || !strings.HasSuffix(f.Name(), ".md") {
				continue
			}
			fpath := filepath.Join(typeDir, f.Name())
			data, err := os.ReadFile(fpath)
			if err != nil {
				continue
			}
			text := string(data)
			kn := &KnowledgeEntry{Type: typeEntry.Name()}
			for _, line := range strings.Split(text, "\n") {
				if strings.HasPrefix(line, "# Knowledge: ") {
					kn.Title = strings.TrimPrefix(line, "# Knowledge: ")
				} else if strings.HasPrefix(line, "> Type: ") {
					kn.Type = strings.TrimPrefix(line, "> Type: ")
				} else if strings.HasPrefix(line, "> Source: ") {
					kn.Source = strings.TrimPrefix(line, "> Source: ")
				} else if strings.HasPrefix(line, "> Tags: ") {
					t := strings.TrimPrefix(line, "> Tags: ")
					if t != "" {
						kn.Tags = strings.Split(t, ", ")
					}
				} else if strings.HasPrefix(line, "> Timestamp: ") {
					kn.Timestamp = strings.TrimPrefix(line, "> Timestamp: ")
				} else if strings.HasPrefix(line, "> Confidence: ") {
					fmt.Sscanf(strings.TrimPrefix(line, "> Confidence: "), "%f", &kn.Confidence)
				}
			}
			if idx := strings.Index(text, "## Content\n\n"); idx >= 0 {
				kn.Content = strings.TrimSpace(text[idx+12:])
			}
			if kn.Content == "" {
				kn.Content = text
			}
			if kn.ID == "" {
				kn.ID = fmt.Sprintf("kn-loaded-%d", loaded)
			}
			ks.put(kn)
			loaded++
		}
	}
	logWithTimestamp("📚 知识库加载完成: %d 条", loaded)
	return loaded
}

func slugify(s string) string {
	var result strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' || r == '_' {
			result.WriteRune(r)
		} else if r == ' ' || r == '　' {
			result.WriteRune('-')
		} else if r >= 0x4E00 && r <= 0x9FFF {
			// 保留中文字符
			result.WriteRune(r)
		}
	}
	return result.String()
}

// ══════════════════════════════════════════════════════════════════════
// HTTP Handlers
// ══════════════════════════════════════════════════════════════════════

// handleKnowledgePut — POST /api/v1/knowledge/put
func (g *OpcGateway) handleKnowledgePut(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeJSON(w, Response{Success: false, Error: "read body: " + err.Error()})
		return
	}

	var entry KnowledgeEntry
	if err := json.Unmarshal(body, &entry); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}

	if entry.Title == "" || entry.Content == "" {
		writeJSON(w, Response{Success: false, Error: "title and content are required"})
		return
	}
	if entry.Type == "" {
		entry.Type = "lesson"
	}

	id, err := globalKnowledgeStore.put(&entry)
	if err != nil {
		writeJSON(w, Response{Success: false, Error: err.Error()})
		return
	}

	// 同步到 ClusterMemory
	clusterMem.storeKnowledge(&SharedKnowledge{
		NodeID:  entry.Source,
		Topic:   entry.Title,
		Content: entry.Content,
		Author:  entry.Source,
		Tags:    entry.Tags,
		Timestamp: time.Now(),
	})

	logWithTimestamp("📚 知识写入: id=%s, type=%s, title=%s, source=%s", id, entry.Type, entry.Title[:min(len(entry.Title), 40)], entry.Source)

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"id":   id,
			"path": fmt.Sprintf("shared/knowledge/%s/%s.md", entry.Type, slugify(entry.Title)),
		},
	})
}

// handleKnowledgeQuery — GET /api/v1/knowledge/query
func (g *OpcGateway) handleKnowledgeQuery(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, Response{Success: false, Error: "GET required"})
		return
	}

	q := r.URL.Query().Get("q")
	typeFilter := r.URL.Query().Get("type")
	tagsStr := r.URL.Query().Get("tags")
	limit := 20
	if l := r.URL.Query().Get("limit"); l != "" {
		fmt.Sscanf(l, "%d", &limit)
	}

	var tags []string
	if tagsStr != "" {
		tags = strings.Split(tagsStr, ",")
	}

	results := globalKnowledgeStore.query(q, typeFilter, tags, limit)

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"results": results,
			"total":   len(results),
		},
	})
}

// handleKnowledgeSync — POST /api/v1/knowledge/sync
func (g *OpcGateway) handleKnowledgeSync(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Source string `json:"source"`
		Since  string `json:"since"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}

	if req.Source == "" {
		writeJSON(w, Response{Success: false, Error: "source is required"})
		return
	}

	since := time.Now().Add(-24 * time.Hour)
	if req.Since != "" {
		if t, err := time.Parse(time.RFC3339, req.Since); err == nil {
			since = t
		}
	}

	newCount, updatedCount := globalKnowledgeStore.sync(req.Source, since)

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"new":     newCount,
			"updated": updatedCount,
			"deleted": 0,
		},
	})
}

// handleKnowledgeStats — GET /api/v1/knowledge/stats
func (g *OpcGateway) handleKnowledgeStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, Response{Success: false, Error: "GET required"})
		return
	}

	globalKnowledgeStore.mu.RLock()
	defer globalKnowledgeStore.mu.RUnlock()

	typeCount := make(map[string]int)
	sourceCount := make(map[string]int)
	tagCount := make(map[string]int)

	for _, entry := range globalKnowledgeStore.entries {
		typeCount[entry.Type]++
		sourceCount[entry.Source]++
		for _, tag := range entry.Tags {
			tag = strings.ToLower(strings.TrimSpace(tag))
			if tag != "" {
				tagCount[tag]++
			}
		}
	}

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"total":   len(globalKnowledgeStore.entries),
			"by_type": typeCount,
			"by_source": sourceCount,
			"by_tag":  tagCount,
		},
	})
}
