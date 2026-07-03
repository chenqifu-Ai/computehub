// Package gateway — Ollama 本地模型对话代理
// 提供 /api/v1/ollama/* 端点，让前端通过 Gateway 与本地 Ollama 交互
//
// 端点:
//   GET  /api/v1/ollama/status       — 检查 Ollama 是否运行
//   POST /api/v1/ollama/start        — 启动 ollama serve
//   GET  /api/v1/ollama/models        — 获取模型列表
//   POST /api/v1/ollama/chat          — 对话（流式 SSE）

package gateway

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"
	"time"
)

const ollamaBaseURL = "http://127.0.0.1:11434"

// ── 状态检查 ──

// handleOllamaStatus 检查 Ollama 服务是否在运行
func (g *OpcGateway) handleOllamaStatus(w http.ResponseWriter, r *http.Request) {
	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get(ollamaBaseURL + "/api/tags")
	if err != nil {
		g.sendJSON(w, map[string]interface{}{
			"running": false,
			"error":   err.Error(),
		})
		return
	}
	defer resp.Body.Close()
	g.sendJSON(w, map[string]interface{}{
		"running": true,
		"version": resp.Header.Get("Ollama-Version"),
	})
}

// ── 启动 Ollama ──

// handleOllamaStart 启动 ollama serve（后台进程）
func (g *OpcGateway) handleOllamaStart(w http.ResponseWriter, r *http.Request) {
	// 先检查是否已在运行
	client := &http.Client{Timeout: 2 * time.Second}
	if resp, err := client.Get(ollamaBaseURL + "/api/tags"); err == nil {
		resp.Body.Close()
		g.sendJSON(w, map[string]interface{}{
			"success": true,
			"message": "Ollama 已在运行中",
		})
		return
	}

	// 启动 ollama serve
	cmd := exec.Command("ollama", "serve")
	if err := cmd.Start(); err != nil {
		g.sendJSON(w, map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("启动失败: %v", err),
		})
		return
	}

	// 等待服务就绪（最多等 5 秒）
	for i := 0; i < 10; i++ {
		time.Sleep(500 * time.Millisecond)
		if resp, err := client.Get(ollamaBaseURL + "/api/tags"); err == nil {
			resp.Body.Close()
			g.sendJSON(w, map[string]interface{}{
				"success": true,
				"message": "Ollama 已启动",
			})
			return
		}
	}

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"message": "Ollama 启动命令已执行，等待就绪中...",
	})
}

// ── 模型列表 ──

// handleOllamaModels 获取本地模型列表
func (g *OpcGateway) handleOllamaModels(w http.ResponseWriter, r *http.Request) {
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(ollamaBaseURL + "/api/tags")
	if err != nil {
		g.sendJSON(w, map[string]interface{}{
			"success": false,
			"error":   err.Error(),
			"models":  []interface{}{},
		})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var result struct {
		Models []struct {
			Name       string `json:"name"`
			Size       int64  `json:"size"`
			ModifiedAt string `json:"modified_at"`
		} `json:"models"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		g.sendJSON(w, map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("解析失败: %v", err),
			"models":  []interface{}{},
		})
		return
	}

	models := make([]map[string]interface{}, 0, len(result.Models))
	for _, m := range result.Models {
		// 去掉 :latest 后缀
		name := strings.TrimSuffix(m.Name, ":latest")
		models = append(models, map[string]interface{}{
			"name":       name,
			"size":       m.Size,
			"size_human": formatBytes(m.Size),
		})
	}

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"models":  models,
	})
}

// ── 对话（流式 SSE） ──

// ollamaChatRequest 前端发来的对话请求
type ollamaChatRequest struct {
	Model        string          `json:"model"`
	Messages     []chatMessage   `json:"messages"`
	Stream       bool            `json:"stream"`
	ThinkEnabled bool            `json:"think_enabled"`
	Options      *ollamaOptions  `json:"options,omitempty"`
}

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ollamaOptions struct {
	Temperature float64 `json:"temperature,omitempty"`
	TopP        float64 `json:"top_p,omitempty"`
	NumPredict  int     `json:"num_predict,omitempty"`
}

// handleOllamaChat 处理对话请求，支持流式 SSE 返回
func (g *OpcGateway) handleOllamaChat(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req ollamaChatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf(`{"error":"invalid request: %v"}`, err), http.StatusBadRequest)
		return
	}

	if req.Model == "" {
		http.Error(w, `{"error":"model is required"}`, http.StatusBadRequest)
		return
	}

	// 构造 Ollama API 请求
	ollamaReq := map[string]interface{}{
		"model":    req.Model,
		"messages": req.Messages,
		"stream":   true,
	}

	// 合并 options
	opts := make(map[string]interface{})
	if req.Options != nil {
		if req.Options.Temperature > 0 {
			opts["temperature"] = req.Options.Temperature
		}
		if req.Options.TopP > 0 {
			opts["top_p"] = req.Options.TopP
		}
		if req.Options.NumPredict > 0 {
			opts["num_predict"] = req.Options.NumPredict
		}
	}
	// 默认 temperature
	if _, ok := opts["temperature"]; !ok {
		opts["temperature"] = 0.7
	}
	// 如果 Think 未开启，在 options 中禁用 thinking（qwen3 等模型默认会思考）
	if !req.ThinkEnabled {
		opts["thinking"] = false
	}
	if len(opts) > 0 {
		ollamaReq["options"] = opts
	}

	body, _ := json.Marshal(ollamaReq)

	// 设置 SSE 头 — 必须在调用 Ollama API 之前发送，否则浏览器 fetch 会超时
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		// 如果 flush 不支持，回退到非流式
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}
	flusher.Flush()

	// 发送心跳，让浏览器知道连接已建立（qwen3:4b CPU 推理可能等 60 秒）
	fmt.Fprintf(w, "event: status\ndata: 🧠 模型加载中，请稍候...\n\n")
	flusher.Flush()

	// 启动后台心跳 goroutine，每 5 秒发一次 data 事件（浏览器 ReadableStream 需要 data: 前缀才能触发 chunk）
	// ⚠️ 模型开始输出内容后立即停止心跳，避免 data race（两个 goroutine 同时写 ResponseWriter）
	heartbeatDone := make(chan struct{})
	firstContent := make(chan struct{}, 1)
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				fmt.Fprintf(w, "data: .\n\n")
				flusher.Flush()
			case <-firstContent:
				// 模型已开始输出，停止心跳
				return
			case <-heartbeatDone:
				return
			}
		}
	}()
	defer close(heartbeatDone)

	// 调用 Ollama API（CPU 推理可能很慢，给 5 分钟超时）
	client := &http.Client{Timeout: 300 * time.Second}
	ollamaResp, err := client.Post(ollamaBaseURL+"/api/chat", "application/json", bytes.NewReader(body))
	if err != nil {
		fmt.Fprintf(w, "event: error\ndata: ollama call failed: %v\n\n", err)
		flusher.Flush()
		return
	}
	defer ollamaResp.Body.Close()

	// 流式读取 Ollama 响应并转发为 SSE
	scanner := bufio.NewScanner(ollamaResp.Body)
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)
	fullContent := ""
	hasSentContent := false

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		var chunk struct {
			Model     string `json:"model"`
			CreatedAt string `json:"created_at"`
			Message   struct {
				Role     string `json:"role"`
				Content  string `json:"content"`
				Thinking string `json:"thinking"`
			} `json:"message"`
			Done bool `json:"done"`
		}
		if err := json.Unmarshal([]byte(line), &chunk); err != nil {
			continue
		}

		// 先发 thinking 内容（如果有且 Think 已开启）
		if chunk.Message.Thinking != "" && req.ThinkEnabled {
			if !hasSentContent {
				hasSentContent = true
				close(firstContent) // 停止心跳
			}
			fmt.Fprintf(w, "event: thinking\ndata: %s\n\n", jsonEscape(chunk.Message.Thinking))
			flusher.Flush()
		}

		if chunk.Message.Content != "" {
			if !hasSentContent {
				hasSentContent = true
				close(firstContent) // 停止心跳
			}
			fullContent += chunk.Message.Content
			fmt.Fprintf(w, "data: %s\n\n", jsonEscape(chunk.Message.Content))
			flusher.Flush()
		}

		if chunk.Done {
			// 发送完成事件
			fmt.Fprintf(w, "event: done\ndata: %s\n\n", jsonEscape(fullContent))
			flusher.Flush()
			break
		}
	}

	if err := scanner.Err(); err != nil {
		fmt.Fprintf(w, "event: error\ndata: %v\n\n", err)
		flusher.Flush()
	}
}

// ── 工具函数 ──

func (g *OpcGateway) sendJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func formatBytes(b int64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := int64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(b)/float64(div), "KMGTPE"[exp])
}

func jsonEscape(s string) string {
	// 简单转义，确保 SSE data 字段安全
	s = strings.ReplaceAll(s, "\\", "\\\\")
	s = strings.ReplaceAll(s, "\n", "\\n")
	s = strings.ReplaceAll(s, "\r", "\\r")
	return s
}
