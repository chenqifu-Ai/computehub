// Package pure implements the four-stage purification pipeline.
// Every task request must pass through all four filters before reaching
// the kernel. This ensures syntax correctness, semantic validity,
// security boundaries, and proper physical context injection.
//
// Architecture: Syntax → Semantic → Boundary → Context
package pure

import (
	"fmt"
	"strings"
	"time"

	"github.com/chenqifu-Ai/computehub/src/kernel"
)

// ─── 过滤器接口 ───

// Filter is a single stage in the purification pipeline.
type Filter interface {
	Filter(input any) FilterResult
	Name() string
}

// FilterResult is the output of a filter stage.
type FilterResult struct {
	Passed  bool
	Reason  string
	Cleaned any
}

// ─── 流水线 ───

// Pipeline manages the sequence of purification filters.
// Every task passes through in order: Syntax → Semantic → Boundary → Context
type Pipeline struct {
	filters      []Filter
	LastLatency  time.Duration
	TotalBlocked int64
	TotalPassed  int64
}

// NewPipeline creates a pipeline with all four standard filters.
func NewPipeline() *Pipeline {
	p := &Pipeline{
		filters: make([]Filter, 0, 4),
	}

	// Stage 1: Syntax Filter
	p.AddFilter(&SyntaxFilter{})

	// Stage 2: Semantic Filter
	p.AddFilter(&SemanticFilter{
		AllowedFrameworks: map[string]bool{
			"pytorch": true, "tensorflow": true, "jax": true,
			"onnx": true, "huggingface": true, "custom": true,
		},
		AllowedResourceTypes: map[string]bool{
			"gpu": true, "cpu": true, "tpu": true,
		},
		AllowedActions: map[string]bool{
			string(kernel.TaskActionSubmit):   true,
			string(kernel.TaskActionExecute):  true,
			string(kernel.TaskActionCancel):   true,
			string(kernel.TaskActionStatus):   true,
			string(kernel.TaskActionResource): true,
		},
	})

	// Stage 3: Boundary Filter
	p.AddFilter(&BoundaryFilter{
		MaxGPUs:  8,
		MaxCPUs:  32,
		MaxMemGB: 128,
	})

	// Stage 4: Context Filter
	p.AddFilter(&ContextFilter{
		SystemID: "computehub-gateway",
	})

	return p
}

// AddFilter adds a custom filter to the pipeline.
func (p *Pipeline) AddFilter(f Filter) {
	p.filters = append(p.filters, f)
}

// Process runs input through all filter stages.
// Returns cleaned output or an error if any stage blocks.
func (p *Pipeline) Process(input any) (any, error) {
	start := time.Now()
	current := input

	for _, filter := range p.filters {
		res := filter.Filter(current)
		if !res.Passed {
			p.LastLatency = time.Since(start)
			p.TotalBlocked++
			return nil, fmt.Errorf("[%s] purified blocked: %s", filter.Name(), res.Reason)
		}
		current = res.Cleaned
	}

	p.LastLatency = time.Since(start)
	p.TotalPassed++
	return current, nil
}

// Stats returns pipeline statistics.
func (p *Pipeline) Stats() map[string]any {
	return map[string]any{
		"total_passed":  p.TotalPassed,
		"total_blocked": p.TotalBlocked,
		"last_latency":  p.LastLatency.String(),
	}
}

// ─── Stage 1: 语法过滤器 ───

// SyntaxFilter validates task structure and removes garbage input.
type SyntaxFilter struct {
	// Max task name length
	MaxTaskName int
}

func (f *SyntaxFilter) Name() string { return "SyntaxFilter" }

func (f *SyntaxFilter) Filter(input any) FilterResult {
	task, ok := input.(*kernel.ComputeTask)
	if !ok {
		return FilterResult{
			Passed: false,
			Reason: "input must be a ComputeTask",
		}
	}

	// Validate action
	if strings.TrimSpace(string(task.Action)) == "" {
		return FilterResult{
			Passed: false,
			Reason: "action is required",
		}
	}

	// For compute tasks, validate resource params
	if task.Action == kernel.TaskActionSubmit {
		if task.ResourceType == "" && task.Framework == "" {
			return FilterResult{
				Passed: false,
				Reason: "submit requires resource_type or framework",
			}
		}
	}

	return FilterResult{
		Passed:  true,
		Cleaned: task,
	}
}

// ─── Stage 2: 语义过滤器 ───

// SemanticFilter validates task intent and policy compliance.
type SemanticFilter struct {
	AllowedFrameworks    map[string]bool
	AllowedResourceTypes map[string]bool
	AllowedActions       map[string]bool
}

func (f *SemanticFilter) Name() string { return "SemanticFilter" }

func (f *SemanticFilter) Filter(input any) FilterResult {
	task, ok := input.(*kernel.ComputeTask)
	if !ok {
		return FilterResult{
			Passed: false,
			Reason: "semantic filter requires ComputeTask",
		}
	}

	// Validate action
	actionStr := strings.ToUpper(strings.TrimSpace(string(task.Action)))
	if !f.AllowedActions[actionStr] {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("action not permitted: %s", task.Action),
		}
	}

	// Validate framework
	if task.Framework != "" && !f.AllowedFrameworks[strings.ToLower(task.Framework)] {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("framework not allowed: %s", task.Framework),
		}
	}

	// Validate resource type
	if task.ResourceType != "" && !f.AllowedResourceTypes[strings.ToLower(task.ResourceType)] {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("resource type not allowed: %s", task.ResourceType),
		}
	}

	return FilterResult{
		Passed:  true,
		Cleaned: task,
	}
}

// ─── Stage 3: 边界过滤器 ───

// BoundaryFilter enforces resource limits and security boundaries.
type BoundaryFilter struct {
	MaxGPUs    int
	MaxCPUs    int
	MaxMemGB   int
	MaxDurSecs int
}

func (f *BoundaryFilter) Name() string { return "BoundaryFilter" }

func (f *BoundaryFilter) Filter(input any) FilterResult {
	task, ok := input.(*kernel.ComputeTask)
	if !ok {
		return FilterResult{Passed: false, Reason: "requires ComputeTask"}
	}

	// GPU count check
	if task.GPUCount > f.MaxGPUs {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("GPU count %d exceeds limit %d", task.GPUCount, f.MaxGPUs),
		}
	}

	// CPU count check
	if task.CPUCount > f.MaxCPUs {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("CPU count %d exceeds limit %d", task.CPUCount, f.MaxCPUs),
		}
	}

	// Memory check
	if task.MemoryGB > f.MaxMemGB {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("memory %dGB exceeds limit %dGB", task.MemoryGB, f.MaxMemGB),
		}
	}

	// Duration check
	if task.DurationSecs > 0 && task.DurationSecs > f.MaxDurSecs {
		return FilterResult{
			Passed: false,
			Reason: fmt.Sprintf("duration %ds exceeds limit %ds", task.DurationSecs, f.MaxDurSecs),
		}
	}

	// Negative resource check
	if task.GPUCount < 0 || task.CPUCount < 0 || task.MemoryGB < 0 {
		return FilterResult{
			Passed: false,
			Reason: "negative resource allocation not allowed",
		}
	}

	return FilterResult{
		Passed:  true,
		Cleaned: task,
	}
}

// ─── Stage 4: 上下文过滤器 ───

// ContextFilter injects physical context into the task.
type ContextFilter struct {
	SystemID    string
	Environment string
}

func (f *ContextFilter) Name() string { return "ContextFilter" }

func (f *ContextFilter) Filter(input any) FilterResult {
	task, ok := input.(*kernel.ComputeTask)
	if !ok {
		return FilterResult{Passed: false, Reason: "requires ComputeTask"}
	}

	// Inject physical context
	if task.Requirements == nil {
		task.Requirements = make(map[string]string)
	}
	task.Requirements["_system_id"] = f.SystemID
	task.Requirements["_env"] = f.Environment
	task.Requirements["_purified_at"] = time.Now().Format(time.RFC3339)

	return FilterResult{
		Passed:  true,
		Cleaned: task,
	}
}

// ─── 常用过滤器组合 ───

// ProductionPipeline returns a pipeline configured for production use.
func ProductionPipeline() *Pipeline {
	p := NewPipeline()
	// Additional production-level filters could be added here
	return p
}
