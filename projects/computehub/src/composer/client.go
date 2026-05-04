// Package composer — LLM API 客户端
// 对接 NewAPI (ai.zhangtuokeji.top) / Ollama / 任意 OpenAI-compatible API
package composer

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
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
func NewLLMClient(apiURL, apiKey, model string) *LLMClient {
	if apiURL == "" {
		apiURL = "https://ai.zhangtuokeji.top:9090/v1"
	}
	if model == "" {
		model = "qwen3.6-35b-common"
	}
	return &LLMClient{
		APIURL:    apiURL,
		APIKey:    apiKey,
		Model:     model,
		Timeout:   30 * time.Second,
		MaxTokens: 4096,
		client:    &http.Client{Timeout: 30 * time.Second},
	}
}

// ChatMessage OpenAI 格式消息
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatRequest 请求体
type ChatRequest struct {
	Model     string        `json:"model"`
	Messages  []ChatMessage `json:"messages"`
	MaxTokens int           `json:"max_tokens,omitempty"`
	Stream    bool          `json:"stream,omitempty"`
}

// ChatResponse 响应体
type ChatResponse struct {
	Choices []struct {
		Message struct {
			Content   string `json:"content"`
			Reasoning string `json:"reasoning,omitempty"`
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

	reqBody := ChatRequest{
		Model:     c.Model,
		Messages:  messages,
		MaxTokens: maxTokens,
		Stream:    false,
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
		return "", fmt.Errorf("empty response content")
	}

	return content, nil
}

// CallWithPrompt 快捷方法：给一条 system + user 消息
func (c *LLMClient) CallWithPrompt(system, user string, maxTokens int) (string, error) {
	messages := []ChatMessage{
		{Role: "system", Content: system},
		{Role: "user", Content: user},
	}
	return c.Chat(messages, maxTokens)
}
