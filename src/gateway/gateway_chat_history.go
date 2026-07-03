// Package gateway — 对话历史 Git 管理
// 每次对话自动保存为 .md 文件，通过 git commit 管理版本
//
// 文件结构: memory/chats/YYYY-MM-DD_<model>.md
// Commit 策略: 每 30 秒 或 每 5 条消息 触发一次 commit
// 集群同步: commit 后自动 git push 到远端

package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// ── 配置 ──

var (
	chatsDir     = "memory/chats" // 相对于仓库根目录
	chatRepoDir  = ""             // 仓库根目录（自动检测）
	chatMu       sync.Mutex
	chatBuffer   = make(map[string]*chatBufferEntry) // key: "YYYY-MM-DD_model"
	chatInitOnce sync.Once
)

type chatBufferEntry struct {
	lines    []string
	msgCount int
	lastFlush time.Time
	mu       sync.Mutex
}

// chatSaveRequest 前端发来的保存请求
type chatSaveRequest struct {
	Model   string `json:"model"`
	Role    string `json:"role"`
	Content string `json:"content"`
}

// chatHistoryRequest 前端发来的历史请求
type chatHistoryRequest struct {
	Model string `json:"model"`
	Date  string `json:"date"` // YYYY-MM-DD，默认今天
}

// ── 初始化 ──

func initChatHistory() {
	chatInitOnce.Do(func() {
		// 自动检测仓库根目录
		candidates := []string{
			"/home/computehub/ComputeHub",
			"/data/data/com.termux/files/home/ComputeHub_new",
			".",
		}
		for _, dir := range candidates {
			if info, err := os.Stat(filepath.Join(dir, ".git")); err == nil && info.IsDir() {
				chatRepoDir = dir
				break
			}
		}
		if chatRepoDir == "" {
			// 尝试从当前工作目录找
			cwd, _ := os.Getwd()
			for dir := cwd; dir != "/"; dir = filepath.Dir(dir) {
				if info, err := os.Stat(filepath.Join(dir, ".git")); err == nil && info.IsDir() {
					chatRepoDir = dir
					break
				}
			}
		}
		if chatRepoDir == "" {
			chatRepoDir = "."
		}
		logWithTimestamp("📝 Chat history repo: %s", chatRepoDir)

		// 确保目录存在
		chatDir := filepath.Join(chatRepoDir, chatsDir)
		os.MkdirAll(chatDir, 0755)

		// 启动定期 flush goroutine
		go chatFlushLoop()
	})
}

// chatFlushLoop 每 15 秒检查一次 buffer，超时未 flush 的强制写入
func chatFlushLoop() {
	ticker := time.NewTicker(15 * time.Second)
	for range ticker.C {
		chatMu.Lock()
		for key, entry := range chatBuffer {
			entry.mu.Lock()
			if entry.msgCount > 0 && time.Since(entry.lastFlush) > 30*time.Second {
				lines := entry.lines
				count := entry.msgCount
				entry.lines = nil
				entry.msgCount = 0
				entry.lastFlush = time.Now()
				entry.mu.Unlock()
				// 异步写入
				go flushChatBuffer(key, lines, count)
			} else {
				entry.mu.Unlock()
			}
		}
		chatMu.Unlock()
	}
}

// ── API Handlers ──

// handleChatSave 保存一条消息到 buffer（攒批写入）
func (g *OpcGateway) handleChatSave(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req chatSaveRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	if req.Model == "" || req.Content == "" {
		g.sendJSON(w, map[string]string{"error": "model and content are required"})
		return
	}

	initChatHistory()

	date := time.Now().Format("2006-01-02")
	timeStr := time.Now().Format("15:04:05")
	key := date + "_" + sanitizeModelName(req.Model)

	// 格式化消息行
	var line string
	switch req.Role {
	case "user":
		line = fmt.Sprintf("**你** (%s)\n%s\n", timeStr, req.Content)
	case "assistant":
		line = fmt.Sprintf("**%s** (%s)\n%s\n", req.Model, timeStr, req.Content)
	default:
		line = fmt.Sprintf("**%s** (%s)\n%s\n", req.Role, timeStr, req.Content)
	}

	// 写入 buffer
	chatMu.Lock()
	entry, ok := chatBuffer[key]
	if !ok {
		entry = &chatBufferEntry{lastFlush: time.Now()}
		chatBuffer[key] = entry
	}
	chatMu.Unlock()

	entry.mu.Lock()
	entry.lines = append(entry.lines, line)
	entry.msgCount++
	count := entry.msgCount
	entry.mu.Unlock()

	// 每 5 条消息触发一次 flush
	if count >= 5 {
		entry.mu.Lock()
		lines := entry.lines
		entry.lines = nil
		entry.msgCount = 0
		entry.lastFlush = time.Now()
		entry.mu.Unlock()
		go flushChatBuffer(key, lines, count)
	}

	g.sendJSON(w, map[string]interface{}{
		"success":  true,
		"buffered": count,
	})
}

// handleChatHistory 读取某日某模型的对话历史
func (g *OpcGateway) handleChatHistory(w http.ResponseWriter, r *http.Request) {
	initChatHistory()

	model := r.URL.Query().Get("model")
	date := r.URL.Query().Get("date")
	if date == "" {
		date = time.Now().Format("2006-01-02")
	}
	if model == "" {
		g.sendJSON(w, map[string]interface{}{
			"success": false,
			"error":   "model is required",
			"messages": []interface{}{},
		})
		return
	}

	fileName := date + "_" + sanitizeModelName(model) + ".md"
	filePath := filepath.Join(chatRepoDir, chatsDir, fileName)

	content, err := os.ReadFile(filePath)
	if err != nil {
		// 文件不存在不是错误
		g.sendJSON(w, map[string]interface{}{
			"success":  true,
			"messages": []interface{}{},
			"file":     fileName,
		})
		return
	}

	// 解析为消息列表
	messages := parseChatFile(string(content), model)

	g.sendJSON(w, map[string]interface{}{
		"success":  true,
		"messages": messages,
		"file":     fileName,
	})
}

// handleChatSessions 列出所有可用的对话 session
func (g *OpcGateway) handleChatSessions(w http.ResponseWriter, r *http.Request) {
	initChatHistory()

	chatDir := filepath.Join(chatRepoDir, chatsDir)
	entries, err := os.ReadDir(chatDir)
	if err != nil {
		g.sendJSON(w, map[string]interface{}{
			"success":  true,
			"sessions": []interface{}{},
		})
		return
	}

	type sessionInfo struct {
		Date  string `json:"date"`
		Model string `json:"model"`
		File  string `json:"file"`
		Size  int64  `json:"size"`
	}

	var sessions []sessionInfo
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".md") {
			continue
		}
		// 文件名: YYYY-MM-DD_model.md
		name := strings.TrimSuffix(e.Name(), ".md")
		parts := strings.SplitN(name, "_", 2)
		if len(parts) != 2 {
			continue
		}
		info, _ := e.Info()
		sessions = append(sessions, sessionInfo{
			Date:  parts[0],
			Model: parts[1],
			File:  e.Name(),
			Size:  info.Size(),
		})
	}

	// 按日期降序
	sort.Slice(sessions, func(i, j int) bool {
		return sessions[i].Date+sessions[i].Model > sessions[j].Date+sessions[j].Model
	})

	g.sendJSON(w, map[string]interface{}{
		"success":  true,
		"sessions": sessions,
	})
}

// ── 核心函数 ──

// flushChatBuffer 将 buffer 中的消息写入文件并 git commit
func flushChatBuffer(key string, lines []string, count int) {
	if len(lines) == 0 {
		return
	}

	initChatHistory()

	// 解析 key: "YYYY-MM-DD_model"
	parts := strings.SplitN(key, "_", 2)
	if len(parts) != 2 {
		return
	}
	date, model := parts[0], parts[1]

	fileName := key + ".md"
	filePath := filepath.Join(chatRepoDir, chatsDir, fileName)

	chatMu.Lock()
	defer chatMu.Unlock()

	// 追加写入文件
	f, err := os.OpenFile(filePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		logWithTimestamp("📝 ❌ Failed to open chat file %s: %v", filePath, err)
		return
	}

	// 如果是新文件，写入 header
	info, _ := f.Stat()
	if info.Size() == 0 {
		header := fmt.Sprintf("---\nsession: %s\nmodel: %s\ncreated: %s\n---\n\n",
			model, model, time.Now().Format(time.RFC3339))
		f.WriteString(header)
	}

	for _, line := range lines {
		f.WriteString(line + "\n")
	}
	f.Close()

	// git add + commit
	commitMsg := fmt.Sprintf("chat: %s — %d 条消息 (%s)", model, count, date)
	gitCmd := exec.Command("git", "add", filepath.Join(chatsDir, fileName))
	gitCmd.Dir = chatRepoDir
	if out, err := gitCmd.CombinedOutput(); err != nil {
		logWithTimestamp("📝 ⚠️ git add failed: %v\n%s", err, string(out))
		return
	}

	gitCmd = exec.Command("git", "commit", "-m", commitMsg)
	gitCmd.Dir = chatRepoDir
	if out, err := gitCmd.CombinedOutput(); err != nil {
		// 没有变更不是错误
		if !strings.Contains(string(out), "nothing to commit") {
			logWithTimestamp("📝 ⚠️ git commit failed: %v\n%s", err, string(out))
		}
		return
	}

	logWithTimestamp("📝 ✅ Chat committed: %s (%d msgs)", commitMsg, count)

	// 集群同步：git push
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		gitCmd := exec.CommandContext(ctx, "git", "push", "origin", "master")
		gitCmd.Dir = chatRepoDir
		if out, err := gitCmd.CombinedOutput(); err != nil {
			// push 失败不阻塞，下次再试
			logWithTimestamp("📝 ⚠️ git push failed (will retry): %v\n%s", err, string(out))
		} else {
			logWithTimestamp("📝 ✅ Chat synced to cluster")
		}
	}()
}

// ── 工具函数 ──

func sanitizeModelName(name string) string {
	// 模型名可能包含 : 和 /，替换为安全字符
	name = strings.ReplaceAll(name, ":", "-")
	name = strings.ReplaceAll(name, "/", "-")
	name = strings.ReplaceAll(name, " ", "-")
	return name
}

// parseChatFile 将 .md 文件解析为消息列表
func parseChatFile(content, model string) []map[string]interface{} {
	var messages []map[string]interface{}
	lines := strings.Split(content, "\n")

	var currentRole string
	var currentContent strings.Builder

	for _, line := range lines {
		if strings.HasPrefix(line, "**你** (") {
			// 保存上一条
			if currentRole != "" && currentContent.Len() > 0 {
				messages = append(messages, map[string]interface{}{
					"role":    currentRole,
					"content": strings.TrimSpace(currentContent.String()),
				})
				currentContent.Reset()
			}
			currentRole = "user"
			// 提取时间
			if idx := strings.Index(line, ")"); idx > 0 {
				// 跳过时间行，内容在下一行
			}
		} else if strings.HasPrefix(line, "**"+model) || strings.HasPrefix(line, "**") && strings.Contains(line, "** (") {
			// 保存上一条
			if currentRole != "" && currentContent.Len() > 0 {
				messages = append(messages, map[string]interface{}{
					"role":    currentRole,
					"content": strings.TrimSpace(currentContent.String()),
				})
				currentContent.Reset()
			}
			currentRole = "assistant"
		} else if strings.HasPrefix(line, "---") {
			continue // frontmatter
		} else if line == "" {
			if currentRole != "" && currentContent.Len() > 0 {
				currentContent.WriteString("\n")
			}
		} else {
			if currentRole != "" {
				currentContent.WriteString(line + "\n")
			}
		}
	}

	// 最后一条
	if currentRole != "" && currentContent.Len() > 0 {
		messages = append(messages, map[string]interface{}{
			"role":    currentRole,
			"content": strings.TrimSpace(currentContent.String()),
		})
	}

	return messages
}
