package gateway

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/computehub/opc/src/agent"
)

// ====== LLM 代理端点（Worker 节点通过 Gateway 中转调用 NewAPI） ======

// handleLlmProxy 接收 Worker 的 LLM 请求，通过 Gateway 转发到 NewAPI
func (g *OpcGateway) handleLlmProxy(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, `{"error":"read body failed"}`, http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// 注入 reasoning: false（默认关掉 thinking）
	var reqMap map[string]interface{}
	if err := json.Unmarshal(body, &reqMap); err == nil {
		if _, exists := reqMap["reasoning"]; !exists {
			reqMap["reasoning"] = false
		}
		modified, err := json.Marshal(reqMap)
		if err == nil {
			body = modified
		}
	}

	apiURL := g.composerAPI
	apiKey := g.composerKey
	timeout := 60
	if apiURL == "" {
		apiURL = "https://ai.zhangtuokeji.top:9090/v1"
		apiKey = "sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB"
	}

	targetURL := strings.TrimRight(apiURL, "/") + "/chat/completions"
	req, err := http.NewRequest("POST", targetURL, bytes.NewReader(body))
	if err != nil {
		http.Error(w, `{"error":"create upstream request failed"}`, http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	transport := &http.Transport{
		TLSNextProto: make(map[string]func(authority string, c *tls.Conn) http.RoundTripper),
	}
	client := &http.Client{
		Timeout:   time.Duration(timeout) * time.Second,
		Transport: transport,
	}

	resp, err := client.Do(req)
	if err != nil {
		logWithTimestamp("[LLM Proxy] ❌ Upstream call failed: %v", err)
		http.Error(w, fmt.Sprintf(`{"error":"upstream call failed: %v"}`, err), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	for key, vals := range resp.Header {
		for _, v := range vals {
			w.Header().Add(key, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// ====== Phase 3: Expert List Handler ======

func (g *OpcGateway) handleExpertList(w http.ResponseWriter, r *http.Request) {
	if g.ExpertRegistry == nil {
		g.sendResponse(w, Response{Success: false, Error: "Expert registry not initialized"})
		return
	}

	experts := g.ExpertRegistry.List()
	type expertInfo struct {
		ID          string   `json:"id"`
		Name        string   `json:"name"`
		Nickname    string   `json:"nickname"`
		Domain      string   `json:"domain"`
		Description string   `json:"description"`
		Tags        []string `json:"tags"`
	}

	list := make([]expertInfo, 0, len(experts))
	for _, e := range experts {
		list = append(list, expertInfo{
			ID:          e.ID,
			Name:        e.Name,
			Nickname:    e.Nickname,
			Domain:      e.Domain,
			Description: e.Description,
			Tags:        e.Tags,
		})
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"experts": list,
			"count":   len(list),
		},
	})
}

// ====== Agent Think Handler (Layer 2) ======

func (g *OpcGateway) handleAgentThink(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil {
		g.sendResponse(w, Response{
			Success: false,
			Error:   "Agent not initialized",
		})
		return
	}

	var req agent.AgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{
			Success: false,
			Error:   fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	if req.Task == "" {
		g.sendResponse(w, Response{
			Success: false,
			Error:   "task is required",
		})
		return
	}

	logWithTimestamp("[Agent] 🧠 Think request: %s (session=%s)", req.Task, req.SessionID)

	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()

	resp, err := g.Agent.Think(ctx, &req)
	if err != nil {
		logWithTimestamp("[Agent] ❌ Think failed: %v", err)
		g.sendResponse(w, Response{
			Success: false,
			Error:   fmt.Sprintf("Agent think failed: %v", err),
		})
		return
	}

	logWithTimestamp("[Agent] ✅ Think complete: %d plan steps, result=%d chars",
		len(resp.Plan), len(resp.Result))

	g.sendResponse(w, Response{
		Success: true,
		Data:    resp,
	})
}

// handleAgentStream — SSE 流式端到端对话
func (g *OpcGateway) handleAgentStream(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil {
		g.sendResponse(w, Response{Success: false, Error: "Agent not initialized"})
		return
	}

	var req agent.AgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid request body: %v", err)})
		return
	}
	if req.Task == "" {
		g.sendResponse(w, Response{Success: false, Error: "task is required"})
		return
	}

	logWithTimestamp("[Agent] 🧠 Stream request: %s (session=%s)", req.Task, req.SessionID)

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		g.sendResponse(w, Response{Success: false, Error: "streaming not supported"})
		return
	}

	sendSSE := func(eventType, data string) {
		fmt.Fprintf(w, "event: %s\ndata: %s\n\n", eventType, data)
		flusher.Flush()
	}

	heartbeatDone := make(chan struct{})
	firstContent := make(chan struct{}, 1)
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				fmt.Fprintf(w, ": heartbeat\n\n")
				flusher.Flush()
			case <-firstContent:
				return
			case <-heartbeatDone:
				return
			}
		}
	}()
	defer close(heartbeatDone)

	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()

	hasSentContent := false
	cb := func(ev agent.StreamEvent) {
		if !hasSentContent {
			hasSentContent = true
			close(firstContent)
		}
		switch ev.Type {
		case "thought_chunk":
			sendSSE("thought", ev.Data)
		case "step_start":
			sendSSE("step", ev.Data)
		case "step_chunk":
			sendSSE("step_output", ev.Data)
		case "step_done":
			sendSSE("step_end", ev.Data)
		case "result_chunk":
			sendSSE("result", ev.Data)
		case "result":
			sendSSE("result", ev.Data)
		case "thinking":
			sendSSE("status", ev.Data)
		case "error":
			sendSSE("error", ev.Data)
		case "done":
			sendSSE("done", "")
		default:
			js, _ := json.Marshal(ev)
			if js != nil {
				sendSSE(ev.Type, string(js))
			}
		}
	}

	_, err := g.Agent.ThinkStream(ctx, &req, cb)
	if err != nil {
		logWithTimestamp("[Agent] ❌ Stream failed: %v", err)
		sendSSE("error", fmt.Sprintf("内部错误: %v", err))
		sendSSE("done", "")
		return
	}

	logWithTimestamp("[Agent] ✅ Stream complete: session=%s", req.SessionID)
}

// handleAIPage — 独立 AI 对话页面
func (g *OpcGateway) handleAIPage(w http.ResponseWriter, r *http.Request) {
	webDir := filepath.Join(filepath.Dir(os.Args[0]), "..", "web")
	if _, err := os.Stat(webDir); os.IsNotExist(err) {
		webDir = "web"
	}
	htmlPath := filepath.Join(webDir, "ai.html")

	html, err := os.ReadFile(htmlPath)
	if err != nil {
		http.Error(w, "⚠️ 页面文件未找到: "+htmlPath, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(html)
}
