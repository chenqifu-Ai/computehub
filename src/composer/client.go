// Package composer — LLM API 客户端
// 对接 NewAPI (ai.zhangtuokeji.top) / Ollama / 任意 OpenAI-compatible API
package composer

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"runtime"
	"strings"
	"time"
)

// LLMClient 通用 LLM API 客户端
type LLMClient struct {
	APIURL    string
	APIKey    string
	Model     string
	Timeout   time.Duration
	MaxTokens int
	client    *http.Client
}

// NewLLMClient 创建客户端
// 优先从传入参数获取，为空时使用硬编码默认值
func NewLLMClient(apiURL, apiKey, model string) *LLMClient {
	if apiURL == "" {
		apiURL = "https://ai.zhangtuokeji.top:9090/v1"
	}
	if model == "" {
		model = "gemma4:31b"
	}
	// 标准 HTTP transport（允许 HTTP/2 协商，NewAPI 的 HTTP/2 更稳定）
	// DNS 解析策略：
	//   Android（Termux）：自定义 8.8.8.8 DNS（设备无本地 DNS 服务器）
	//   其他平台（Linux/ECS/Windows/Mac）：走系统 DNS
	var transport *http.Transport
	if runtime.GOOS == "android" {
		resolver := &net.Resolver{
			PreferGo: true,
			Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
				d := net.Dialer{}
				return d.DialContext(ctx, "udp", "8.8.8.8:53")
			},
		}
		dialer := &net.Dialer{
			Timeout:  5 * time.Second,
			Resolver: resolver,
		}
		transport = &http.Transport{
			MaxIdleConns:        10,
			IdleConnTimeout:     90 * time.Second,
			TLSHandshakeTimeout: 10 * time.Second,
			DialContext:         dialer.DialContext,
		}
	} else {
		dialer := &net.Dialer{Timeout: 5 * time.Second}
		transport = &http.Transport{
			MaxIdleConns:        10,
			IdleConnTimeout:     90 * time.Second,
			TLSHandshakeTimeout: 10 * time.Second,
			DialContext:         dialer.DialContext,
		}
	}
	return &LLMClient{
		APIURL:    apiURL,
		APIKey:    apiKey,
		Model:     model,
		Timeout:   30 * time.Second,
		MaxTokens: 4096,
		client:    &http.Client{Timeout: 30 * time.Second, Transport: transport},
	}
}

// ChatMessage OpenAI 格式消息
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// SetTimeout 设置客户端超时（同时更新 Timeout 字段和 http.Client）
func (c *LLMClient) SetTimeout(d time.Duration) {
	c.Timeout = d
	if c.client != nil {
		c.client.Timeout = d
	}
}

// ChatRequest 请求体
type ChatRequest struct {
	Model     string        `json:"model"`
	Messages  []ChatMessage `json:"messages"`
	MaxTokens int           `json:"max_tokens,omitempty"`
	Stream    bool          `json:"stream,omitempty"`
	Reasoning *bool         `json:"reasoning,omitempty"`
}

// ChatResponse 响应体
type ChatResponse struct {
	Choices []struct {
		Message struct {
			Content          string `json:"content"`
			Reasoning        string `json:"reasoning,omitempty"`
			ReasoningContent string `json:"reasoning_content,omitempty"`
		} `json:"message"`
	} `json:"choices"`
	Error struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// Chat 发送对话请求
func (c *LLMClient) Chat(messages []ChatMessage, maxTokens int) (string, error) {
	if maxTokens <= 0 {
		maxTokens = c.MaxTokens
	}

	reasoning := false
	reqBody := ChatRequest{
		Model:     c.Model,
		Messages:  messages,
		MaxTokens: maxTokens,
		Stream:    false,
		Reasoning: &reasoning,
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequest("POST", c.APIURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("api call: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("api error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	var chatResp ChatResponse
	if err := json.Unmarshal(respBody, &chatResp); err != nil {
		return "", fmt.Errorf("parse response: %w", err)
	}

	if chatResp.Error.Message != "" {
		return "", fmt.Errorf("api error: %s", chatResp.Error.Message)
	}

	if len(chatResp.Choices) == 0 {
		return "", fmt.Errorf("empty response (no choices)")
	}

	// NewAPI 的 content 可能为 null，fallback 到 reasoning
	content := chatResp.Choices[0].Message.Content
	if content == "" {
		content = chatResp.Choices[0].Message.Reasoning
	}
	if content == "" {
		content = chatResp.Choices[0].Message.ReasoningContent
	}
	if content == "" {
		return "", fmt.Errorf("empty response content")
	}

	return content, nil
}

// CallWithPrompt 快捷方法
func (c *LLMClient) CallWithPrompt(system, user string, maxTokens int) (string, error) {
	messages := []ChatMessage{
		{Role: "system", Content: system},
		{Role: "user", Content: user},
	}
	return c.Chat(messages, maxTokens)
}

// ── 流式聊天 ──

// ChatStreamCallback 流式回调
type ChatStreamCallback func(chunk string, done bool, err error)

// ChatStream 流式对话 — 通过回调逐步推送
// 兼容 OpenAI SSE 格式和 NewAPI reasoning 字段
func (c *LLMClient) ChatStream(messages []ChatMessage, maxTokens int, cb ChatStreamCallback) (string, error) {
	if maxTokens <= 0 {
		maxTokens = c.MaxTokens
	}

	reasoning := false
	reqBody := ChatRequest{
		Model:     c.Model,
		Messages:  messages,
		MaxTokens: maxTokens,
		Stream:    true,
		Reasoning: &reasoning,
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequest("POST", c.APIURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("api call: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		respBody, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("api error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	var fullText strings.Builder
	reader := bufio.NewReader(resp.Body)

	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				break
			}
			return fullText.String(), fmt.Errorf("read stream: %w", err)
		}

		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		if !strings.HasPrefix(line, "data: ") {
			continue
		}

		data := strings.TrimPrefix(line, "data: ")
		if data == "[DONE]" {
			break
		}

		var streamResp struct {
			Choices []struct {
				Delta struct {
					Content          string `json:"content"`
					Reasoning        string `json:"reasoning,omitempty"`
					ReasoningContent string `json:"reasoning_content,omitempty"`
				} `json:"delta"`
				FinishReason *string `json:"finish_reason"`
			} `json:"choices"`
		}

		if err := json.Unmarshal([]byte(data), &streamResp); err != nil {
			continue
		}

		if len(streamResp.Choices) == 0 {
			continue
		}

		delta := streamResp.Choices[0].Delta
		chunk := delta.Content
		if chunk == "" {
			chunk = delta.Reasoning
		}
		if chunk == "" {
			chunk = delta.ReasoningContent
		}

		if chunk != "" {
			fullText.WriteString(chunk)
			cb(chunk, false, nil)
		}

		if streamResp.Choices[0].FinishReason != nil && *streamResp.Choices[0].FinishReason == "stop" {
			break
		}
	}

	result := fullText.String()
	cb("", true, nil)
	return result, nil
}
