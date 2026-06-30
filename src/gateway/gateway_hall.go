// Package gateway — 智能体大厅（AI Hall）
// 多 Agent 共享讨论板：Agent 们在此"看到彼此"，自动讨论同一话题
//
// ARC-AI-NET-003 协议 — 群聊模式
//   topic: 讨论话题（如 "四智群聊")
//   to: "all"（全体）或具体 node_id（私聊）
//   from: 发言者 node_id
//   content: 消息内容

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

// ── 持久化 ──
var hallDataFile = "hall_data.json" // 会被 InitHallData 解析为绝对路径

// join 去重：同一节点 60s 内重复 join 不显示
var (
	joinDedupMu    sync.RWMutex
	lastJoinTime   = make(map[string]time.Time)
	joinCooldown   = 300 * time.Second
)

func shouldSkipJoin(nodeID string) bool {
	joinDedupMu.RLock()
	last, exists := lastJoinTime[nodeID]
	joinDedupMu.RUnlock()
	if exists && time.Since(last) < joinCooldown {
		return true
	}
	joinDedupMu.Lock()
	lastJoinTime[nodeID] = time.Now()
	joinDedupMu.Unlock()
	return false
}

func clearStaleJoins() {
	joinDedupMu.Lock()
	defer joinDedupMu.Unlock()
	for id, t := range lastJoinTime {
		if time.Since(t) > joinCooldown*2 {
			delete(lastJoinTime, id)
		}
	}
}

// Agent 自动回复用
// attachments: 本条消息的附件（如果有）
var hallOnNewMessage func(topic, from, to, content string, attachments []Attachment)

// SetHallOnNewMessage 注册新消息回调（Gateway 启动时由 Agent 注册）
func SetHallOnNewMessage(cb func(topic, from, to, content string, attachments []Attachment)) {
	hallOnNewMessage = cb
}

func InitHallData(binaryDir string) {
	if binaryDir != "" {
		hallDataFile = filepath.Join(binaryDir, "hall_data.json")
	} else {
		exe, err := os.Executable()
		if err == nil {
			hallDataFile = filepath.Join(filepath.Dir(exe), "hall_data.json")
		}
	}
	loadHallData()
}

// HallData 持久化结构
type HallData struct {
	Messages []HallMessage              `json:"messages"`
	Topics   map[string]int64           `json:"topics"`
	NextSeq  int64                      `json:"next_seq"`
	Pinned   map[string][]string        `json:"pinned,omitempty"`
}

func saveHallData() {
	hall.mu.RLock()
	defer hall.mu.RUnlock()
	
	data := HallData{
		Messages: hall.messages,
		Topics:   hall.topics,
		NextSeq:  hall.nextSeq,
		Pinned:   hall.pinned,
	}
	
	// 只保留最后 500 条（与内存限制一致）
	if len(data.Messages) > 500 {
		data.Messages = data.Messages[len(data.Messages)-500:]
	}
	
	b, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		fmt.Printf("[Hall] ⚠️ save failed: %v\n", err)
		return
	}
	
	if err := os.WriteFile(hallDataFile, b, 0644); err != nil {
		fmt.Printf("[Hall] ⚠️ write failed: %v\n", err)
	}
}

func loadHallData() {
	b, err := os.ReadFile(hallDataFile)
	if err != nil {
		fmt.Printf("[Hall] 📂 no existing data (%v), starting fresh\n", err)
		return
	}
	
	var data HallData
	if err := json.Unmarshal(b, &data); err != nil {
		fmt.Printf("[Hall] ⚠️ corrupt data file: %v\n", err)
		return
	}
	
	hall.mu.Lock()
	defer hall.mu.Unlock()
	
	hall.messages = data.Messages
	if hall.messages == nil {
		hall.messages = make([]HallMessage, 0, 100)
	}
	hall.topics = data.Topics
	if hall.topics == nil {
		hall.topics = make(map[string]int64)
	}
	hall.nextSeq = data.NextSeq
	hall.pinned = data.Pinned
	if hall.pinned == nil {
		hall.pinned = make(map[string][]string)
	}
	
	fmt.Printf("[Hall] 📂 loaded %d messages from %s\n", len(data.Messages), hallDataFile)
}

// Attachment 消息附件
type Attachment struct {
	Name string `json:"name"` // 文件名
	URL  string `json:"url"`  // 下载链接
	Size int64  `json:"size"` // 文件大小（字节）
	Type string `json:"type"` // MIME 类型
}

// Reaction 消息反应（表情回复）
type Reaction struct {
	Emoji   string    `json:"emoji"`
	UserID  string    `json:"user_id"`
	Time    time.Time `json:"time"`
}

// HallMessage 大厅消息
type HallMessage struct {
	MsgID       string       `json:"msg_id"`
	Topic       string       `json:"topic"`
	From        string       `json:"from"`
	FromName    string       `json:"from_name"`
	To          string       `json:"to"`       // "all" 或具体 node_id
	Content     string       `json:"content"`
	Attachments []Attachment `json:"attachments,omitempty"` // 文件附件
	Reactions   []Reaction   `json:"reactions,omitempty"`   // 表情反应
	ReplyTo     string       `json:"reply_to,omitempty"`    // 回复的目标 msg_id
	Edited      bool         `json:"edited,omitempty"`      // 是否被编辑过
	Pinned      bool         `json:"pinned,omitempty"`       // 是否被置顶
	Timestamp   time.Time    `json:"timestamp"`
	Seq         int64        `json:"seq"`      // 话题内的序号
}

// HallState 大厅状态（单例）
type HallState struct {
	mu       sync.RWMutex
	messages []HallMessage
	topics   map[string]int64 // topic → 最新 seq
	nextSeq  int64
	pinned   map[string][]string // topic → pinned msg_ids
	typing   map[string]map[string]time.Time // topic → userID → lastTyping
	online   map[string]time.Time // userID → lastSeen
}

// TypingInfo 正在输入状态
type TypingInfo struct {
	Topic  string `json:"topic"`
	UserID string `json:"user_id"`
	Name   string `json:"name"`
}

var hall = &HallState{
	messages: make([]HallMessage, 0, 100),
	topics:   make(map[string]int64),
	pinned:   make(map[string][]string),
	typing:   make(map[string]map[string]time.Time),
	online:   make(map[string]time.Time),
}

// PostHallMessage 发送一条大厅消息
// 支持可选参数：replyTo (回复目标 msg_id)
func PostHallMessage(topic, from, fromName, to, content string, attachments ...Attachment) HallMessage {
	return PostHallMessageEx(topic, from, fromName, to, content, "", attachments...)
}

// PostHallMessageEx 发送一条大厅消息（扩展版，支持 replyTo）
func PostHallMessageEx(topic, from, fromName, to, content, replyTo string, attachments ...Attachment) HallMessage {
	// 去重：join 消息 60s 内重复不记录
	if strings.Contains(content, "已加入大厅") {
		if shouldSkipJoin(from) {
			return HallMessage{} // 静默过滤
		}
	}

	hall.mu.Lock()
	defer hall.mu.Unlock()

	hall.nextSeq++

	// 更新该话题的 seq（初始为 1）
	topicSeq := hall.topics[topic] + 1
	hall.topics[topic] = topicSeq

	msg := HallMessage{
		MsgID:       fmt.Sprintf("hall-%d", time.Now().UnixNano()),
		Topic:       topic,
		From:        from,
		FromName:    fromName,
		To:          to,
		Content:     content,
		Attachments: attachments,
		ReplyTo:     replyTo,
		Timestamp:   time.Now(),
		Seq:         topicSeq,
	}
	hall.messages = append(hall.messages, msg)

	// 保留最近 500 条，超过时淘汰最旧的 100 条
	if len(hall.messages) > 500 {
		hall.messages = hall.messages[100:]
	}

	fmt.Printf("[Hall] 📨 %s → %s [%s]: %s\n", from, to, topic, truncateString(content, 60))

	// 异步持久化
	go saveHallData()

	// 异步清理过期 join dedup 记录
	go clearStaleJoins()

	// 新消息回调（Agent 自动回复 + 专家路由）
	// 跳过条件：
	//   - join/系统消息
	//   - 专家报错消息（含"思考时遇到问题"）→ 防止死循环
	//   - 非 @ 消息
	//   - 自己发的消息
	if hallOnNewMessage != nil && !strings.Contains(content, "已加入大厅") && !strings.Contains(content, "交流大厅 v2") && !strings.Contains(content, "思考时遇到问题") {
		// 触发条件：任何 @ 提及（@小智 或 @专家名），且不是自己发的
		if strings.Contains(content, "@") && !strings.EqualFold(from, "小智") && !strings.EqualFold(fromName, "小智") && !strings.EqualFold(fromName, "小智 [cn-east]") {
			fmt.Printf("[Hall] 🔔 triggering callback: from=%s fromName=%s content=%s attachments=%d\n", from, fromName, truncateString(content, 60), len(attachments))
			go hallOnNewMessage(topic, from, to, content, attachments)
		} else {
			fmt.Printf("[Hall] 🔇 callback skipped: hasAt=%v from=%s fromName=%s\n", strings.Contains(content, "@"), from, fromName)
		}
	}

	return msg
}

// GetHallTopics 获取所有活跃话题
func GetHallTopics() []map[string]interface{} {
	hall.mu.RLock()
	defer hall.mu.RUnlock()

	var result []map[string]interface{}
	for topic, seq := range hall.topics {
		// 统计参与人数
		participants := make(map[string]bool)
		for _, m := range hall.messages {
			if m.Topic == topic {
				participants[m.From] = true
			}
		}
		result = append(result, map[string]interface{}{
			"topic":        topic,
			"seq":          seq,
			"participants": len(participants),
			"messages":     len(hall.messages),
		})
	}
	// 按最新 seq 倒序
	sort.Slice(result, func(i, j int) bool {
		return result[i]["seq"].(int64) > result[j]["seq"].(int64)
	})
	return result
}

// GetHallMessages 获取话题下的消息
// sinceSeq=0 返回全部，>0 返回该 seq 之后的新消息
func GetHallMessages(topic string, sinceSeq int64, limit int) []HallMessage {
	hall.mu.RLock()
	defer hall.mu.RUnlock()

	if limit <= 0 {
		limit = 50
	}

	var result []HallMessage
	for _, m := range hall.messages {
		if m.Topic == topic && m.Seq > sinceSeq {
			result = append(result, m)
		}
	}

	// 取最近 limit 条
	if len(result) > limit {
		result = result[len(result)-limit:]
	}

	return result
}

// GetHallMessagesForNode 获取给某节点或全体的话题消息
func GetHallMessagesForNode(topic, nodeID string, sinceSeq int64) []HallMessage {
	hall.mu.RLock()
	defer hall.mu.RUnlock()

	var result []HallMessage
	for _, m := range hall.messages {
		if m.Topic == topic && m.Seq > sinceSeq {
			if m.To == "all" || m.To == nodeID {
				result = append(result, m)
			}
		}
	}
	return result
}

// ── HTTP Handlers ──

func (g *OpcGateway) handleHallPost(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Topic       string       `json:"topic"`
		Content     string       `json:"content"`
		From        string       `json:"from"`
		To          string       `json:"to"`
		NodeName    string       `json:"node_name,omitempty"`
		Attachments []Attachment `json:"attachments,omitempty"`
		ReplyTo     string       `json:"reply_to,omitempty"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}

	if req.Topic == "" {
		req.Topic = "general"
	}
	if req.From == "" {
		writeJSON(w, Response{Success: false, Error: "from is required"})
		return
	}
	if req.To == "" {
		req.To = "all"
	}
	if req.Content == "" && len(req.Attachments) == 0 {
		writeJSON(w, Response{Success: false, Error: "content or attachments required"})
		return
	}
	if req.NodeName == "" {
		req.NodeName = req.From
	}

	msg := PostHallMessageEx(req.Topic, req.From, req.NodeName, req.To, req.Content, req.ReplyTo, req.Attachments...)

	// BUGFIX: HTTP 发的 Hall 消息也要 FanOut 给 WS 连接的 Worker 节点
	// 否则 Worker 收不到消息，不会触发 thinkAndReply
	if g.wsHub != nil {
		g.wsHub.FanOut(req.Topic, &WSMessage{
			MsgType:  MsgTypeHall,
			Topic:    req.Topic,
			From:     req.From,
			FromName: req.NodeName,
			To:       req.To,
			Content:  req.Content,
			Seq:      uint64(msg.Seq),
		}, "")
	}

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"msg_id": msg.MsgID,
			"seq":    msg.Seq,
			"topic":  msg.Topic,
		},
	})
}

// handleHallUpload — 上传文件到 Hall
func (g *OpcGateway) handleHallUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	// 限制 50MB
	r.Body = http.MaxBytesReader(w, r.Body, 50<<20)

	if err := r.ParseMultipartForm(10 << 20); err != nil {
		writeJSON(w, Response{Success: false, Error: "upload too large or invalid: " + err.Error()})
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		writeJSON(w, Response{Success: false, Error: "file field required: " + err.Error()})
		return
	}
	defer file.Close()

	// 安全文件名：保留原始文件名用于显示，用 hash 做存储文件名
	originalName := header.Filename
	safeName := fmt.Sprintf("file_%d_%s", time.Now().UnixNano(), sanitizeFilename(originalName))
	if safeName == "" || safeName == fmt.Sprintf("file_%d_", time.Now().UnixNano()) {
		safeName = fmt.Sprintf("file_%d", time.Now().UnixNano())
	}

	// 确保目录存在
	filesDir := filepath.Join(filepath.Dir(hallDataFile), "hall_files")
	if err := os.MkdirAll(filesDir, 0755); err != nil {
		writeJSON(w, Response{Success: false, Error: "create files dir: " + err.Error()})
		return
	}

	// 写文件
	dstPath := filepath.Join(filesDir, safeName)
	dst, err := os.Create(dstPath)
	if err != nil {
		writeJSON(w, Response{Success: false, Error: "create file: " + err.Error()})
		return
	}
	defer dst.Close()

	written, err := io.Copy(dst, file)
	if err != nil {
		os.Remove(dstPath)
		writeJSON(w, Response{Success: false, Error: "write file: " + err.Error()})
		return
	}

	// 检测 MIME 类型
	mimeType := header.Header.Get("Content-Type")
	if mimeType == "" || mimeType == "application/octet-stream" {
		mimeType = detectMimeType(safeName)
	}

	att := Attachment{
		Name: originalName,
		URL:  fmt.Sprintf("/api/v1/hall/files/%s", safeName),
		Size: written,
		Type: mimeType,
	}

	writeJSON(w, Response{
		Success: true,
		Data:    att,
	})
}

// handleHallFileDownload — 下载 Hall 文件
func (g *OpcGateway) handleHallFileDownload(w http.ResponseWriter, r *http.Request) {
	filename := strings.TrimPrefix(r.URL.Path, "/api/v1/hall/files/")
	if filename == "" || strings.Contains(filename, "..") {
		http.Error(w, "invalid filename", http.StatusBadRequest)
		return
	}

	filesDir := filepath.Join(filepath.Dir(hallDataFile), "hall_files")
	filePath := filepath.Join(filesDir, filename)

	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		http.Error(w, "file not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, filename))
	w.Header().Set("Content-Type", detectMimeType(filename))
	http.ServeFile(w, r, filePath)
}

// detectMimeType 根据扩展名推断 MIME 类型
func detectMimeType(name string) string {
	ext := strings.ToLower(filepath.Ext(name))
	switch ext {
	case ".pdf":
		return "application/pdf"
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".gif":
		return "image/gif"
	case ".webp":
		return "image/webp"
	case ".doc", ".docx":
		return "application/msword"
	case ".xls", ".xlsx":
		return "application/vnd.ms-excel"
	case ".zip":
		return "application/zip"
	case ".tar", ".gz":
		return "application/gzip"
	case ".txt":
		return "text/plain"
	case ".json":
		return "application/json"
	case ".html", ".htm":
		return "text/html"
	case ".py":
		return "text/x-python"
	case ".go":
		return "text/x-go"
	case ".js":
		return "application/javascript"
	case ".css":
		return "text/css"
	case ".mp4":
		return "video/mp4"
	case ".mp3":
		return "audio/mpeg"
	default:
		return "application/octet-stream"
	}
}

// sanitizeFilename 清理文件名中的不安全字符，保留中文
func sanitizeFilename(name string) string {
	var result strings.Builder
	for _, r := range name {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '.' || r == '-' || r == '_' {
			result.WriteRune(r)
		}
	}
	return result.String()
}

func (g *OpcGateway) handleHallTopics(w http.ResponseWriter, r *http.Request) {
	topics := GetHallTopics()
	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"topics": topics,
		"count":  len(topics),
	}})
}

func (g *OpcGateway) handleHallMessages(w http.ResponseWriter, r *http.Request) {
	topic := r.URL.Query().Get("topic")
	if topic == "" {
		topic = "general"
	}

	var sinceSeq int64
	if s := r.URL.Query().Get("since_seq"); s != "" {
		fmt.Sscanf(s, "%d", &sinceSeq)
	}

	nodeID := r.URL.Query().Get("node_id")

	limit := 50
	if l := r.URL.Query().Get("limit"); l != "" {
		fmt.Sscanf(l, "%d", &limit)
	}

	var msgs []HallMessage
	if nodeID != "" {
		msgs = GetHallMessagesForNode(topic, nodeID, sinceSeq)
	} else {
		msgs = GetHallMessages(topic, sinceSeq, limit)
	}

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"topic":    topic,
			"messages": msgs,
			"count":    len(msgs),
			"since":    sinceSeq,
		},
	})
}

// hallPollHandler — 节点专用轮询端点：返回该节点关心的所有新消息
// 参数: node_id, topic(可选), since_seq(可选)
func (g *OpcGateway) handleHallPoll(w http.ResponseWriter, r *http.Request) {
	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		writeJSON(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	topic := r.URL.Query().Get("topic")
	var sinceSeq int64
	if s := r.URL.Query().Get("since_seq"); s != "" {
		fmt.Sscanf(s, "%d", &sinceSeq)
	}

	hall.mu.RLock()

	var result []HallMessage
	for _, m := range hall.messages {
		if m.Seq <= sinceSeq {
			continue
		}
		if topic != "" && m.Topic != topic {
			continue
		}
		// 只返回发给 all 或发给本节点的
		if m.To == "all" || m.To == nodeID {
			result = append(result, m)
		}
	}

	hall.mu.RUnlock()

	writeJSON(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"messages": result,
			"count":    len(result),
			"node_id":  nodeID,
		},
	})
}

// handleHallClear — 清空话题消息
func (g *OpcGateway) handleHallClear(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Topic string `json:"topic"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.Topic == "" {
		writeJSON(w, Response{Success: false, Error: "topic is required"})
		return
	}

	hall.mu.Lock()
	// 过滤掉该话题的消息
	var kept []HallMessage
	for _, m := range hall.messages {
		if m.Topic != req.Topic {
			kept = append(kept, m)
		}
	}
	hall.messages = kept
	// 重置话题 seq
	hall.topics[req.Topic] = 0
	hall.mu.Unlock()

	go saveHallData()

	fmt.Printf("[Hall] 🗑️ cleared all messages for topic [%s]\n", req.Topic)
	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"topic": req.Topic,
	}})
}

// handleHallRenameTopic — 重命名话题
func (g *OpcGateway) handleHallRenameTopic(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		OldTopic string `json:"old_topic"`
		NewTopic string `json:"new_topic"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.OldTopic == "" || req.NewTopic == "" {
		writeJSON(w, Response{Success: false, Error: "old_topic and new_topic are required"})
		return
	}

	hall.mu.Lock()
	// 更新所有消息的话题名
	for i := range hall.messages {
		if hall.messages[i].Topic == req.OldTopic {
			hall.messages[i].Topic = req.NewTopic
		}
	}
	// 迁移话题 seq
	if seq, exists := hall.topics[req.OldTopic]; exists {
		hall.topics[req.NewTopic] = seq
		delete(hall.topics, req.OldTopic)
	}
	hall.mu.Unlock()

	go saveHallData()

	fmt.Printf("[Hall] ✏️ renamed topic [%s] → [%s]\n", req.OldTopic, req.NewTopic)
	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"old_topic": req.OldTopic,
		"new_topic": req.NewTopic,
	}})
}

// ══════════════════════════════════════════════════════════════════════
//  Phase 4: 新功能 — 反应、置顶、编辑、在线状态、正在输入
// ══════════════════════════════════════════════════════════════════════

// ── 表情反应 ──

// handleHallReact — POST /api/v1/hall/react
// 对消息添加/移除表情反应
func (g *OpcGateway) handleHallReact(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		MsgID  string `json:"msg_id"`
		Emoji  string `json:"emoji"`
		UserID string `json:"user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.MsgID == "" || req.Emoji == "" || req.UserID == "" {
		writeJSON(w, Response{Success: false, Error: "msg_id, emoji, user_id required"})
		return
	}

	hall.mu.Lock()
	defer hall.mu.Unlock()

	for i := range hall.messages {
		if hall.messages[i].MsgID == req.MsgID {
			// 检查是否已有该用户+该表情的反应
			found := false
			for j := range hall.messages[i].Reactions {
				r := &hall.messages[i].Reactions[j]
				if r.Emoji == req.Emoji && r.UserID == req.UserID {
					// 已存在 → 移除（toggle）
					hall.messages[i].Reactions = append(hall.messages[i].Reactions[:j], hall.messages[i].Reactions[j+1:]...)
					found = true
					break
				}
			}
			if !found {
				hall.messages[i].Reactions = append(hall.messages[i].Reactions, Reaction{
					Emoji:  req.Emoji,
					UserID: req.UserID,
					Time:   time.Now(),
				})
			}
			go saveHallData()
			writeJSON(w, Response{Success: true, Data: map[string]interface{}{
				"msg_id":   req.MsgID,
				"reactions": hall.messages[i].Reactions,
			}})
			return
		}
	}

	writeJSON(w, Response{Success: false, Error: "message not found"})
}

// ── 置顶/取消置顶 ──

// handleHallPin — POST /api/v1/hall/pin
func (g *OpcGateway) handleHallPin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Topic string `json:"topic"`
		MsgID string `json:"msg_id"`
		Pin   bool   `json:"pin"` // true=置顶, false=取消置顶
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.Topic == "" || req.MsgID == "" {
		writeJSON(w, Response{Success: false, Error: "topic and msg_id required"})
		return
	}

	hall.mu.Lock()
	defer hall.mu.Unlock()

	// 更新消息的 pinned 状态
	for i := range hall.messages {
		if hall.messages[i].MsgID == req.MsgID {
			hall.messages[i].Pinned = req.Pin
			break
		}
	}

	// 更新话题的置顶列表
	if req.Pin {
		// 检查是否已在列表中
		already := false
		for _, id := range hall.pinned[req.Topic] {
			if id == req.MsgID {
				already = true
				break
			}
		}
		if !already {
			hall.pinned[req.Topic] = append(hall.pinned[req.Topic], req.MsgID)
		}
	} else {
		var kept []string
		for _, id := range hall.pinned[req.Topic] {
			if id != req.MsgID {
				kept = append(kept, id)
			}
		}
		hall.pinned[req.Topic] = kept
	}

	go saveHallData()
	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"topic":  req.Topic,
		"msg_id": req.MsgID,
		"pinned": req.Pin,
	}})
}

// handleHallPinned — GET /api/v1/hall/pinned?topic=xxx
func (g *OpcGateway) handleHallPinned(w http.ResponseWriter, r *http.Request) {
	topic := r.URL.Query().Get("topic")
	if topic == "" {
		topic = "general"
	}

	hall.mu.RLock()
	pinnedIDs := hall.pinned[topic]
	var pinnedMsgs []HallMessage
	for _, id := range pinnedIDs {
		for _, m := range hall.messages {
			if m.MsgID == id {
				pinnedMsgs = append(pinnedMsgs, m)
				break
			}
		}
	}
	hall.mu.RUnlock()

	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"topic":    topic,
		"pinned":   pinnedMsgs,
		"count":    len(pinnedMsgs),
	}})
}

// ── 编辑消息 ──

// handleHallEdit — POST /api/v1/hall/edit
func (g *OpcGateway) handleHallEdit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		MsgID   string `json:"msg_id"`
		Content string `json:"content"`
		UserID  string `json:"user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.MsgID == "" || req.Content == "" || req.UserID == "" {
		writeJSON(w, Response{Success: false, Error: "msg_id, content, user_id required"})
		return
	}

	hall.mu.Lock()
	defer hall.mu.Unlock()

	for i := range hall.messages {
		if hall.messages[i].MsgID == req.MsgID {
			if hall.messages[i].From != req.UserID {
				writeJSON(w, Response{Success: false, Error: "只能编辑自己的消息"})
				return
			}
			hall.messages[i].Content = req.Content
			hall.messages[i].Edited = true
			go saveHallData()
			writeJSON(w, Response{Success: true, Data: map[string]interface{}{
				"msg_id": req.MsgID,
				"edited": true,
			}})
			return
		}
	}

	writeJSON(w, Response{Success: false, Error: "message not found"})
}

// ── 删除消息 ──

// handleHallDelete — POST /api/v1/hall/delete
func (g *OpcGateway) handleHallDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		MsgID  string `json:"msg_id"`
		UserID string `json:"user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.MsgID == "" || req.UserID == "" {
		writeJSON(w, Response{Success: false, Error: "msg_id and user_id required"})
		return
	}

	hall.mu.Lock()
	defer hall.mu.Unlock()

	for i := range hall.messages {
		if hall.messages[i].MsgID == req.MsgID {
			if hall.messages[i].From != req.UserID {
				writeJSON(w, Response{Success: false, Error: "只能删除自己的消息"})
				return
			}
			// 标记为已删除（保留占位）
			hall.messages[i].Content = "[消息已删除]"
			hall.messages[i].Attachments = nil
			hall.messages[i].Reactions = nil
			go saveHallData()
			writeJSON(w, Response{Success: true, Data: map[string]interface{}{
				"msg_id": req.MsgID,
				"deleted": true,
			}})
			return
		}
	}

	writeJSON(w, Response{Success: false, Error: "message not found"})
}

// ── 在线状态 ──

// handleHallOnline — POST /api/v1/hall/online
// 节点心跳上报在线状态
func (g *OpcGateway) handleHallOnline(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		UserID   string `json:"user_id"`
		UserName string `json:"user_name"`
		Online   bool   `json:"online"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.UserID == "" {
		writeJSON(w, Response{Success: false, Error: "user_id required"})
		return
	}

	hall.mu.Lock()
	if req.Online {
		hall.online[req.UserID] = time.Now()
	} else {
		delete(hall.online, req.UserID)
	}
	hall.mu.Unlock()

	writeJSON(w, Response{Success: true})
}

// handleHallOnlineList — GET /api/v1/hall/online
func (g *OpcGateway) handleHallOnlineList(w http.ResponseWriter, r *http.Request) {
	hall.mu.RLock()
	defer hall.mu.RUnlock()

	type onlineUser struct {
		UserID    string    `json:"user_id"`
		LastSeen  time.Time `json:"last_seen"`
		Online    bool      `json:"online"`
	}

	var list []onlineUser
	now := time.Now()
	for uid, lastSeen := range hall.online {
		online := now.Sub(lastSeen) < 2*time.Minute
		list = append(list, onlineUser{
			UserID:   uid,
			LastSeen: lastSeen,
			Online:   online,
		})
	}

	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"users": list,
		"count": len(list),
	}})
}

// ── 正在输入 ──

// handleHallTyping — POST /api/v1/hall/typing
func (g *OpcGateway) handleHallTyping(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, Response{Success: false, Error: "POST required"})
		return
	}

	var req struct {
		Topic  string `json:"topic"`
		UserID string `json:"user_id"`
		Name   string `json:"name"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.Topic == "" || req.UserID == "" {
		writeJSON(w, Response{Success: false, Error: "topic and user_id required"})
		return
	}

	hall.mu.Lock()
	if hall.typing[req.Topic] == nil {
		hall.typing[req.Topic] = make(map[string]time.Time)
	}
	hall.typing[req.Topic][req.UserID] = time.Now()
	hall.mu.Unlock()

	writeJSON(w, Response{Success: true})
}

// handleHallTypingList — GET /api/v1/hall/typing?topic=xxx
func (g *OpcGateway) handleHallTypingList(w http.ResponseWriter, r *http.Request) {
	topic := r.URL.Query().Get("topic")
	if topic == "" {
		topic = "general"
	}

	hall.mu.Lock()
	defer hall.mu.Unlock()

	// 清理超过 5 秒的 typing 记录
	now := time.Now()
	var result []TypingInfo
	if users, ok := hall.typing[topic]; ok {
		for uid, t := range users {
			if now.Sub(t) < 5*time.Second {
				result = append(result, TypingInfo{
					Topic:  topic,
					UserID: uid,
					Name:   uid,
				})
			} else {
				delete(users, uid)
			}
		}
	}

	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"topic":  topic,
		"typing": result,
		"count":  len(result),
	}})
}

// ── 话题统计增强 ──

// handleHallStats — GET /api/v1/hall/stats
func (g *OpcGateway) handleHallStats(w http.ResponseWriter, r *http.Request) {
	hall.mu.RLock()
	defer hall.mu.RUnlock()

	totalMsgs := len(hall.messages)
	totalTopics := len(hall.topics)
	activeUsers := len(hall.online)

	// 各话题消息数
	topicStats := make(map[string]int)
	for _, m := range hall.messages {
		topicStats[m.Topic]++
	}

	writeJSON(w, Response{Success: true, Data: map[string]interface{}{
		"total_messages": totalMsgs,
		"total_topics":   totalTopics,
		"active_users":   activeUsers,
		"topic_stats":    topicStats,
	}})
}

// ── Helper ──

func truncateString(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) > maxLen {
		return string(runes[:maxLen]) + "..."
	}
	return s
}

// trimTrailingNewline 去除末尾换行
func trimTrailingNewline(s string) string {
	return strings.TrimRight(s, "\n\r")
}
