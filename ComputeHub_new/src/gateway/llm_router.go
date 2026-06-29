// Package gateway — 分布式 LLM 路由器
//
// 职责：
//   1. 自动发现集群中所有带 Ollama 的 Worker
//   2. 维护 Ollama 实例池（健康状态 + 模型列表）
//   3. 负载均衡 + 故障转移
//   4. 统一 /api/v1/llm/* 端点
//
// 核心设计原则：
//   - 零外部依赖（利用现有 Worker 的 Ollama）
//   - 多层容灾（本地 → 跨节点 → 外部 API → 降级）
//   - 按需路由（简单任务用本地小模型，复杂推理用外部大模型）

package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"github.com/computehub/opc/src/kernel"
)

// ============================================================
// 常量定义
// ============================================================

const (
	// HealthCheckInterval 健康检查间隔
	HealthCheckInterval = 30 * time.Second

	// RequestTimeout 单个 LLM 请求超时
	RequestTimeout = 15 * time.Second

	// ModelCacheTTL 模型列表缓存时间
	ModelCacheTTL = 5 * time.Minute

	// MaxConcurrentPerInstance 每个 Ollama 实例最大并发请求
	MaxConcurrentPerInstance = 3

	// FailedThreshold 连续失败次数达到此值标记为 unhealthy
	FailedThreshold = 3
)

// ============================================================
// 数据结构
// ============================================================

// OllamaInstance 表示一个 Ollama 实例（通常运行在 Worker 的 localhost:11434）
type OllamaInstance struct {
	WorkerID   string    `json:"worker_id"`
	Host       string    `json:"host"` // http://worker-ip:11434 或 localhost
	Port       int       `json:"port"`
	Region     string    `json:"region"`
	ModelInfo  []Model   `json:"models"`
	Healthy    bool      `json:"healthy"`
	FailedCount uint32   `json:"-"`
	LastCheck  time.Time `json:"last_check"`
	Concurrent atomic.Int32
	LastLatency time.Duration `json:"-"`
	TotalRequests atomic.Int64 `json:"-"`
	TotalFailures atomic.Int64 `json:"-"`
}

// Model 表示一个可用的 LLM 模型
type Model struct {
	Name  string  `json:"name"`
	Size  float64 `json:"size_gb"` // GB
	Loaded bool   `json:"loaded"`
}

// LLMRequest 统一 LLM 请求接口
type LLMRequest struct {
	Model   string   `json:"model"`
	Messages []Message `json:"messages"`
	Stream  bool     `json:"stream,omitempty"`
	Tools   []Tool   `json:"tools,omitempty"`
	Temperature float64 `json:"temperature,omitempty"`
	MaxTokens   int     `json:"max_tokens,omitempty"`
}

// Message OpenAI 兼容消息格式
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Tool OpenAI 兼容工具格式
type Tool struct {
	Type     string `json:"type"`
	Function FunctionTool `json:"function"`
}

type FunctionTool struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
}

// LLMResponse 统一响应格式
type LLMResponse struct {
	Content  string            `json:"content"`
	Model    string            `json:"model"`
	Provider string            `json:"provider"` // "ollama-worker-A" / "newapi"
	Usage    *UsageInfo        `json:"usage,omitempty"`
	Error    string            `json:"error,omitempty"`
	Latency  time.Duration     `json:"latency_ms"`
}

type UsageInfo struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// ============================================================
// LLMRouter — 分布式 LLM 路由器
// ============================================================

type LLMRouter struct {
	mu           sync.RWMutex
	gateway      *OpcGateway
	instances    map[string]*OllamaInstance // worker_id -> instance
	external     *ExternalLLM               // 外部 API 兜底
	enabled      bool
	stopped      chan struct{}

	// 统计
	totalRequests atomic.Int64
	totalFailures atomic.Int64
}

// NewLLMRouter 创建 LLM 路由器
func NewLLMRouter(gw *OpcGateway) *LLMRouter {
	return &LLMRouter{
		gateway:   gw,
		instances: make(map[string]*OllamaInstance),
		external:  NewExternalLLM(),
		stopped:   make(chan struct{}),
	}
}

// Start 启动路由器（后台健康检查 + 节点发现）
func (r *LLMRouter) Start() {
	r.enabled = true
	r.log("LLM Router 启动")

	// 启动后台健康检查
	go r.healthCheckLoop()

	// 启动节点事件监听（新 Worker 加入时自动注册 Ollama）
	// 这部分在 Gateway init 时连接
}

// Stop 停止路由器
func (r *LLMRouter) Stop() {
	r.enabled = false
	close(r.stopped)
	r.log("LLM Router 已停止")
}

// Submit 提交 LLM 请求（自动选择最佳实例）
func (r *LLMRouter) Submit(ctx context.Context, req *LLMRequest) (*LLMResponse, error) {
	r.totalRequests.Add(1)

	// 1. 策略：优先本地/就近模型
	// 2. 故障转移：失败自动切下一个
	// 3. 降级：全部失败时走外部 API

	instances := r.getHealthyInstances()

	// 按模型匹配过滤
	candidates := r.filterByModel(instances, req.Model)

	if len(candidates) == 0 {
		// 没有匹配的本地模型 → 尝试外部 API
		r.log("无匹配本地模型，降级到外部 API")
		return r.external.Call(ctx, req)
	}

	// 按延迟排序，优先调用最快的
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].LastLatency < candidates[j].LastLatency
	})

	// 尝试前 N 个候选（带重试）
	maxAttempts := min(3, len(candidates))
	for i := 0; i < maxAttempts; i++ {
		resp, err := r.callInstance(ctx, candidates[i], req)
		if err == nil {
			return resp, nil
		}

		r.instances[candidates[i].WorkerID].FailedCount++
		r.log("实例调用失败: %s, err=%v, attempt=%d/%d", candidates[i].WorkerID, err, i+1, maxAttempts)
	}

	// 所有本地实例都失败 → 降级到外部 API
	r.log("所有本地实例失败，降级到外部 API")
	return r.external.Call(ctx, req)
}

// callInstance 调用单个 Ollama 实例
func (r *LLMRouter) callInstance(ctx context.Context, inst *OllamaInstance, req *LLMRequest) (*LLMResponse, error) {
	// 并发限制
	if inst.Concurrent.Add(1) > MaxConcurrentPerInstance {
		inst.Concurrent.Add(-1)
		return nil, fmt.Errorf("实例 %s 并发达到上限 (%d)", inst.WorkerID, MaxConcurrentPerInstance)
	}
	defer inst.Concurrent.Add(-1)

	// 设置超时
	ctx, cancel := context.WithTimeout(ctx, RequestTimeout)
	defer cancel()

	// 构建 OpenAI 兼容请求
	body, _ := json.Marshal(map[string]interface{}{
		"model":    req.Model,
		"messages": req.Messages,
		"stream":   req.Stream,
	})

	// 发起 HTTP 请求
	url := fmt.Sprintf("%s:%d/v1/chat/completions", inst.Host, inst.Port)
	start := time.Now()

	resp, err := http.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		inst.FailedCount++
		return nil, err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	latency := time.Since(start)

	if resp.StatusCode != http.StatusOK {
		inst.FailedCount++
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(respBody))
	}

	// 解析响应
	var apiResp struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Usage struct {
			PromptTokens     int `json:"prompt_tokens"`
			CompletionTokens int `json:"completion_tokens"`
			TotalTokens      int `json:"total_tokens"`
		} `json:"usage"`
	}

	if err := json.Unmarshal(respBody, &apiResp); err != nil {
		inst.FailedCount++
		return nil, err
	}

	// 更新统计
	inst.LastLatency = latency
	inst.TotalRequests.Add(1)
	inst.LastCheck = time.Now()
	if inst.FailedCount > 0 {
		inst.FailedCount-- // 成功一次，失败计数递减
	}

	return &LLMResponse{
		Content:  apiResp.Choices[0].Message.Content,
		Model:    req.Model,
		Provider: fmt.Sprintf("ollama-%s", inst.WorkerID),
		Usage: &UsageInfo{
			PromptTokens:     apiResp.Usage.PromptTokens,
			CompletionTokens: apiResp.Usage.CompletionTokens,
			TotalTokens:      apiResp.Usage.TotalTokens,
		},
		Latency: latency,
	}, nil
}

// RegisterWorker 注册新 Worker 的 Ollama 实例（由 Gateway 节点注册时调用）
func (r *LLMRouter) RegisterWorker(nodeID, host string, port int, region string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	inst := &OllamaInstance{
		WorkerID: nodeID,
		Host:     host,
		Port:     port,
		Region:   region,
		Healthy:  true,
	}
	r.instances[nodeID] = inst
	r.log("注册 Worker Ollama: %s (%s:%d)", nodeID, host, port)

	// 立即做一次健康检查
	r.checkInstanceHealth(inst)
}

// UnregisterWorker 移除 Worker 的 Ollama 实例
func (r *LLMRouter) UnregisterWorker(nodeID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if inst, ok := r.instances[nodeID]; ok {
		inst.Healthy = false
		r.log("移除 Worker Ollama: %s", nodeID)
	}
	delete(r.instances, nodeID)
}

// getHealthyInstances 返回所有健康的实例
func (r *LLMRouter) getHealthyInstances() []*OllamaInstance {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var healthy []*OllamaInstance
	for _, inst := range r.instances {
		if inst.Healthy && inst.FailedCount < FailedThreshold {
			healthy = append(healthy, inst)
		}
	}
	return healthy
}

// filterByModel 按模型名称过滤实例
func (r *LLMRouter) filterByModel(instances []*OllamaInstance, modelName string) []*OllamaInstance {
	if modelName == "" {
		return instances // 没有指定模型，返回全部
	}

	var matched []*OllamaInstance
	for _, inst := range instances {
		for _, model := range inst.ModelInfo {
			if model.Name == modelName || strings.HasPrefix(model.Name, modelName) {
				matched = append(matched, inst)
				break
			}
		}
	}
	return matched
}

// checkInstanceHealth 检查单个实例健康状态
func (r *LLMRouter) checkInstanceHealth(inst *OllamaInstance) {
	url := fmt.Sprintf("http://%s:%d/api/tags", inst.Host, inst.Port)

	resp, err := http.Get(url)
	if err != nil || resp.StatusCode != http.StatusOK {
		inst.Healthy = false
		inst.FailedCount++
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var tagsResp struct {
		Models []struct {
			Name string `json:"name"`
			Size float64 `json:"size"`
		} `json:"models"`
	}

	if err := json.Unmarshal(body, &tagsResp); err == nil {
		for _, m := range tagsResp.Models {
			inst.ModelInfo = append(inst.ModelInfo, Model{
				Name: m.Name,
				Size: m.Size / 1e9, // bytes → GB
				Loaded: true,
			})
		}
		inst.Healthy = true
		inst.FailedCount = 0
		inst.LastCheck = time.Now()
	}
}

// healthCheckLoop 后台健康检查循环
func (r *LLMRouter) healthCheckLoop() {
	ticker := time.NewTicker(HealthCheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			r.mu.RLock()
			var toCheck []*OllamaInstance
			for _, inst := range r.instances {
				toCheck = append(toCheck, inst)
			}
			r.mu.RUnlock()

			for _, inst := range toCheck {
				r.checkInstanceHealth(inst)
			}
		case <-r.stopped:
			return
		}
	}
}

// Status 返回路由器状态（供监控使用）
func (r *LLMRouter) Status() map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	instances := make(map[string]map[string]interface{})
	totalHealthy := 0
	totalModels := 0

	for id, inst := range r.instances {
		instances[id] = map[string]interface{}{
			"host":         inst.Host,
			"port":         inst.Port,
			"region":       inst.Region,
			"healthy":      inst.Healthy,
			"failed_count": inst.FailedCount,
			"models":       inst.ModelInfo,
		}
		if inst.Healthy {
			totalHealthy++
		}
		totalModels += len(inst.ModelInfo)
	}

	return map[string]interface{}{
		"enabled":         r.enabled,
		"total_instances": len(r.instances),
		"healthy":         totalHealthy,
		"total_models":    totalModels,
		"instances":       instances,
		"total_requests":  r.totalRequests.Load(),
		"total_failures":  r.totalFailures.Load(),
	}
}

func (r *LLMRouter) log(format string, args ...interface{}) {
	log.Printf("[LLM-Router] "+format, args...)
}

// ============================================================
// HTTP 路由注册
// ============================================================

// RegisterRoutes 注册 LLM 路由到 Gateway HTTP 服务器
func (r *LLMRouter) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/v1/llm/chat", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
			return
		}

		var llmReq LLMRequest
		if err := json.NewDecoder(req.Body).Decode(&llmReq); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		ctx, cancel := context.WithTimeout(req.Context(), 60*time.Second)
		defer cancel()

		resp, err := r.Submit(ctx, &llmReq)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadGateway)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	mux.HandleFunc("/api/v1/llm/status", func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(r.Status())
	})

	mux.HandleFunc("/api/v1/llm/discovery", func(w http.ResponseWriter, req *http.Request) {
		// 返回所有可用模型及其所在位置
		r.mu.RLock()
		models := make(map[string][]string) // model -> [worker_ids]
		for id, inst := range r.instances {
			for _, m := range inst.ModelInfo {
				if inst.Healthy {
					models[m.Name] = append(models[m.Name], id)
				}
			}
		}
		r.mu.RUnlock()

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(models)
	})
}
