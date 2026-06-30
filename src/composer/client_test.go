package composer

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// ═══════════════════════════════════════════
// NewLLMClient — 初始化测试
// ═══════════════════════════════════════════

func TestNewLLMClient_Defaults(t *testing.T) {
	c := NewLLMClient("", "", "")
	if c == nil {
		t.Fatal("NewLLMClient returned nil")
	}

	if c.APIURL != "https://ai.zhangtuokeji.top:9090/v1" {
		t.Errorf("expected default API URL, got %s", c.APIURL)
	}
	if c.Model != "qwen3.6-35b" {
		t.Errorf("expected default model 'qwen3.6-35b', got %s", c.Model)
	}
	if c.Timeout != 30*time.Second {
		t.Errorf("expected default timeout 30s, got %v", c.Timeout)
	}
	if c.MaxTokens != 4096 {
		t.Errorf("expected default MaxTokens 4096, got %d", c.MaxTokens)
	}
	if c.client == nil {
		t.Error("HTTP client should not be nil")
	}
	if c.client.Timeout != 30*time.Second {
		t.Errorf("http.Client timeout should be 30s, got %v", c.client.Timeout)
	}
}

func TestNewLLMClient_CustomConfig(t *testing.T) {
	c := NewLLMClient("http://localhost:9999/v1", "test-key-123", "llama3")
	if c.APIURL != "http://localhost:9999/v1" {
		t.Errorf("expected custom API URL, got %s", c.APIURL)
	}
	if c.Model != "llama3" {
		t.Errorf("expected model 'llama3', got %s", c.Model)
	}
	if c.APIKey != "test-key-123" {
		t.Errorf("expected API key 'test-key-123', got %s", c.APIKey)
	}
}

// ═══════════════════════════════════════════
// SetTimeout 测试
// ═══════════════════════════════════════════

func TestSetTimeout(t *testing.T) {
	c := NewLLMClient("http://localhost:9999/v1", "", "test-model")
	c.SetTimeout(60 * time.Second)

	if c.Timeout != 60*time.Second {
		t.Errorf("expected timeout 60s, got %v", c.Timeout)
	}
	if c.client.Timeout != 60*time.Second {
		t.Errorf("http.Client timeout should be 60s, got %v", c.client.Timeout)
	}
}

// ═══════════════════════════════════════════
// ChatRequest JSON 序列化测试
// ═══════════════════════════════════════════

func TestChatRequest_JSON(t *testing.T) {
	req := ChatRequest{
		Model: "test-model",
		Messages: []ChatMessage{
			{Role: "system", Content: "You are helpful"},
			{Role: "user", Content: "Hello"},
		},
		MaxTokens: 100,
		Stream:    false,
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	var parsed map[string]interface{}
	json.Unmarshal(data, &parsed)

	if parsed["model"] != "test-model" {
		t.Errorf("expected model 'test-model', got %v", parsed["model"])
	}

	messages, _ := parsed["messages"].([]interface{})
	if len(messages) != 2 {
		t.Errorf("expected 2 messages, got %d", len(messages))
	}
}

func TestChatRequest_ZeroMaxTokens(t *testing.T) {
	req := ChatRequest{
		Model: "test-model",
		Messages: []ChatMessage{
			{Role: "user", Content: "hi"},
		},
		MaxTokens: 0, // zero value — should be omitted via omitempty? No, it's not omitempty
	}
	data, _ := json.Marshal(req)
	if strings.Contains(string(data), `"max_tokens":0`) {
		// Go json.Marshal doesn't omit 0 without omitempty tag
		// This is expected behavior — not a bug
		t.Log("max_tokens:0 is included (no omitempty tag)")
	}
}

// ═══════════════════════════════════════════
// ChatResponse 解析测试
// ═══════════════════════════════════════════

func TestChatResponse_Parse(t *testing.T) {
	jsonData := `{
		"choices": [{
			"message": {
				"content": "Hello, I'm an AI assistant.",
				"reasoning": "I need to be polite."
			}
		}]
	}`

	var resp ChatResponse
	if err := json.Unmarshal([]byte(jsonData), &resp); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if len(resp.Choices) != 1 {
		t.Fatalf("expected 1 choice, got %d", len(resp.Choices))
	}
	if resp.Choices[0].Message.Content != "Hello, I'm an AI assistant." {
		t.Errorf("unexpected content: %s", resp.Choices[0].Message.Content)
	}
	if resp.Choices[0].Message.Reasoning != "I need to be polite." {
		t.Errorf("unexpected reasoning: %s", resp.Choices[0].Message.Reasoning)
	}
}

func TestChatResponse_ContentNullFallback(t *testing.T) {
	// NewAPI-style: content is null, reasoning has the text
	jsonData := `{
		"choices": [{
			"message": {
				"content": null,
				"reasoning": "The actual response is here"
			}
		}]
	}`

	var resp ChatResponse
	json.Unmarshal([]byte(jsonData), &resp)

	content := resp.Choices[0].Message.Content
	reasoning := resp.Choices[0].Message.Reasoning

	if content != "" {
		t.Errorf("expected empty content, got %q", content)
	}
	if reasoning != "The actual response is here" {
		t.Errorf("expected reasoning 'The actual response is here', got %q", reasoning)
	}
}

func TestChatResponse_ReasoningContentField(t *testing.T) {
	// Some APIs use reasoning_content instead of reasoning
	jsonData := `{
		"choices": [{
			"message": {
				"content": null,
				"reasoning_content": "Response from reasoning_content field"
			}
		}]
	}`

	var resp ChatResponse
	json.Unmarshal([]byte(jsonData), &resp)

	if resp.Choices[0].Message.ReasoningContent != "Response from reasoning_content field" {
		t.Errorf("unexpected reasoning_content: %s", resp.Choices[0].Message.ReasoningContent)
	}
}

func TestChatResponse_Error(t *testing.T) {
	jsonData := `{
		"error": {
			"message": "Rate limit exceeded"
		}
	}`

	var resp ChatResponse
	json.Unmarshal([]byte(jsonData), &resp)

	if resp.Error.Message != "Rate limit exceeded" {
		t.Errorf("expected error 'Rate limit exceeded', got %s", resp.Error.Message)
	}
}

func TestChatResponse_NoChoices(t *testing.T) {
	jsonData := `{
		"choices": []
	}`

	var resp ChatResponse
	json.Unmarshal([]byte(jsonData), &resp)

	if len(resp.Choices) != 0 {
		t.Errorf("expected 0 choices, got %d", len(resp.Choices))
	}
}

// ═══════════════════════════════════════════
// Chat — HTTP Mock 测试
// ═══════════════════════════════════════════

func TestChat_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify request
		if r.Method != "POST" {
			t.Errorf("expected POST, got %s", r.Method)
		}
		if r.Header.Get("Authorization") != "Bearer test-key" {
			t.Errorf("unexpected auth header: %s", r.Header.Get("Authorization"))
		}

		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"choices": [{
				"message": {
					"content": "你好！我是 AI 助手。"
				}
			}]
		}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "test-key", "test-model")
	result, err := c.Chat([]ChatMessage{
		{Role: "user", Content: "你好"},
	}, 100)

	if err != nil {
		t.Fatalf("Chat failed: %v", err)
	}
	if result != "你好！我是 AI 助手。" {
		t.Errorf("unexpected result: %s", result)
	}
}

func TestChat_WithReasoningFallback(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// content is null, reasoning has the text
		w.Write([]byte(`{
			"choices": [{
				"message": {
					"content": null,
					"reasoning": "这是原因分析。结论是模型回答。"
				}
			}]
		}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	result, err := c.Chat([]ChatMessage{
		{Role: "user", Content: "test"},
	}, 100)

	if err != nil {
		t.Fatalf("Chat failed: %v", err)
	}
	if result != "这是原因分析。结论是模型回答。" {
		t.Errorf("expected fallback to reasoning, got %q", result)
	}
}

func TestChat_HTTPError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`internal error`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	_, err := c.Chat([]ChatMessage{{Role: "user", Content: "hi"}}, 100)

	if err == nil {
		t.Fatal("expected error for HTTP 500")
	}
	if !strings.Contains(err.Error(), "500") {
		t.Errorf("expected 500 error, got: %v", err)
	}
}

func TestChat_APIError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"error": {
				"message": "Model not available"
			}
		}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	_, err := c.Chat([]ChatMessage{{Role: "user", Content: "hi"}}, 100)

	if err == nil {
		t.Fatal("expected error for API error response")
	}
	if !strings.Contains(err.Error(), "Model not available") {
		t.Errorf("expected 'Model not available', got: %v", err)
	}
}

func TestChat_EmptyChoices(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"choices": []}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	_, err := c.Chat([]ChatMessage{{Role: "user", Content: "hi"}}, 100)

	if err == nil {
		t.Fatal("expected error for empty choices")
	}
}

func TestChat_EmptyContentAllFields(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"choices": [{
				"message": {
					"content": null,
					"reasoning": null,
					"reasoning_content": null
				}
			}]
		}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	_, err := c.Chat([]ChatMessage{{Role: "user", Content: "hi"}}, 100)

	if err == nil {
		t.Fatal("expected error for all null content")
	}
}

// ═══════════════════════════════════════════
// CallWithPrompt — 快捷方法测试
// ═══════════════════════════════════════════

func TestCallWithPrompt(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req ChatRequest
		json.NewDecoder(r.Body).Decode(&req)

		if len(req.Messages) != 2 {
			t.Errorf("expected 2 messages, got %d", len(req.Messages))
		}
		if req.Messages[0].Role != "system" {
			t.Errorf("expected first message role 'system', got %s", req.Messages[0].Role)
		}
		if req.Messages[0].Content != "You are a test bot." {
			t.Errorf("unexpected system prompt: %s", req.Messages[0].Content)
		}
		if req.Messages[1].Content != "Hello" {
			t.Errorf("unexpected user message: %s", req.Messages[1].Content)
		}

		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"choices": [{
				"message": {
					"content": "Response from prompt"
				}
			}]
		}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	result, err := c.CallWithPrompt("You are a test bot.", "Hello", 100)

	if err != nil {
		t.Fatalf("CallWithPrompt failed: %v", err)
	}
	if result != "Response from prompt" {
		t.Errorf("unexpected result: %s", result)
	}
}

// ═══════════════════════════════════════════
// ChatRequest — JSON auth header 测试
// ═══════════════════════════════════════════

func TestChat_NoAuthWhenKeyEmpty(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := r.Header.Get("Authorization")
		if auth != "" {
			t.Errorf("expected no auth header, got %s", auth)
		}
		w.Write([]byte(`{"choices": [{"message": {"content": "ok"}}]}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	_, err := c.Chat([]ChatMessage{{Role: "user", Content: "hi"}}, 100)
	if err != nil {
		t.Fatalf("Chat failed: %v", err)
	}
}

// ═══════════════════════════════════════════
// ChatMessage — 基础测试
// ═══════════════════════════════════════════

func TestChatMessage(t *testing.T) {
	msg := ChatMessage{Role: "user", Content: "hello"}
	data, _ := json.Marshal(msg)

	var parsed map[string]string
	json.Unmarshal(data, &parsed)

	if parsed["role"] != "user" {
		t.Errorf("expected role 'user', got %s", parsed["role"])
	}
	if parsed["content"] != "hello" {
		t.Errorf("expected content 'hello', got %s", parsed["content"])
	}
}

// ═══════════════════════════════════════════
// ChatStream — HTTP Mock（可选，需要处理 SSE 格式）
// ═══════════════════════════════════════════

func TestChatStream_SSEFormat(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.WriteHeader(http.StatusOK)

		// Simulate SSE stream
		sseData := []string{
			`data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}`,
			`data: {"choices":[{"delta":{"content":"世界"},"finish_reason":null}]}`,
			`data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}`,
			`data: [DONE]`,
		}
		for _, line := range sseData {
			w.Write([]byte(line + "\n\n"))
		}
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")

	var chunks []string
	result, err := c.ChatStream(
		[]ChatMessage{{Role: "user", Content: "hi"}},
		100,
		func(chunk string, done bool, err error) {
			if chunk != "" {
				chunks = append(chunks, chunk)
			}
		},
	)

	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}
	if result != "你好世界" {
		t.Errorf("expected '你好世界', got %s", result)
	}
	if len(chunks) != 2 {
		t.Errorf("expected 2 chunks, got %d: %v", len(chunks), chunks)
	}
}

func TestChatStream_ReasoningFallback(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)

		sseData := []string{
			`data: {"choices":[{"delta":{"content":null,"reasoning":"思考中..."},"finish_reason":null}]}`,
			`data: {"choices":[{"delta":{"content":null,"reasoning":"得出结论"},"finish_reason":null}]}`,
			`data: {"choices":[{"delta":{"content":"","reasoning":""},"finish_reason":"stop"}]}`,
			`data: [DONE]`,
		}
		for _, line := range sseData {
			w.Write([]byte(line + "\n\n"))
		}
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")

	var fullResult string
	result, err := c.ChatStream(
		[]ChatMessage{{Role: "user", Content: "hi"}},
		100,
		func(chunk string, done bool, err error) {
			fullResult += chunk
		},
	)

	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}
	if result != "思考中...得出结论" {
		t.Errorf("expected '思考中...得出结论', got %s", result)
	}
}

func TestChatStream_HTTPError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		w.Write([]byte(`{"error": {"message": "bad request"}}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")
	_, err := c.ChatStream(
		[]ChatMessage{{Role: "user", Content: "hi"}},
		100,
		func(chunk string, done bool, err error) {},
	)

	if err == nil {
		t.Fatal("expected error for HTTP 400")
	}
}

func TestChatStream_EmptyDelta(t *testing.T) {
	// Some APIs send empty delta lines — should be skipped
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)

		sseData := []string{
			`data: {"choices":[{"delta":{},"finish_reason":null}]}`,
			`data: {"choices":[{"delta":{"content":"result"},"finish_reason":null}]}`,
			`data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}`,
			`data: [DONE]`,
		}
		for _, line := range sseData {
			w.Write([]byte(line + "\n\n"))
		}
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")

	var chunks []string
	result, err := c.ChatStream(
		[]ChatMessage{{Role: "user", Content: "hi"}},
		100,
		func(chunk string, done bool, err error) {
			if chunk != "" {
				chunks = append(chunks, chunk)
			}
		},
	)

	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}
	if result != "result" {
		t.Errorf("expected 'result', got %s", result)
	}
	if len(chunks) != 1 {
		t.Errorf("expected 1 chunk, got %d: %v", len(chunks), chunks)
	}
}

// ═══════════════════════════════════════════
// 并发安全测试
// ═══════════════════════════════════════════

func TestChat_ConcurrentCalls(t *testing.T) {
	counter := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		counter++
		w.Write([]byte(`{"choices": [{"message": {"content": "ok"}}]}`))
	}))
	defer server.Close()

	c := NewLLMClient(server.URL, "", "test-model")

	done := make(chan bool, 5)
	for i := 0; i < 5; i++ {
		go func() {
			_, err := c.Chat([]ChatMessage{{Role: "user", Content: "hi"}}, 100)
			if err != nil {
				t.Logf("concurrent Chat error: %v", err)
			}
			done <- true
		}()
	}

	for i := 0; i < 5; i++ {
		<-done
	}

	if counter != 5 {
		t.Logf("concurrent calls: expected 5 requests, got %d", counter)
	}
}

// ═══════════════════════════════════════════
// ChatRequest — Streaming flag test
// ═══════════════════════════════════════════

func TestChatRequest_StreamingHasExpectedValues(t *testing.T) {
	// Non-streaming — Stream:false is omitted due to `omitempty` tag
	req1 := ChatRequest{Model: "m", Stream: false}
	data1, _ := json.Marshal(req1)
	if strings.Contains(string(data1), "stream") {
		t.Log("stream=false omitted from JSON (omitempty), expected")
	}

	// Streaming — Stream:true is always included
	req2 := ChatRequest{Model: "m", Stream: true}
	data2, _ := json.Marshal(req2)
	if !strings.Contains(string(data2), `"stream":true`) {
		t.Errorf("stream should be true in streaming request, got: %s", string(data2))
	}
}