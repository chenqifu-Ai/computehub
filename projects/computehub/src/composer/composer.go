// Package composer implements the TaskComposer pattern:
//   Large Task → Decompose (大模型) → Parallel Dispatch (小模型) → Merge Results (大模型)
//
// Architecture:
//   TaskComposer
//     ├── Decomposer (拆分解)
//     ├── DispatchEngine (并行分发，复用 scheduler)
//     └── Compositor (汇总合并)
//
// Phase 3 - ComputeHub Core
package composer

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"strings"
	"sync"
	"time"
)

// ====== 核心类型 ======

// TaskComposer 任务编排器 — 大模型拆、小模型并行干、大模型收编
type TaskComposer struct {
	// Decomposer: 大模型 → 子任务列表
	Decomposer Decomposer

	// DispatchEngine: 并行分发子任务到各小模型节点
	DispatchEngine *DispatchEngine

	// Compositor: 汇总结果 → 大模型整合
	Compositor Compositor

	// Config
	config Config
}

// Config TaskComposer 配置
type Config struct {
	// 最大并行度 — 同时跑多少个子任务
	MaxConcurrency int `json:"max_concurrency"`

	// 总超时 — 从分解到汇总的总时间
	Timeout time.Duration `json:"timeout"`

	// 失败容忍度 — 允许多少个子任务失败
	MaxFailures int `json:"max_failures"`

	// 分解模型 — 大模型（负责拆解和汇总）
	DecomposeModel string `json:"decompose_model"` // "qwen3.6-35b"

	// 执行模型 — 小模型（负责干具体活）
	ExecuteModels []string `json:"execute_models"` // ["qwen2.5:3b", "glm-4.7-flash", ...]

	// 分解提示词模板
	DecomposePrompt string `json:"decompose_prompt"`
	// 汇总提示词模板
	ComposePrompt string `json:"compose_prompt"`
}

// DefaultConfig 返回默认配置
func DefaultConfig() Config {
	return Config{
		MaxConcurrency: 10,
		Timeout:        300 * time.Second,
		MaxFailures:    2,
		DecomposeModel: "qwen3.6-35b",
		ExecuteModels:  []string{"qwen2.5:3b", "glm-4.7-flash", "ministral-3:8b"},
		DecomposePrompt: `你是一个任务拆解专家。请将以下任务分解为 N 个互不依赖的子任务，
每个子任务必须是独立可执行的，返回 JSON 格式:
{
  "subtasks": [
    {"id": "sub_1", "description": "子任务描述", "expected_input": "输入", "expected_output": "输出格式"},
    ...
  ]
}`,
		ComposePrompt: `你是一个结果汇总专家。以下是 N 个子任务的执行结果，
请整合所有结果，给出最终答案。
原始任务: {{.OriginalTask}}
子任务结果: {{.Results}}`,
	}
}

// ====== 任务定义 ======

// TaskComposerInput 编排输入
type TaskComposerInput struct {
	// TaskID 任务唯一标识
	TaskID string `json:"task_id"`
	// OriginalTask 原始大任务描述
	OriginalTask string `json:"original_task"`
	// ExtraContext 补充上下文（可选）
	ExtraContext string `json:"extra_context,omitempty"`
	// Metadata 元数据（可选）
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// DecomposedTask 分解后的子任务
type DecomposedTask struct {
	ID             string                 `json:"id"`
	Description    string                 `json:"description"`
	ExpectedInput  string                 `json:"expected_input"`
	ExpectedOutput string                 `json:"expected_output"`
	Priority       int                    `json:"priority"` // 1-10
	Dependencies   []string               `json:"dependencies"` // 依赖的其他子任务ID
	Payload        map[string]interface{} `json:"payload,omitempty"`
}

// DecomposedResult 分解结果
type DecomposedResult struct {
	TaskID       string            `json:"task_id"`
	Subtasks     []DecomposedTask  `json:"subtasks"`
	DecomposeAt  time.Time         `json:"decompose_at"`
	DecomposeModel string           `json:"decompose_model"`
	DecomposeLatency time.Duration   `json:"decompose_latency"`
}

// SubtaskExecution 子任务执行结果
type SubtaskExecution struct {
	SubtaskID string        `json:"subtask_id"`
	Success   bool          `json:"success"`
	Result    string        `json:"result"`
	Error     string        `json:"error,omitempty"`
	ModelUsed string        `json:"model_used"`
	ExecutedOn string       `json:"executed_on"` // node_id
	Duration  time.Duration  `json:"duration"`
	CompletedAt time.Time    `json:"completed_at"`
}

// TaskComposerOutput 编排输出
type TaskComposerOutput struct {
	TaskID       string             `json:"task_id"`
	Subtasks     []DecomposedTask   `json:"subtasks"`
	Results      []SubtaskExecution `json:"results"`
	FinalResult  string             `json:"final_result"`
	Success      bool               `json:"success"`
	TotalDuration time.Duration     `json:"total_duration"`
	ComposedAt   time.Time          `json:"composed_at"`
	ComposedModel string            `json:"composed_model"`
}

// ====== 接口定义 ======

// Decomposer 分解器接口 — 大模型将任务拆成子任务
type Decomposer interface {
	// Decompose 将一个大任务分解为多个子任务
	Decompose(input TaskComposerInput) (*DecomposedResult, error)
}

// Compositor 合并器接口 — 大模型汇总子任务结果
type Compositor interface {
	// Compose 将多个子任务结果合并为最终答案
	Compose(originalTask string, results []SubtaskExecution) (string, error)
}

// ====== 默认实现: 基于 LLM 的 Decomposer/Compositor ======

// LLMDecomposer 基于 LLM API 的分解器
type LLMDecomposer struct {
	Model       string
	APIURL      string
	APIKey      string
	Prompt      string
}

// LLMCompositor 基于 LLM API 的合并器
type LLMCompositor struct {
	Model       string
	APIURL      string
	APIKey      string
	Prompt      string
}

// Decompose 实现 Decomposer 接口
func (d *LLMDecomposer) Decompose(input TaskComposerInput) (*DecomposedResult, error) {
	start := time.Now()

	// Build prompt
	prompt := d.Prompt
	if prompt == "" {
		prompt = DefaultConfig().DecomposePrompt
	}
	fullPrompt := fmt.Sprintf("%s\n\n原始任务:\n%s", prompt, input.OriginalTask)
	if input.ExtraContext != "" {
		fullPrompt += fmt.Sprintf("\n\n补充上下文:\n%s", input.ExtraContext)
	}

	// 调用 LLM (实际项目中通过 HTTP 调用 API)
	result, err := callLLM(d.Model, d.APIURL, d.APIKey, fullPrompt, 2000)
	if err != nil {
		return nil, fmt.Errorf("decompose failed: %w", err)
	}

	// Parse result into DecomposedResult
	decomposed, err := parseDecomposeResult(input.TaskID, result)
	if err != nil {
		return nil, fmt.Errorf("parse decompose result failed: %w", err)
	}
	decomposed.DecomposeAt = time.Now()
	decomposed.DecomposeLatency = time.Since(start)
	decomposed.DecomposeModel = d.Model

	return decomposed, nil
}

// Compose 实现 Compositor 接口
func (c *LLMCompositor) Compose(originalTask string, results []SubtaskExecution) (string, error) {
	prompt := c.Prompt
	if prompt == "" {
		prompt = DefaultConfig().ComposePrompt
	}

	// Build results string
	var resultText string
	for _, r := range results {
		status := "✅"
		if !r.Success {
			status = "❌"
		}
		resultText += fmt.Sprintf("[%s] %s: %s\n", status, r.SubtaskID, r.Result)
		if !r.Success {
			resultText += fmt.Sprintf("  错误: %s\n", r.Error)
		}
	}

	fullPrompt := fmt.Sprintf(prompt, originalTask, resultText)

	result, err := callLLM(c.Model, c.APIURL, c.APIKey, fullPrompt, 2000)
	if err != nil {
		return "", fmt.Errorf("compose failed: %w", err)
	}

	return result, nil
}

// ====== 分发引擎 ======

// DispatchEngine 分发引擎 — 并行调度子任务到各小模型节点
type DispatchEngine struct {
	// 可用模型列表
	Models []string

	// LLM API 配置
	APIURL string
	APIKey string

	// 节点池 (实际项目中从 discover 获取)
	NodePool []string

	// 最大并发
	MaxConcurrency int

	// 超时
	Timeout time.Duration

	// 重试次数
	MaxRetries int

	mu   sync.RWMutex
	rng  *rand.Rand
}

// NewDispatchEngine 创建分发引擎
func NewDispatchEngine(models []string, maxConcurrency int, timeout time.Duration, apiURL, apiKey string) *DispatchEngine {
	return &DispatchEngine{
		Models:         models,
		APIURL:         apiURL,
		APIKey:         apiKey,
		MaxConcurrency: maxConcurrency,
		Timeout:        timeout,
		MaxRetries:     3,
		rng:            rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// Dispatch 并行分发并收集所有子任务结果
func (e *DispatchEngine) Dispatch(ctx context.Context, subtasks []DecomposedTask) ([]SubtaskExecution, error) {
	log.Printf("[DispatchEngine] Dispatching %d subtasks (concurrency=%d)", len(subtasks), e.MaxConcurrency)

	// 按优先级排序
	sorted := make([]DecomposedTask, len(subtasks))
	copy(sorted, subtasks)
	sortTasksByPriority(sorted)

	results := make([]SubtaskExecution, len(sorted))
	resultMu := sync.Mutex{}

	// 使用 semaphore 控制并发
	sem := make(chan struct{}, e.MaxConcurrency)
	var wg sync.WaitGroup

	for i, task := range sorted {
		wg.Add(1)
		go func(idx int, t DecomposedTask) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			select {
			case <-ctx.Done():
				resultMu.Lock()
				results[idx] = SubtaskExecution{
					SubtaskID: t.ID,
					Success:   false,
					Error:     "context cancelled",
				}
				resultMu.Unlock()
				return
			default:
			}

			result := e.executeSubtask(ctx, t)
			resultMu.Lock()
			results[idx] = result
			resultMu.Unlock()
		}(i, task)
	}

	wg.Wait()
	return results, nil
}

// executeSubtask 执行单个子任务 (带重试)
func (e *DispatchEngine) executeSubtask(ctx context.Context, task DecomposedTask) SubtaskExecution {
	start := time.Now()
	model := e.selectModel()

	for attempt := 0; attempt <= e.MaxRetries; attempt++ {
		select {
		case <-ctx.Done():
			return SubtaskExecution{
				SubtaskID: task.ID,
				Success:   false,
				Error:     "context cancelled",
				Duration:  time.Since(start),
			}
		default:
		}

		// 调用小模型执行
		result, err := callSmallModel(ctx, model, task, e.APIURL, e.APIKey)
		if err == nil {
			return SubtaskExecution{
				SubtaskID:    task.ID,
				Success:      true,
				Result:       result,
				ModelUsed:    model,
				Duration:     time.Since(start),
				CompletedAt:  time.Now(),
			}
		}

		log.Printf("[DispatchEngine] Subtask %s failed (attempt %d/%d): %v", task.ID, attempt+1, e.MaxRetries+1, err)
		if attempt < e.MaxRetries {
			time.Sleep(time.Duration(attempt+1) * 500 * time.Millisecond) // 指数退避
		}
	}

	return SubtaskExecution{
		SubtaskID:  task.ID,
		Success:    false,
		Error:      fmt.Sprintf("max retries exceeded (%d)", e.MaxRetries+1),
		Duration:   time.Since(start),
		CompletedAt: time.Now(),
	}
}

// selectModel 选择一个可用的小模型
func (e *DispatchEngine) selectModel() string {
	e.mu.RLock()
	defer e.mu.RUnlock()
	if len(e.Models) == 0 {
		return "unknown"
	}
	return e.Models[e.rng.Intn(len(e.Models))]
}

// ====== TaskComposer 核心方法 ======

// NewTaskComposer 创建 TaskComposer
func NewTaskComposer(cfg Config, apiURL, apiKey string) *TaskComposer {
	// 默认 Decomposer
	if cfg.DecomposePrompt == "" {
		cfg.DecomposePrompt = DefaultConfig().DecomposePrompt
	}
	if cfg.ComposePrompt == "" {
		cfg.ComposePrompt = DefaultConfig().ComposePrompt
	}

	// 初始化 Decomposer
	dec := &LLMDecomposer{
		Model:    cfg.DecomposeModel,
		Prompt:   cfg.DecomposePrompt,
		APIURL:   apiURL,
		APIKey:   apiKey,
	}

	// 初始化 Compositor
	com := &LLMCompositor{
		Model:  cfg.DecomposeModel, // 汇总也用大模型
		Prompt: cfg.ComposePrompt,
		APIURL: apiURL,
		APIKey: apiKey,
	}

	// 初始化 DispatchEngine
	engine := NewDispatchEngine(
		cfg.ExecuteModels,
		cfg.MaxConcurrency,
		cfg.Timeout,
		apiURL,
		apiKey,
	)

	return &TaskComposer{
		Decomposer:     dec,
		DispatchEngine: engine,
		Compositor:     com,
		config:         cfg,
	}
}

// Run 执行完整的编排流程: 分解 → 并行分发 → 汇总
func (tc *TaskComposer) Run(input TaskComposerInput) (*TaskComposerOutput, error) {
	start := time.Now()

	// 创建超时上下文
	ctx, cancel := context.WithTimeout(context.Background(), tc.config.Timeout)
	defer cancel()

	log.Printf("[TaskComposer] Starting task %s: %s", input.TaskID, input.OriginalTask[:min(len(input.OriginalTask), 60)])

	// Step 1: 大模型分解
	log.Printf("[TaskComposer] Step 1/3: Decomposing...")
	decomposed, err := tc.Decomposer.Decompose(input)
	if err != nil {
		return nil, fmt.Errorf("decompose failed: %w", err)
	}
	log.Printf("[TaskComposer] Decomposed into %d subtasks (took %v)", len(decomposed.Subtasks), decomposed.DecomposeLatency)

	// 检查是否有子任务
	if len(decomposed.Subtasks) == 0 {
		return nil, fmt.Errorf("decomposition produced 0 subtasks")
	}

	// Step 2: 并行分发
	log.Printf("[TaskComposer] Step 2/3: Dispatching %d subtasks in parallel...", len(decomposed.Subtasks))
	results, err := tc.DispatchEngine.Dispatch(ctx, decomposed.Subtasks)
	if err != nil {
		return nil, fmt.Errorf("dispatch failed: %w", err)
	}

	// 统计成功/失败
	successCount := 0
	failCount := 0
	for _, r := range results {
		if r.Success {
			successCount++
		} else {
			failCount++
		}
	}
	log.Printf("[TaskComposer] Dispatch complete: %d success, %d failed", successCount, failCount)

	// 检查失败是否超出容忍
	if failCount > tc.config.MaxFailures {
		log.Printf("[TaskComposer] WARNING: %d failures exceed max tolerance (%d)", failCount, tc.config.MaxFailures)
		// 仍然继续汇总，但标记部分失败
	}

	// Step 3: 大模型汇总
	log.Printf("[TaskComposer] Step 3/3: Composing final result...")
	finalResult, err := tc.Compositor.Compose(input.OriginalTask, results)
	if err != nil {
		return nil, fmt.Errorf("compose failed: %w", err)
	}

	totalDuration := time.Since(start)

	output := &TaskComposerOutput{
		TaskID:          input.TaskID,
		Subtasks:        decomposed.Subtasks,
		Results:         results,
		FinalResult:     finalResult,
		Success:         failCount <= tc.config.MaxFailures,
		TotalDuration:   totalDuration,
		ComposedAt:      time.Now(),
		ComposedModel:   tc.config.DecomposeModel,
	}

	log.Printf("[TaskComposer] Task %s complete (total: %v, success: %v)", input.TaskID, totalDuration, output.Success)
	return output, nil
}

// ====== 工具函数 ======

// callLLM 调用大模型 API
func callLLM(model, apiURL, apiKey, prompt string, maxTokens int) (string, error) {
	client := NewLLMClient(apiURL, apiKey, model)
	// 使用 system 角色给指令，user 角色给任务
	return client.CallWithPrompt(
		"你是一个严谨的 AI 助手，请严格按照要求的格式输出。",
		prompt,
		maxTokens,
	)
}

// callSmallModel 在 worker 上执行子任务
func callSmallModel(ctx context.Context, model string, task DecomposedTask, apiURL, apiKey string) (string, error) {
	client := NewLLMClient(apiURL, apiKey, model)
	prompt := fmt.Sprintf("请执行以下任务:\n描述: %s\n预期输入: %s\n预期输出: %s",
		task.Description, task.ExpectedInput, task.ExpectedOutput)
	return client.CallWithPrompt("你是一个专注的任务执行者。", prompt, 1024)
}

// parseDecomposeResult 解析 LLM 返回的 JSON 分解结果
func parseDecomposeResult(taskID, result string) (*DecomposedResult, error) {
	// 尝试从 ```json ... ``` 代码块中提取
	cleaned := result
	if idx := strings.Index(cleaned, "```json"); idx >= 0 {
		end := strings.Index(cleaned[idx+7:], "```")
		if end >= 0 {
			cleaned = cleaned[idx+7 : idx+7+end]
		}
	} else if idx := strings.Index(cleaned, "```"); idx >= 0 {
		end := strings.Index(cleaned[idx+3:], "```")
		if end >= 0 {
			cleaned = cleaned[idx+3 : idx+3+end]
		}
	}
	cleaned = strings.TrimSpace(cleaned)

	var parsed struct {
		Subtasks []DecomposedTask `json:"subtasks"`
		Thinking string           `json:"thinking,omitempty"`
	}
	if err := json.Unmarshal([]byte(cleaned), &parsed); err != nil {
		// 解析失败时 fallback：把整段文本当单个子任务
		return &DecomposedResult{
			TaskID: taskID,
			Subtasks: []DecomposedTask{
				{
					ID:             "sub_1",
					Description:    result[:min(len(result), 200)],
					ExpectedOutput: "文本结果",
					Priority:       5,
				},
			},
		}, nil
	}

	if len(parsed.Subtasks) == 0 {
		return nil, fmt.Errorf("decomposition produced 0 subtasks")
	}

	// 补全默认值
	for i := range parsed.Subtasks {
		if parsed.Subtasks[i].ID == "" {
			parsed.Subtasks[i].ID = fmt.Sprintf("sub_%d", i+1)
		}
		if parsed.Subtasks[i].Priority == 0 {
			parsed.Subtasks[i].Priority = 5
		}
	}

	return &DecomposedResult{
		TaskID:   taskID,
		Subtasks: parsed.Subtasks,
	}, nil
}

// sortTasksByPriority 按优先级排序任务
func sortTasksByPriority(tasks []DecomposedTask) {
	for i := 0; i < len(tasks); i++ {
		for j := i + 1; j < len(tasks); j++ {
			if tasks[j].Priority > tasks[i].Priority {
				tasks[i], tasks[j] = tasks[j], tasks[i]
			}
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
