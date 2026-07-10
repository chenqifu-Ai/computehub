// Package gateway — 统一 Agent API 入口
// 让其他 OpenClaw Agent 通过一个入口调用集群所有能力
//
// 端点:
//   POST /api/v1/agent/exec     — 在指定节点执行命令
//   POST /api/v1/agent/chat     — 调用本地 Ollama 模型
//   POST /api/v1/agent/llm      — 调用 NewAPI LLM
//   GET  /api/v1/agent/status   — 集群状态总览
//   POST /api/v1/agent/upload   — 上传文件到 Gallery
//
// 认证: X-Agent-Key Header（配置在 config.json → gateway.agent_keys）

package gateway

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

// =============================================================================
// Agent API Key 认证
// =============================================================================

var agentKeys map[string]string

func SetAgentKeys(keys map[string]string) {
	agentKeys = keys
}

func verifyAgentKey(r *http.Request) (string, bool) {
	if len(agentKeys) == 0 {
		return "anonymous", true
	}
	key := r.Header.Get("X-Agent-Key")
	if key == "" {
		return "", false
	}
	for name, k := range agentKeys {
		if k == key {
			return name, true
		}
	}
	return "", false
}

// =============================================================================
// 统一响应格式
// =============================================================================

type agentAPIResponse struct {
	Success  bool        `json:"success"`
	Agent    string      `json:"agent,omitempty"`
	Endpoint string      `json:"endpoint,omitempty"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
}

func writeAgentJSON(w http.ResponseWriter, resp agentAPIResponse) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// =============================================================================
// POST /api/v1/agent/exec — 远程执行命令
// =============================================================================

type agentExecRequest struct {
	Node    string `json:"node"`
	Command string `json:"command"`
	Timeout int    `json:"timeout,omitempty"`
}

func (g *OpcGateway) handleAgentExec(w http.ResponseWriter, r *http.Request) {
	agentName, ok := verifyAgentKey(r)
	if !ok {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "unauthorized: missing or invalid X-Agent-Key"})
		return
	}
	if r.Method != http.MethodPost {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "only POST allowed"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "read body failed"})
		return
	}
	defer r.Body.Close()

	var req agentExecRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("invalid JSON: %v", err)})
		return
	}
	if req.Node == "" || req.Command == "" {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "node and command are required"})
		return
	}
	if req.Timeout <= 0 {
		req.Timeout = 60
	}
	if req.Timeout > 300 {
		req.Timeout = 300
	}

	logWithTimestamp("[Agent API] %s exec on %s: %s", agentName, req.Node, truncateStr(req.Command, 100))

	// Use the existing dispatch mechanism
	respChan := g.Kernel.DispatchExtended("agent-exec", req.Command, map[string]interface{}{
		"node_id": req.Node,
		"timeout": req.Timeout,
	})

	select {
	case resp := <-respChan:
		writeAgentJSON(w, agentAPIResponse{
			Success: true, Agent: agentName, Endpoint: "exec",
			Data: map[string]interface{}{
				"node":     req.Node,
				"command":  req.Command,
				"stdout":   resp.Data,
				"error":    fmt.Sprintf("%v", resp.Error),
				"duration": resp.Duration,
			},
		})
	case <-time.After(time.Duration(req.Timeout) * time.Second):
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "exec timed out", Agent: agentName, Endpoint: "exec"})
	}
}

// =============================================================================
// POST /api/v1/agent/chat — 调用本地 Ollama 模型
// =============================================================================

type agentChatRequest struct {
	Model   string `json:"model"`
	Prompt  string `json:"prompt"`
	Stream  bool   `json:"stream,omitempty"`
	Timeout int    `json:"timeout,omitempty"`
}

func (g *OpcGateway) handleAgentChat(w http.ResponseWriter, r *http.Request) {
	agentName, ok := verifyAgentKey(r)
	if !ok {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "unauthorized"})
		return
	}
	if r.Method != http.MethodPost {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "only POST allowed"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "read body failed"})
		return
	}
	defer r.Body.Close()

	var req agentChatRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("invalid JSON: %v", err)})
		return
	}
	if req.Model == "" || req.Prompt == "" {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "model and prompt are required"})
		return
	}
	if req.Timeout <= 0 {
		req.Timeout = 120
	}

	logWithTimestamp("[Agent API] %s chat: model=%s", agentName, req.Model)

	ollamaReq := map[string]interface{}{
		"model":  req.Model,
		"prompt": req.Prompt,
		"stream": false,
	}
	reqBody, _ := json.Marshal(ollamaReq)

	client := &http.Client{Timeout: time.Duration(req.Timeout) * time.Second}
	resp, err := client.Post("http://127.0.0.1:11434/api/generate", "application/json", bytes.NewReader(reqBody))
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("ollama call failed: %v", err), Agent: agentName, Endpoint: "chat"})
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	var result struct {
		Response      string `json:"response"`
		EvalCount     int    `json:"eval_count"`
		TotalDuration int64  `json:"total_duration"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("ollama parse failed: %v", err), Agent: agentName, Endpoint: "chat"})
		return
	}

	writeAgentJSON(w, agentAPIResponse{
		Success: true, Agent: agentName, Endpoint: "chat",
		Data: map[string]interface{}{
			"model":       req.Model,
			"response":    result.Response,
			"tokens":      result.EvalCount,
			"duration_ms": result.TotalDuration / 1e6,
		},
	})
}

// =============================================================================
// POST /api/v1/agent/llm — 调用 NewAPI LLM
// =============================================================================

type agentLlmRequest struct {
	Model    string `json:"model"`
	Messages []struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	} `json:"messages"`
	Stream  bool `json:"stream,omitempty"`
	Timeout int  `json:"timeout,omitempty"`
}

func (g *OpcGateway) handleAgentLlm(w http.ResponseWriter, r *http.Request) {
	agentName, ok := verifyAgentKey(r)
	if !ok {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "unauthorized"})
		return
	}
	if r.Method != http.MethodPost {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "only POST allowed"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "read body failed"})
		return
	}
	defer r.Body.Close()

	var req agentLlmRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("invalid JSON: %v", err)})
		return
	}
	if req.Model == "" || len(req.Messages) == 0 {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "model and messages are required"})
		return
	}
	if req.Timeout <= 0 {
		req.Timeout = 120
	}

	logWithTimestamp("[Agent API] %s llm: model=%s messages=%d", agentName, req.Model, len(req.Messages))

	llmBody, _ := json.Marshal(map[string]interface{}{
		"model":    req.Model,
		"messages": req.Messages,
		"stream":   false,
	})

	client := &http.Client{Timeout: time.Duration(req.Timeout) * time.Second}
	resp, err := client.Post("http://127.0.0.1:8282/api/v1/llm/chat/completions", "application/json", bytes.NewReader(llmBody))
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("LLM call failed: %v", err), Agent: agentName, Endpoint: "llm"})
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	var llmResult map[string]interface{}
	if json.Unmarshal(respBody, &llmResult) == nil {
		writeAgentJSON(w, agentAPIResponse{Success: true, Agent: agentName, Endpoint: "llm", Data: llmResult})
		return
	}
	writeAgentJSON(w, agentAPIResponse{Success: true, Agent: agentName, Endpoint: "llm", Data: string(respBody)})
}

// =============================================================================
// GET /api/v1/agent/status — 集群状态总览
// =============================================================================

func (g *OpcGateway) handleAgentStatus(w http.ResponseWriter, r *http.Request) {
	agentName, ok := verifyAgentKey(r)
	if !ok {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "unauthorized"})
		return
	}

	nodes := make([]map[string]interface{}, 0)
	onlineCount := 0

	if g.Kernel != nil && g.Kernel.NodeMgr != nil {
		for _, state := range g.Kernel.NodeMgr.ListNodes() {
			reg := state.Register
			if reg == nil {
				continue
			}
			status := reg.Status
			if status == "online" {
				onlineCount++
			}
			nodes = append(nodes, map[string]interface{}{
				"id":       reg.NodeID,
				"status":   status,
				"version":  reg.Version,
				"platform": reg.Platform,
				"gpu":      reg.GPUType,
				"ip":       reg.IPAddress,
				"type":     reg.NodeType,
			})
		}
	}

	// Ollama 模型
	models := make([]string, 0)
	client := &http.Client{Timeout: 3 * time.Second}
	if resp, err := client.Get("http://127.0.0.1:11434/api/tags"); err == nil {
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		var tagResult struct {
			Models []struct {
				Name string `json:"name"`
			} `json:"models"`
		}
		if json.Unmarshal(body, &tagResult) == nil {
			for _, m := range tagResult.Models {
				models = append(models, m.Name)
			}
		}
	}

	writeAgentJSON(w, agentAPIResponse{
		Success: true, Agent: agentName, Endpoint: "status",
		Data: map[string]interface{}{
			"cluster": map[string]interface{}{
				"nodes":      nodes,
				"node_count": len(nodes),
				"online":     onlineCount,
			},
			"ollama": map[string]interface{}{
				"running": len(models) > 0,
				"models":  models,
			},
			"gateway": map[string]interface{}{
				"uptime": time.Since(g.startTime).String(),
			},
		},
	})
}

// =============================================================================
// POST /api/v1/agent/upload — 上传文件到 Gallery
// =============================================================================

func (g *OpcGateway) handleAgentUpload(w http.ResponseWriter, r *http.Request) {
	agentName, ok := verifyAgentKey(r)
	if !ok {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "unauthorized"})
		return
	}
	if r.Method != http.MethodPost {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: "only POST allowed"})
		return
	}

	r.Body = http.MaxBytesReader(w, r.Body, 50<<20)
	if err := r.ParseMultipartForm(50 << 20); err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("parse form failed: %v", err), Agent: agentName, Endpoint: "upload"})
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("file field required: %v", err), Agent: agentName, Endpoint: "upload"})
		return
	}
	defer file.Close()

	filename := header.Filename
	logWithTimestamp("[Agent API] %s upload: %s (%d bytes)", agentName, filename, header.Size)

	galleryDir := "/home/computehub/gallery"
	os.MkdirAll(galleryDir, 0755)
	dst, err := os.Create(filepath.Join(galleryDir, filename))
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("create file failed: %v", err), Agent: agentName, Endpoint: "upload"})
		return
	}
	defer dst.Close()

	written, err := io.Copy(dst, file)
	if err != nil {
		writeAgentJSON(w, agentAPIResponse{Success: false, Error: fmt.Sprintf("write failed: %v", err), Agent: agentName, Endpoint: "upload"})
		return
	}

	writeAgentJSON(w, agentAPIResponse{
		Success: true, Agent: agentName, Endpoint: "upload",
		Data: map[string]interface{}{
			"filename": filename,
			"size":     written,
			"url":      fmt.Sprintf("/api/v1/files/%s", filename),
		},
	})
}
