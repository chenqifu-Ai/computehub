#!/usr/bin/env python3
"""
ComputeHub 模型故障自动切换模块

功能：
1. 多模型健康检查
2. 自动故障切换
3. 降级策略
4. 恢复检测

执行者：小智 AI 助手
时间：2026-04-22 15:41
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# === 配置 ===
GO_ORCHESTRATION = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go")
MODELS_DIR = GO_ORCHESTRATION / "internal" / "models"

# === 颜色输出 ===
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": Colors.BLUE, "SUCCESS": Colors.GREEN, "WARNING": Colors.YELLOW, "ERROR": Colors.RED}
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def create_model_failover():
    log("=" * 60, "INFO")
    log("ComputeHub 模型故障自动切换模块", "INFO")
    log("=" * 60, "INFO")
    
    # 1. 创建目录
    log("步骤 1: 创建模型模块目录", "INFO")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    log(f"  ✅ 创建 {MODELS_DIR}", "SUCCESS")
    
    # 2. 创建模型故障切换核心
    log("步骤 2: 创建故障切换核心", "INFO")
    failover_go = '''package models

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

// ModelEndpoint 模型端点
type ModelEndpoint struct {
	Name        string            `json:"name"`
	URL         string            `json:"url"`
	Model       string            `json:"model"`
	APIKey      string            `json:"api_key,omitempty"`
	Priority    int               `json:"priority"` // 数字越小优先级越高
	TimeoutSecs int               `json:"timeout_secs"`
	Healthy     bool              `json:"healthy"`
	LastCheck   time.Time         `json:"last_check"`
	Failures    int               `json:"failures"`
	Successes   int               `json:"successes"`
	Metadata    map[string]string `json:"metadata"`
}

// ModelRouter 模型路由器（带故障切换）
type ModelRouter struct {
	mu              sync.RWMutex
	endpoints       []*ModelEndpoint
	currentIndex    int
	config          *RouterConfig
	healthCheckStop chan struct{}
}

// RouterConfig 路由器配置
type RouterConfig struct {
	HealthCheckInterval time.Duration `json:"health_check_interval"`
	MaxFailures         int           `json:"max_failures"`
	RecoveryThreshold   int           `json:"recovery_threshold"` // 连续成功多少次恢复健康
	EnableAutoFailover  bool          `json:"enable_auto_failover"`
	EnableHealthCheck   bool          `json:"enable_health_check"`
}

// DefaultConfig 默认配置
func DefaultConfig() *RouterConfig {
	return &RouterConfig{
		HealthCheckInterval: 10 * time.Second,
		MaxFailures:         3,
		RecoveryThreshold:   2,
		EnableAutoFailover:  true,
		EnableHealthCheck:   true,
	}
}

// ChatRequest 聊天请求
type ChatRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream,omitempty"`
}

// Message 消息
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatResponse 聊天响应
type ChatResponse struct {
	ID      string   `json:"id"`
	Model   string   `json:"model"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}

// Choice 选择
type Choice struct {
	Index   int     `json:"index"`
	Message Message `json:"message"`
}

// Usage 使用情况
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// NewModelRouter 创建模型路由器
func NewModelRouter(config *RouterConfig) *ModelRouter {
	if config == nil {
		config = DefaultConfig()
	}
	router := &ModelRouter{
		endpoints:       make([]*ModelEndpoint, 0),
		config:          config,
		healthCheckStop: make(chan struct{}),
	}
	return router
}

// AddEndpoint 添加模型端点
func (r *ModelRouter) AddEndpoint(ep *ModelEndpoint) {
	r.mu.Lock()
	defer r.mu.Unlock()
	ep.Healthy = true
	r.endpoints = append(r.endpoints, ep)
}

// SetEndpoints 设置模型端点列表
func (r *ModelRouter) SetEndpoints(endpoints []*ModelEndpoint) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, ep := range endpoints {
		ep.Healthy = true
	}
	r.endpoints = endpoints
}

// Chat 智能调用（带故障切换）
func (r *ModelRouter) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
	r.mu.RLock()
	endpoints := make([]*ModelEndpoint, len(r.endpoints))
	copy(endpoints, r.endpoints)
	r.mu.RUnlock()

	if len(endpoints) == 0 {
		return nil, fmt.Errorf("no model endpoints configured")
	}

	var lastErr error
	var selectedEndpoint *ModelEndpoint

	// 按优先级排序
	sorted := r.sortByPriority(endpoints)

	// 尝试每个端点直到成功
	for _, ep := range sorted {
		if !ep.Healthy && r.config.EnableAutoFailover {
			continue // 跳过不健康的端点
		}

		selectedEndpoint = ep
		resp, err := r.callEndpoint(ctx, ep, messages)
		if err == nil {
			// 成功，记录成功次数
			r.RecordSuccess(ep.Name)
			return resp, nil
		}

		lastErr = err
		r.RecordFailure(ep.Name)
	}

	// 所有端点都失败
	if selectedEndpoint != nil {
		r.RecordFailure(selectedEndpoint.Name)
	}

	return nil, fmt.Errorf("all model endpoints failed, last error: %v", lastErr)
}

// callEndpoint 调用单个端点
func (r *ModelRouter) callEndpoint(ctx context.Context, ep *ModelEndpoint, messages []Message) (*ChatResponse, error) {
	timeout := time.Duration(ep.TimeoutSecs) * time.Second
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	reqBody := ChatRequest{
		Model:    ep.Model,
		Messages: messages,
		Stream:   false,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", ep.URL+"/api/chat", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if ep.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+ep.APIKey)
	}

	client := &http.Client{
		Timeout: timeout,
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(body))
	}

	var chatResp ChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&chatResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &chatResp, nil
}

// sortByPriority 按优先级排序（优先选健康的）
func (r *ModelRouter) sortByPriority(endpoints []*ModelEndpoint) []*ModelEndpoint {
	sorted := make([]*ModelEndpoint, len(endpoints))
	copy(sorted, endpoints)

	// 简单的冒泡排序
	for i := 0; i < len(sorted)-1; i++ {
		for j := 0; j < len(sorted)-i-1; j++ {
			// 健康优先，然后按优先级
			score1 := r.getEndpointScore(sorted[j])
			score2 := r.getEndpointScore(sorted[j+1])
			if score1 > score2 {
				sorted[j], sorted[j+1] = sorted[j+1], sorted[j]
			}
		}
	}
	return sorted
}

// getEndpointScore 获取端点评分（越小越好）
func (r *ModelRouter) getEndpointScore(ep *ModelEndpoint) int {
	score := ep.Priority * 100
	if !ep.Healthy {
		score += 10000 // 不健康的端点评分很高
	}
	score += ep.Failures * 10
	return score
}

// RecordSuccess 记录成功
func (r *ModelRouter) RecordSuccess(name string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, ep := range r.endpoints {
		if ep.Name == name {
			ep.Successes++
			// 连续成功达到阈值，恢复健康状态
			if !ep.Healthy && ep.Successes >= r.config.RecoveryThreshold {
				ep.Healthy = true
				ep.Failures = 0
			}
			break
		}
	}
}

// RecordFailure 记录失败
func (r *ModelRouter) RecordFailure(name string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, ep := range r.endpoints {
		if ep.Name == name {
			ep.Failures++
			ep.Successes = 0 // 重置成功计数
			// 连续失败超过阈值，标记为不健康
			if ep.Failures >= r.config.MaxFailures {
				ep.Healthy = false
			}
			break
		}
	}
}

// StartHealthChecks 启动健康检查
func (r *ModelRouter) StartHealthChecks() {
	if !r.config.EnableHealthCheck {
		return
	}

	go func() {
		ticker := time.NewTicker(r.config.HealthCheckInterval)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				r.checkAllEndpoints()
			case <-r.healthCheckStop:
				return
			}
		}
	}()
}

// StopHealthChecks 停止健康检查
func (r *ModelRouter) StopHealthChecks() {
	close(r.healthCheckStop)
}

// checkAllEndpoints 检查所有端点
func (r *ModelRouter) checkAllEndpoints() {
	r.mu.Lock()
	endpoints := make([]*ModelEndpoint, len(r.endpoints))
	copy(endpoints, r.endpoints)
	r.mu.Unlock()

	for _, ep := range endpoints {
		healthy := r.checkEndpoint(ep)
		r.mu.Lock()
		ep.Healthy = healthy
		ep.LastCheck = time.Now()
		if healthy {
			ep.Failures = 0
		}
		r.mu.Unlock()
	}
}

// checkEndpoint 检查单个端点
func (r *ModelRouter) checkEndpoint(ep *ModelEndpoint) bool {
	timeout := time.Duration(5 * time.Second)
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "GET", ep.URL+"/api/health", nil)
	if err != nil {
		return false
	}

	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK
}

// GetStatus 获取路由器状态
func (r *ModelRouter) GetStatus() map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	endpointStats := make([]map[string]interface{}, len(r.endpoints))
	for i, ep := range r.endpoints {
		endpointStats[i] = map[string]interface{}{
			"name":      ep.Name,
			"url":       ep.URL,
			"model":     ep.Model,
			"healthy":   ep.Healthy,
			"priority":  ep.Priority,
			"failures":  ep.Failures,
			"successes": ep.Successes,
			"last_check": ep.LastCheck.Format(time.RFC3339),
		}
	}

	return map[string]interface{}{
		"total_endpoints": len(r.endpoints),
		"healthy_count":   r.countHealthy(),
		"current_index":   r.currentIndex,
		"endpoints":       endpointStats,
	}
}

// countHealthy 统计健康端点数量
func (r *ModelRouter) countHealthy() int {
	count := 0
	for _, ep := range r.endpoints {
		if ep.Healthy {
			count++
		}
	}
	return count
}

// GetCurrentEndpoint 获取当前端点
func (r *ModelRouter) GetCurrentEndpoint() *ModelEndpoint {
	r.mu.RLock()
	defer r.mu.RUnlock()
	if len(r.endpoints) == 0 {
		return nil
	}
	return r.endpoints[r.currentIndex]
}

// Failover 手动故障切换
func (r *ModelRouter) Failover() bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	if len(r.endpoints) == 0 {
		return false
	}
	r.currentIndex = (r.currentIndex + 1) % len(r.endpoints)
	return true
}
'''
    (MODELS_DIR / "model_failover.go").write_text(failover_go, encoding='utf-8')
    log("  ✅ 创建 internal/models/model_failover.go", "SUCCESS")
    
    # 3. 创建使用示例
    log("步骤 3: 创建使用示例", "INFO")
    example_go = '''package main

import (
	"context"
	"fmt"
	"time"
	"github.com/computehub/opc/orchestration/internal/models"
)

func main() {
	// 创建路由器
	router := models.NewModelRouter(models.DefaultConfig())

	// 添加多个模型端点（按优先级排序）
	router.AddEndpoint(&models.ModelEndpoint{
		Name:        "local-qwen2.5",
		URL:         "http://localhost:11434",
		Model:       "qwen2.5:3b",
		Priority:    1, // 最高优先级
		TimeoutSecs: 5,
		Metadata:    map[string]string{"type": "local", "gpu": "true"},
	})

	router.AddEndpoint(&models.ModelEndpoint{
		Name:        "cloud-deepseek",
		URL:         "https://api.ollama.com",
		Model:       "deepseek-v3.1",
		Priority:    2,
		TimeoutSecs: 10,
		APIKey:      "your-api-key",
		Metadata:    map[string]string{"type": "cloud", "tier": "standard"},
	})

	router.AddEndpoint(&models.ModelEndpoint{
		Name:        "cloud-glm5",
		URL:         "https://api.glm.com",
		Model:       "glm-5.1",
		Priority:    3,
		TimeoutSecs: 10,
		APIKey:      "your-api-key",
		Metadata:    map[string]string{"type": "cloud", "tier": "premium"},
	})

	router.AddEndpoint(&models.ModelEndpoint{
		Name:        "local-qwen0.5b",
		URL:         "http://localhost:11434",
		Model:       "qwen:0.5b",
		Priority:    4, // 保底
		TimeoutSecs: 3,
		Metadata:    map[string]string{"type": "local", "fallback": "true"},
	})

	// 启动健康检查
	router.StartHealthChecks()

	// 调用示例
	messages := []models.Message{
		{Role: "user", Content: "你好，请介绍一下自己"},
	}

	ctx := context.Background()
	resp, err := router.Chat(ctx, messages)
	if err != nil {
		fmt.Printf("❌ 调用失败：%v\\n", err)
	} else {
		fmt.Printf("✅ 调用成功！\\n")
		fmt.Printf("   模型：%s\\n", resp.Model)
		fmt.Printf("   回复：%s\\n", resp.Choices[0].Message.Content)
	}

	// 查看状态
	status := router.GetStatus()
	fmt.Printf("\\n📊 路由器状态:\\n")
	fmt.Printf("   总端点数：%v\\n", status["total_endpoints"])
	fmt.Printf("   健康端点：%v\\n", status["healthy_count"])

	// 等待一段时间观察健康检查
	time.Sleep(30 * time.Second)

	// 停止健康检查
	router.StopHealthChecks()
}
'''
    (MODELS_DIR / "example_usage.go").write_text(example_go, encoding='utf-8')
    log("  ✅ 创建 internal/models/example_usage.go", "SUCCESS")
    
    # 4. 更新 handlers 添加模型路由 API
    log("步骤 4: 更新 handlers 添加模型路由 API", "INFO")
    handlers_path = GO_ORCHESTRATION / "internal" / "handlers" / "handlers.go"
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    # 添加导入
    if '"github.com/computehub/opc/orchestration/internal/models"' not in handlers_content:
        handlers_content = handlers_content.replace(
            '"github.com/computehub/opc/orchestration/internal/statemachine"',
            '"github.com/computehub/opc/orchestration/internal/statemachine"\n\t"github.com/computehub/opc/orchestration/internal/models"'
        )
    
    # 添加 modelRouter 字段
    handlers_content = handlers_content.replace(
        'statemachine *statemachine.StateMachine',
        'statemachine  *statemachine.StateMachine\n\tmodelRouter   *models.ModelRouter'
    )
    
    # 更新 NewHandler
    handlers_content = handlers_content.replace(
        'statemachine: statemachine.NewStateMachine(statemachine.DefaultConfig()),',
        'statemachine:  statemachine.NewStateMachine(statemachine.DefaultConfig()),\n\t\tmodelRouter:   models.NewModelRouter(models.DefaultConfig()),'
    )
    
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新 internal/handlers/handlers.go (添加模型路由)", "SUCCESS")
    
    # 5. 添加模型路由 API 端点
    log("步骤 5: 添加模型路由 API", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    model_router_apis = '''
// ChatWithFailover 带故障切换的聊天
func (h *Handler) ChatWithFailover(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Messages []models.Message `json:"messages"`
		Model    string           `json:"model,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	resp, err := h.modelRouter.Chat(r.Context(), req.Messages)
	if err != nil {
		http.Error(w, fmt.Sprintf("Chat failed: %v", err), http.StatusServiceUnavailable)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// GetModelRouterStatus 获取模型路由器状态
func (h *Handler) GetModelRouterStatus(w http.ResponseWriter, r *http.Request) {
	status := h.modelRouter.GetStatus()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// AddModelEndpoint 添加模型端点
func (h *Handler) AddModelEndpoint(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var ep models.ModelEndpoint
	if err := json.NewDecoder(r.Body).Decode(&ep); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	h.modelRouter.AddEndpoint(&ep)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"endpoint": ep.Name,
	})
}

// ManualFailover 手动故障切换
func (h *Handler) ManualFailover(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	success := h.modelRouter.Failover()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": success,
		"current": h.modelRouter.GetCurrentEndpoint(),
	})
}
'''
    
    handlers_content = handlers_content.rstrip() + '\n' + model_router_apis
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 添加模型路由 API 端点", "SUCCESS")
    
    # 6. 更新路由注册
    log("步骤 6: 更新路由注册", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    old_mux = '''mux.HandleFunc("GET /api/tasks/stats", h.GetTaskStats)

	return mux
}'''
    
    new_mux = '''mux.HandleFunc("GET /api/tasks/stats", h.GetTaskStats)

	// 模型路由端点
	mux.HandleFunc("POST /api/models/chat", h.ChatWithFailover)
	mux.HandleFunc("GET /api/models/status", h.GetModelRouterStatus)
	mux.HandleFunc("POST /api/models/endpoints", h.AddModelEndpoint)
	mux.HandleFunc("POST /api/models/failover", h.ManualFailover)

	return mux
}'''
    
    handlers_content = handlers_content.replace(old_mux, new_mux)
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新路由注册", "SUCCESS")
    
    # 7. 创建测试脚本
    log("步骤 7: 创建测试脚本", "INFO")
    test_failover_py = '''#!/usr/bin/env python3
"""测试模型故障自动切换"""

import requests
import time

BASE_URL = "http://localhost:8080"

def test_add_endpoints():
    """添加多个模型端点"""
    print("\\n=== 添加模型端点 ===")
    
    endpoints = [
        {
            "name": "local-qwen2.5",
            "url": "http://localhost:11434",
            "model": "qwen2.5:3b",
            "priority": 1,
            "timeout_secs": 5
        },
        {
            "name": "cloud-deepseek",
            "url": "https://api.ollama.com",
            "model": "deepseek-v3.1",
            "priority": 2,
            "timeout_secs": 10
        },
        {
            "name": "fallback-qwen0.5b",
            "url": "http://localhost:11434",
            "model": "qwen:0.5b",
            "priority": 3,
            "timeout_secs": 3
        }
    ]
    
    for ep in endpoints:
        resp = requests.post(f"{BASE_URL}/api/models/endpoints", json=ep)
        status = "✅" if resp.status_code == 200 else "❌"
        print(f"  {status} 添加 {ep['name']}")

def test_chat():
    """测试聊天（带故障切换）"""
    print("\\n=== 测试聊天 ===")
    
    payload = {
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍你自己"}
        ]
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/models/chat", json=payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            print(f"  ✅ 聊天成功!")
            print(f"     模型：{result.get('model', 'unknown')}")
            if result.get('choices'):
                print(f"     回复：{result['choices'][0]['message']['content'][:100]}...")
        else:
            print(f"  ❌ 聊天失败：{resp.text}")
    except Exception as e:
        print(f"  ❌ 请求异常：{e}")

def test_status():
    """查看路由器状态"""
    print("\\n=== 路由器状态 ===")
    
    resp = requests.get(f"{BASE_URL}/api/models/status")
    
    if resp.status_code == 200:
        status = resp.json()
        print(f"  总端点数：{status.get('total_endpoints', 0)}")
        print(f"  健康端点：{status.get('healthy_count', 0)}")
        
        endpoints = status.get('endpoints', [])
        for ep in endpoints:
            health = "🟢" if ep.get('healthy') else "🔴"
            print(f"    {health} {ep['name']} (优先级:{ep['priority']}, 失败:{ep['failures']})")

def test_manual_failover():
    """测试手动故障切换"""
    print("\\n=== 手动故障切换 ===")
    
    resp = requests.post(f"{BASE_URL}/api/models/failover")
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"  ✅ 切换成功")
        if result.get('current'):
            print(f"     当前端点：{result['current'].get('name')}")

if __name__ == "__main__":
    print("=" * 60)
    print("模型故障自动切换测试")
    print("=" * 60)
    
    try:
        # 添加端点
        test_add_endpoints()
        
        # 查看状态
        test_status()
        
        # 测试聊天
        test_chat()
        
        # 手动切换
        test_manual_failover()
        
        # 再次查看状态
        test_status()
        
        print("\\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\\n❌ 测试失败：{e}")
'''
    (GO_ORCHESTRATION / "test_model_failover.py").write_text(test_failover_py, encoding='utf-8')
    log("  ✅ 创建 test_model_failover.py", "SUCCESS")
    
    log("", "INFO")
    log("=" * 60, "INFO")
    log("模型故障自动切换模块创建完成！", "SUCCESS")
    log(f"目录：{GO_ORCHESTRATION}", "SUCCESS")
    log("=" * 60, "INFO")
    
    return True

if __name__ == "__main__":
    success = create_model_failover()
    sys.exit(0 if success else 1)
