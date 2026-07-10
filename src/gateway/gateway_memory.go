// Package gateway — 分布式共享记忆层
// SPEC-DMEM-001 Phase 1: 所有 Worker 的记忆通过 Gateway 同步
//
// 端点:
//   POST /api/v1/memory/sync     — 节点上报新记忆
//   GET  /api/v1/memory/search   — 跨节点搜索记忆
//   POST /api/v1/memory/recall   — 联想检索
//   GET  /api/v1/memory/stats    — 集群记忆统计

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

// SharedEpisode 共享经验（来自各 Worker 的 SaveEpisode）
type SharedEpisode struct {
	NodeID    string    `json:"node_id"`
	Task      string    `json:"task"`
	Result    string    `json:"result"`
	Success   bool      `json:"success"`
	Learned   string    `json:"learned"`
	Timestamp time.Time `json:"timestamp"`
	Strength  float64   `json:"strength"`
}

// SharedKnowledge 共享知识（来自各 Worker 的 SaveKnowledge）
type SharedKnowledge struct {
	NodeID    string    `json:"node_id"`
	Topic     string    `json:"topic"`
	Content   string    `json:"content"`
	Author    string    `json:"author"`
	Verified  string    `json:"verified"`
	Tags      []string  `json:"tags"`
	Timestamp time.Time `json:"timestamp"`
}

// MemoryIndex 倒排索引（关键词 → 记忆列表）
type MemoryIndex struct {
	mu       sync.RWMutex
	episodes map[string][]string // keyword → []episodeKey
	knowledge map[string][]string // keyword → []knowledgeKey
}

// ClusterMemory 集群记忆单例
type ClusterMemory struct {
	mu         sync.RWMutex
	episodes   map[string]*SharedEpisode   // "nodeID:task" → episode
	knowledge  map[string]*SharedKnowledge // "topic:nodeID" → knowledge
	index      *MemoryIndex
	lastSync   map[string]time.Time // nodeID → 最后同步时间

	// 知识同步回调：当知识通过 API 写入时，同步到 Agent GitMemory
	knowledgeCallback func(topic, content string)
}

// SetKnowledgeCallback 设置知识同步回调
func (cm *ClusterMemory) SetKnowledgeCallback(fn func(topic, content string)) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.knowledgeCallback = fn
}

var clusterMem = &ClusterMemory{
	episodes:  make(map[string]*SharedEpisode),
	knowledge: make(map[string]*SharedKnowledge),
	index:     &MemoryIndex{
		episodes:  make(map[string][]string),
		knowledge: make(map[string][]string),
	},
	lastSync:  make(map[string]time.Time),
}

// ══════════════════════════════════════════════════════════════════════
// 内部方法
// ══════════════════════════════════════════════════════════════════════

// storeEpisode 存储一条共享经验
func (cm *ClusterMemory) storeEpisode(ep *SharedEpisode) {
	key := ep.NodeID + ":" + ep.Task
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// 去重：同节点同任务只保留最新
	cm.episodes[key] = ep
	cm.lastSync[ep.NodeID] = time.Now()

	// 更新倒排索引
	cm.indexEpisode(ep.Task, key)
	cm.indexEpisode(ep.Learned, key)

	// 异步持久化
	go func() {
		if err := cm.saveToFile(); err != nil {
			logWithTimestamp("⚠️ 记忆持久化失败: %v", err)
		}
	}()
}

// storeKnowledge 存储一条共享知识
func (cm *ClusterMemory) storeKnowledge(kn *SharedKnowledge) {
	key := kn.Topic + ":" + kn.NodeID
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cm.knowledge[key] = kn
	cm.lastSync[kn.NodeID] = time.Now()

	// 更新倒排索引
	cm.indexKnowledge(kn.Topic, key)
	for _, tag := range kn.Tags {
		cm.indexKnowledge(tag, key)
	}

	// 同步到 Agent GitMemory（如果有回调）
	if cm.knowledgeCallback != nil {
		cm.knowledgeCallback(kn.Topic, kn.Content)
	}

	// 同步到 KnowledgeStore API（保证 knowledge/query 能查到）
	globalKnowledgeStore.put(&KnowledgeEntry{
		ID:         fmt.Sprintf("kn-cluster-%s-%s", kn.NodeID, kn.Topic),
		Title:      kn.Topic,
		Content:    kn.Content,
		Type:       "lesson",
		Source:     kn.NodeID,
		Tags:       kn.Tags,
		Confidence: 0.8,
		TTLDays:    30,
		Timestamp:  kn.Timestamp.Format(time.RFC3339),
	})

	// 持久化（异步，批量写入时避免阻塞 Gateway）
	go func() {
		if err := cm.saveToFile(); err != nil {
			logWithTimestamp("⚠️ 记忆持久化失败: %v", err)
		}
	}()
}

// indexEpisode 为 episode 建立倒排索引
func (cm *ClusterMemory) indexEpisode(text, key string) {
	words := tokenize(text)
	for _, w := range words {
		cm.index.episodes[w] = append(cm.index.episodes[w], key)
	}
}

// indexKnowledge 为 knowledge 建立倒排索引
func (cm *ClusterMemory) indexKnowledge(text, key string) {
	words := tokenize(text)
	for _, w := range words {
		cm.index.knowledge[w] = append(cm.index.knowledge[w], key)
	}
}

// searchEpisodes 搜索共享经验
func (cm *ClusterMemory) searchEpisodes(query string, limit int) []*SharedEpisode {
	if limit <= 0 {
		limit = 10
	}

	cm.mu.RLock()
	defer cm.mu.RUnlock()

	words := tokenize(query)
	scored := make(map[string]float64)

	for _, w := range words {
		if keys, ok := cm.index.episodes[w]; ok {
			for _, k := range keys {
				scored[k]++
			}
		}
	}

	// 按分数排序
	type scoredKey struct {
		key   string
		score float64
	}
	var sorted []scoredKey
	for k, s := range scored {
		sorted = append(sorted, scoredKey{k, s})
	}
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].score > sorted[j].score
	})

	var results []*SharedEpisode
	for _, sk := range sorted {
		if len(results) >= limit {
			break
		}
		if ep, ok := cm.episodes[sk.key]; ok {
			results = append(results, ep)
		}
	}

	return results
}

// searchKnowledge 搜索共享知识
func (cm *ClusterMemory) searchKnowledge(query string, limit int) []*SharedKnowledge {
	if limit <= 0 {
		limit = 10
	}

	cm.mu.RLock()
	defer cm.mu.RUnlock()

	words := tokenize(query)
	scored := make(map[string]float64)

	for _, w := range words {
		if keys, ok := cm.index.knowledge[w]; ok {
			for _, k := range keys {
				scored[k]++
			}
		}
	}

	type scoredKey struct {
		key   string
		score float64
	}
	var sorted []scoredKey
	for k, s := range scored {
		sorted = append(sorted, scoredKey{k, s})
	}
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].score > sorted[j].score
	})

	var results []*SharedKnowledge
	for _, sk := range sorted {
		if len(results) >= limit {
			break
		}
		if kn, ok := cm.knowledge[sk.key]; ok {
			results = append(results, kn)
		}
	}

	return results
}

// getStats 获取集群记忆统计
func (cm *ClusterMemory) getStats() map[string]interface{} {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	nodeCount := len(cm.lastSync)
	var totalEpisodes, totalKnowledge int
	for range cm.episodes {
		totalEpisodes++
	}
	for range cm.knowledge {
		totalKnowledge++
	}

	// 各节点最后同步时间
	nodeSync := make(map[string]string)
	for nid, t := range cm.lastSync {
		nodeSync[nid] = t.Format("15:04:05")
	}

	return map[string]interface{}{
		"nodes":          nodeCount,
		"episodes":       totalEpisodes,
		"knowledge":      totalKnowledge,
		"node_sync":      nodeSync,
		"index_episodes": len(cm.index.episodes),
		"index_knowledge": len(cm.index.knowledge),
	}
}

// tokenize 简单分词（支持中文）
// 英文按空格/标点分割，中文按字符分割（2-gram 提高召回率）
func tokenize(s string) []string {
	s = strings.ToLower(s)
	seen := make(map[string]bool)
	var result []string

	// 先按空格和标点分割（处理英文和混合文本）
	parts := strings.FieldsFunc(s, func(r rune) bool {
		return r == ' ' || r == ',' || r == '.' || r == '!' || r == '?' ||
			r == '，' || r == '。' || r == '！' || r == '？' ||
			r == '、' || r == '：' || r == '；' || r == '\n' || r == '\t' ||
			r == '(' || r == ')' || r == '[' || r == ']' || r == '"' || r == '\''
	})

	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		// 判断是否包含中文
		hasChinese := false
		for _, r := range part {
			if r >= 0x4E00 && r <= 0x9FFF {
				hasChinese = true
				break
			}
		}

		if hasChinese {
			// 中文文本：按字符分割，生成 2-gram
			runes := []rune(part)
			// 单个字符也作为索引
			for _, r := range runes {
				w := string(r)
				if !seen[w] && len(w) > 0 {
					seen[w] = true
					result = append(result, w)
				}
			}
			// 2-gram
			for i := 0; i < len(runes)-1; i++ {
				w := string(runes[i]) + string(runes[i+1])
				if !seen[w] {
					seen[w] = true
					result = append(result, w)
				}
			}
		} else {
			// 英文文本：直接作为 token
			if !seen[part] && len(part) > 1 {
				seen[part] = true
				result = append(result, part)
			}
		}
	}

	return result
}

// ══════════════════════════════════════════════════════════════════════
// 持久化
// ══════════════════════════════════════════════════════════════════════

// memoryFilePath 持久化文件路径
var memoryFilePath = ""

// SetMemoryFilePath 设置持久化文件路径
func SetMemoryFilePath(path string) {
	memoryFilePath = path
}

// memoryData 持久化数据结构
type memoryData struct {
	Episodes  map[string]*SharedEpisode   `json:"episodes"`
	Knowledge map[string]*SharedKnowledge `json:"knowledge"`
	LastSync  map[string]time.Time        `json:"last_sync"`
}

// saveToFile 将共享记忆持久化到文件
func (cm *ClusterMemory) saveToFile() error {
	if memoryFilePath == "" {
		return nil
	}

	cm.mu.RLock()
	data := &memoryData{
		Episodes:  cm.episodes,
		Knowledge: cm.knowledge,
		LastSync:  cm.lastSync,
	}
	cm.mu.RUnlock()

	// 确保目录存在
	dir := filepath.Dir(memoryFilePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("create memory dir: %w", err)
	}

	body, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal memory: %w", err)
	}

	if err := os.WriteFile(memoryFilePath, body, 0644); err != nil {
		return fmt.Errorf("write memory file: %w", err)
	}

	return nil
}

// loadFromFile 从文件加载共享记忆
func (cm *ClusterMemory) loadFromFile() error {
	if memoryFilePath == "" {
		return nil
	}

	body, err := os.ReadFile(memoryFilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil // 首次启动，文件不存在
		}
		return fmt.Errorf("read memory file: %w", err)
	}

	var data memoryData
	if err := json.Unmarshal(body, &data); err != nil {
		return fmt.Errorf("unmarshal memory: %w", err)
	}

	cm.mu.Lock()
	defer cm.mu.Unlock()

	cm.episodes = data.Episodes
	if cm.episodes == nil {
		cm.episodes = make(map[string]*SharedEpisode)
	}
	cm.knowledge = data.Knowledge
	if cm.knowledge == nil {
		cm.knowledge = make(map[string]*SharedKnowledge)
	}
	cm.lastSync = data.LastSync
	if cm.lastSync == nil {
		cm.lastSync = make(map[string]time.Time)
	}

	// 重建倒排索引
	cm.index.episodes = make(map[string][]string)
	cm.index.knowledge = make(map[string][]string)
	for key, ep := range cm.episodes {
		cm.indexEpisode(ep.Task, key)
		cm.indexEpisode(ep.Learned, key)
	}
	for key, kn := range cm.knowledge {
		cm.indexKnowledge(kn.Topic, key)
		for _, tag := range kn.Tags {
			cm.indexKnowledge(tag, key)
		}
	}

	logWithTimestamp("🧠 共享记忆已加载: episodes=%d, knowledge=%d, index_ep=%d, index_kn=%d",
		len(cm.episodes), len(cm.knowledge), len(cm.index.episodes), len(cm.index.knowledge))
	return nil
}

// ══════════════════════════════════════════════════════════════════════
// HTTP Handlers
// ══════════════════════════════════════════════════════════════════════

// handleMemorySync — POST /api/v1/memory/sync
// Worker 上报新记忆
func (g *OpcGateway) handleMemorySync(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeJSON(w, Response{Success: false, Error: "read body: " + err.Error()})
		return
	}

	var req struct {
		NodeID    string            `json:"node_id"`
		Episodes  []*SharedEpisode  `json:"episodes,omitempty"`
		Knowledge []*SharedKnowledge `json:"knowledge,omitempty"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}

	if req.NodeID == "" {
		writeJSON(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	// 存储经验
	epCount := 0
	for _, ep := range req.Episodes {
		if ep.Task == "" {
			continue
		}
		ep.NodeID = req.NodeID
		if ep.Timestamp.IsZero() {
			ep.Timestamp = time.Now()
		}
		if ep.Strength <= 0 {
			ep.Strength = 1.0
		}
		clusterMem.storeEpisode(ep)
		epCount++
	}

	// 存储知识
	knCount := 0
	for _, kn := range req.Knowledge {
		if kn.Topic == "" {
			continue
		}
		kn.NodeID = req.NodeID
		if kn.Timestamp.IsZero() {
			kn.Timestamp = time.Now()
		}
		clusterMem.storeKnowledge(kn)
		knCount++
	}

	logWithTimestamp("🧠 记忆同步: node=%s, episodes=%d, knowledge=%d", req.NodeID, epCount, knCount)

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"episodes_synced":  epCount,
			"knowledge_synced": knCount,
		},
	})
}

// handleMemorySearch — GET /api/v1/memory/search
// 跨节点搜索记忆
func (g *OpcGateway) handleMemorySearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, Response{Success: false, Error: "GET required"})
		return
	}

	query := r.URL.Query().Get("q")
	if query == "" {
		writeJSON(w, Response{Success: false, Error: "q (query) is required"})
		return
	}

	limit := 10
	if l := r.URL.Query().Get("limit"); l != "" {
		fmt.Sscanf(l, "%d", &limit)
	}

	typeStr := r.URL.Query().Get("type") // "episode", "knowledge", "all"

	var episodes []*SharedEpisode
	var knowledge []*SharedKnowledge

	if typeStr == "" || typeStr == "all" || typeStr == "episode" {
		episodes = clusterMem.searchEpisodes(query, limit)
	}
	if typeStr == "" || typeStr == "all" || typeStr == "knowledge" {
		knowledge = clusterMem.searchKnowledge(query, limit)
	}

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"query":     query,
			"episodes":  episodes,
			"knowledge": knowledge,
			"ep_count":  len(episodes),
			"kn_count":  len(knowledge),
		},
	})
}

// handleMemoryRecall — POST /api/v1/memory/recall
// 联想检索（含关联扩展）
func (g *OpcGateway) handleMemoryRecall(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Query     string   `json:"query"`
		Tags      []string `json:"tags,omitempty"`
		Limit     int      `json:"limit,omitempty"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}

	if req.Query == "" {
		writeJSON(w, Response{Success: false, Error: "query is required"})
		return
	}
	if req.Limit <= 0 {
		req.Limit = 10
	}

	episodes := clusterMem.searchEpisodes(req.Query, req.Limit)
	knowledge := clusterMem.searchKnowledge(req.Query, req.Limit)

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"query":     req.Query,
			"episodes":  episodes,
			"knowledge": knowledge,
			"ep_count":  len(episodes),
			"kn_count":  len(knowledge),
		},
	})
}

// handleMemoryStats — GET /api/v1/memory/stats
// 集群记忆统计
func (g *OpcGateway) handleMemoryStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, Response{Success: false, Error: "GET required"})
		return
	}

	stats := clusterMem.getStats()
	writeJSON(w, Response{
		Success: true,
		Data:    stats,
	})
}

// handleMemoryList — GET /api/v1/memory/list
// 列出所有记忆（分页）
func (g *OpcGateway) handleMemoryList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, Response{Success: false, Error: "GET required"})
		return
	}

	page := 1
	pageSize := 50
	nodeFilter := r.URL.Query().Get("node_id")
	if p := r.URL.Query().Get("page"); p != "" {
		fmt.Sscanf(p, "%d", &page)
	}
	if ps := r.URL.Query().Get("page_size"); ps != "" {
		fmt.Sscanf(ps, "%d", &pageSize)
	}
	if pageSize <= 0 || pageSize > 200 {
		pageSize = 50
	}
	if page <= 0 {
		page = 1
	}

	clusterMem.mu.RLock()
	defer clusterMem.mu.RUnlock()

	// 收集所有 episodes（支持 node_id 过滤）
	var allEpisodes []*SharedEpisode
	for _, ep := range clusterMem.episodes {
		if nodeFilter != "" && ep.NodeID != nodeFilter {
			continue
		}
		allEpisodes = append(allEpisodes, ep)
	}
	// 按时间倒序
	sort.Slice(allEpisodes, func(i, j int) bool {
		return allEpisodes[i].Timestamp.After(allEpisodes[j].Timestamp)
	})

	// 收集所有 knowledge（支持 node_id 过滤）
	var allKnowledge []*SharedKnowledge
	for _, kn := range clusterMem.knowledge {
		if nodeFilter != "" && kn.NodeID != nodeFilter {
			continue
		}
		allKnowledge = append(allKnowledge, kn)
	}
	sort.Slice(allKnowledge, func(i, j int) bool {
		return allKnowledge[i].Timestamp.After(allKnowledge[j].Timestamp)
	})

	// 分页
	totalEp := len(allEpisodes)
	totalKn := len(allKnowledge)
	start := (page - 1) * pageSize
	end := start + pageSize
	if start > totalEp {
		start = totalEp
	}
	if end > totalEp {
		end = totalEp
	}
	var pageEpisodes []*SharedEpisode
	if start < totalEp {
		pageEpisodes = allEpisodes[start:end]
	}

	start2 := (page - 1) * pageSize
	end2 := start2 + pageSize
	if start2 > totalKn {
		start2 = totalKn
	}
	if end2 > totalKn {
		end2 = totalKn
	}
	var pageKnowledge []*SharedKnowledge
	if start2 < totalKn {
		pageKnowledge = allKnowledge[start2:end2]
	}

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"episodes":  pageEpisodes,
			"knowledge": pageKnowledge,
			"total_ep":  totalEp,
			"total_kn":  totalKn,
			"page":      page,
			"page_size": pageSize,
			"total_pages_ep": (totalEp + pageSize - 1) / pageSize,
			"total_pages_kn": (totalKn + pageSize - 1) / pageSize,
		},
	})
}

// handleMemoryDelete — POST /api/v1/memory/delete
// 删除一条记忆
func (g *OpcGateway) handleMemoryDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Type  string `json:"type"`  // "episode" or "knowledge"
		Key   string `json:"key"`   // "nodeID:task" or "topic:nodeID"
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.Type == "" || req.Key == "" {
		writeJSON(w, Response{Success: false, Error: "type and key required"})
		return
	}

	clusterMem.mu.Lock()
	defer clusterMem.mu.Unlock()

	if req.Type == "episode" {
		delete(clusterMem.episodes, req.Key)
	} else if req.Type == "knowledge" {
		delete(clusterMem.knowledge, req.Key)
	} else {
		writeJSON(w, Response{Success: false, Error: "type must be 'episode' or 'knowledge'"})
		return
	}

	// 持久化
	go func() {
		if err := clusterMem.saveToFile(); err != nil {
			logWithTimestamp("⚠️ 记忆持久化失败: %v", err)
		}
	}()

	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"deleted": req.Type,
		"key":     req.Key,
	}})
}

// handleMemoryTags — GET /api/v1/memory/tags
// 获取所有标签/话题统计
func (g *OpcGateway) handleMemoryTags(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, Response{Success: false, Error: "GET required"})
		return
	}

	clusterMem.mu.RLock()
	defer clusterMem.mu.RUnlock()

	tagCount := make(map[string]int)
	topicCount := make(map[string]int)
	nodeCount := make(map[string]int)

	for _, ep := range clusterMem.episodes {
		nodeCount[ep.NodeID]++
	}
	for _, kn := range clusterMem.knowledge {
		topicCount[kn.Topic]++
		nodeCount[kn.NodeID]++
		for _, tag := range kn.Tags {
			tagCount[tag]++
		}
	}

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"tags":   tagCount,
			"topics": topicCount,
			"nodes":  nodeCount,
		},
	})
}

// handleMemoryPage — GET /memory
// 独立记忆管理页面
func (g *OpcGateway) handleMemoryPage(w http.ResponseWriter, r *http.Request) {
	webDir := filepath.Join(filepath.Dir(os.Args[0]), "..", "web")
	if _, err := os.Stat(webDir); os.IsNotExist(err) {
		// 回退: 用 /proc/self/exe 获取真实路径
		if exe, err := os.Readlink("/proc/self/exe"); err == nil {
			webDir = filepath.Join(filepath.Dir(exe), "..", "web")
		}
	}
	if _, err := os.Stat(webDir); os.IsNotExist(err) {
		webDir = "web"
	}
	htmlPath := filepath.Join(webDir, "memory.html")

	html, err := os.ReadFile(htmlPath)
	if err != nil {
		http.Error(w, "⚠️ 页面文件未找到: "+htmlPath, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(html)
}
