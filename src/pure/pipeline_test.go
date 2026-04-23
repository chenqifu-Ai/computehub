// Package pure_test - 四级纯化流水线单元测试
package pure

import (
	"testing"
	"time"

	"github.com/chenqifu-Ai/computehub/src/kernel"
)

func TestNewPipeline(t *testing.T) {
	p := NewPipeline()
	if p == nil {
		t.Fatal("Pipeline should not be nil")
	}
	if len(p.filters) != 4 {
		t.Errorf("Expected 4 filters, got %d", len(p.filters))
	}
}

func TestSyntaxFilter_Valid(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "pytorch",
		ResourceType: "gpu",
		GPUCount:     1,
		Source:       "test",
	}
	_, err := p.Process(task)
	if err != nil {
		t.Fatalf("Valid task should pass: %v", err)
	}
}

func TestSyntaxFilter_EmptyAction(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       "",
		Framework:    "pytorch",
		ResourceType: "gpu",
		Source:       "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Empty action should be blocked")
	}
}

func TestSyntaxFilter_SubmitRequiresResource(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action: kernel.TaskActionSubmit,
		// No framework, no resource_type
		Source: "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Submit without resource_type or framework should be blocked")
	}
}

func TestSemanticFilter_AllowedAction(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "tensorflow",
		ResourceType: "cpu",
		Source:       "test",
	}
	_, err := p.Process(task)
	if err != nil {
		t.Fatalf("Allowed action should pass: %v", err)
	}
}

func TestSemanticFilter_ForbiddenAction(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action: kernel.TaskAction("INVALID"),
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Forbidden action should be blocked")
	}
}

func TestSemanticFilter_ForbiddenFramework(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "invalid_framework",
		ResourceType: "cpu",
		Source:       "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Forbidden framework should be blocked")
	}
}

func TestSemanticFilter_ForbiddenResourceType(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "pytorch",
		ResourceType: "invalid",
		Source:       "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Forbidden resource type should be blocked")
	}
}

func TestBoundaryFilter_GPUExceed(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		ResourceType: "gpu",
		GPUCount:     100, // > max 8
		Source:       "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Exceeding GPU limit should be blocked")
	}
}

func TestBoundaryFilter_CPUExceed(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		ResourceType: "cpu",
		CPUCount:     100, // > max 32
		Source:       "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Exceeding CPU limit should be blocked")
	}
}

func TestBoundaryFilter_MemoryExceed(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:     kernel.TaskActionSubmit,
		MemoryGB:   200, // > max 128
		Source:     "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Exceeding memory limit should be blocked")
	}
}

func TestBoundaryFilter_NegativeResources(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:     kernel.TaskActionSubmit,
		GPUCount:   -1,
		Source:     "test",
	}
	_, err := p.Process(task)
	if err == nil {
		t.Fatal("Negative resources should be blocked")
	}
}

func TestContextFilter_InjectsContext(t *testing.T) {
	p := NewPipeline()
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "pytorch",
		ResourceType: "gpu",
		GPUCount:     1,
		Source:       "test",
	}
	cleaned, err := p.Process(task)
	if err != nil {
		t.Fatalf("Valid task should pass: %v", err)
	}

	resultTask := cleaned.(*kernel.ComputeTask)
	if resultTask.Requirements["_system_id"] != "computehub-gateway" {
		t.Error("Context filter should inject _system_id")
	}
	if resultTask.Requirements["_env"] != "" {
		t.Error("Context filter should inject _env")
	}
	if resultTask.Requirements["_purified_at"] == "" {
		t.Error("Context filter should inject _purified_at timestamp")
	}
}

func TestPipelineStats(t *testing.T) {
	p := NewPipeline()
	_, err := p.Process(&kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "pytorch",
		ResourceType: "gpu",
		GPUCount:     1,
		Source:       "test",
	})
	if err != nil {
		t.Fatalf("Should pass: %v", err)
	}
	stats := p.Stats()
	if stats["total_passed"] != int64(1) {
		t.Errorf("Expected 1 passed, got %v", stats["total_passed"])
	}
}

func TestPipelineLatency(t *testing.T) {
	p := NewPipeline()
	start := time.Now()
	_, err := p.Process(&kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "pytorch",
		ResourceType: "gpu",
		GPUCount:     1,
		Source:       "test",
	})
	elapsed := time.Since(start)
	if err != nil {
		t.Fatalf("Should pass: %v", err)
	}
	if elapsed > 100*time.Millisecond {
		t.Errorf("Pipeline latency too high: %v", elapsed)
	}
}

func TestProductionPipeline(t *testing.T) {
	p := ProductionPipeline()
	if p == nil {
		t.Fatal("ProductionPipeline should not be nil")
	}
}

func TestFullPipelineChain(t *testing.T) {
	p := NewPipeline()
	// This should pass all 4 stages
	task := &kernel.ComputeTask{
		Action:       kernel.TaskActionSubmit,
		Framework:    "jax",
		ResourceType: "tpu",
		GPUCount:     0,
		CPUCount:     4,
		MemoryGB:     16,
		Source:       "test",
	}
	cleaned, err := p.Process(task)
	if err != nil {
		t.Fatalf("Full chain should pass: %v", err)
	}
	resultTask := cleaned.(*kernel.ComputeTask)
	if resultTask.Requirements["_system_id"] != "computehub-gateway" {
		t.Fatal("All 4 filters should complete")
	}
}
