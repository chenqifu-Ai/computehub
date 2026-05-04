package composer

import (
	"context"
	"testing"
	"time"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.MaxConcurrency != 10 {
		t.Errorf("Expected MaxConcurrency 10, got %d", cfg.MaxConcurrency)
	}
	if cfg.Timeout != 300*time.Second {
		t.Errorf("Expected Timeout 300s, got %v", cfg.Timeout)
	}
	if cfg.MaxFailures != 2 {
		t.Errorf("Expected MaxFailures 2, got %d", cfg.MaxFailures)
	}
	if cfg.DecomposeModel != "qwen3.6-35b" {
		t.Errorf("Expected DecomposeModel 'qwen3.6-35b', got '%s'", cfg.DecomposeModel)
	}
}

func TestNewTaskComposer(t *testing.T) {
	cfg := DefaultConfig()
	tc := NewTaskComposer(cfg, "", "")

	if tc == nil {
		t.Fatal("TaskComposer should not be nil")
	}
	if tc.Decomposer == nil {
		t.Fatal("Decomposer should not be nil")
	}
	if tc.DispatchEngine == nil {
		t.Fatal("DispatchEngine should not be nil")
	}
	if tc.Compositor == nil {
		t.Fatal("Compositor should not be nil")
	}
}

func TestNewDispatchEngine(t *testing.T) {
	models := []string{"qwen2.5:3b", "glm-4.7-flash"}
	de := NewDispatchEngine(models, 5, 30*time.Second)

	if de == nil {
		t.Fatal("DispatchEngine should not be nil")
	}
	if len(de.Models) != 2 {
		t.Errorf("Expected 2 models, got %d", len(de.Models))
	}
	if de.MaxConcurrency != 5 {
		t.Errorf("Expected MaxConcurrency 5, got %d", de.MaxConcurrency)
	}
}

func TestDispatchEngineSelectModel(t *testing.T) {
	models := []string{"test-model"}
	de := NewDispatchEngine(models, 5, 30*time.Second)

	selected := de.selectModel()
	if selected != "test-model" {
		t.Errorf("Expected 'test-model', got '%s'", selected)
	}
}

func TestDispatchEngineSelectModelUnknown(t *testing.T) {
	de := NewDispatchEngine([]string{}, 5, 30*time.Second)
	selected := de.selectModel()
	if selected != "unknown" {
		t.Errorf("Expected 'unknown' for empty models, got '%s'", selected)
	}
}

func TestDispatchEngineDispatch(t *testing.T) {
	models := []string{"test-model"}
	de := NewDispatchEngine(models, 5, 30*time.Second)
	ctx := context.Background()

	tasks := []DecomposedTask{
		{ID: "sub_1", Description: "Task 1"},
		{ID: "sub_2", Description: "Task 2"},
		{ID: "sub_3", Description: "Task 3"},
	}

	results, err := de.Dispatch(ctx, tasks)
	if err != nil {
		t.Fatalf("Dispatch failed: %v", err)
	}
	if len(results) != 3 {
		t.Errorf("Expected 3 results, got %d", len(results))
	}

	for _, r := range results {
		if !r.Success {
			t.Errorf("Subtask %s should succeed (mock), got error: %s", r.SubtaskID, r.Error)
		}
		if r.ModelUsed != "test-model" {
			t.Errorf("Expected model 'test-model', got '%s'", r.ModelUsed)
		}
	}
}

func TestDispatchEngineContextCancellation(t *testing.T) {
	models := []string{"test-model"}
	de := NewDispatchEngine(models, 5, 30*time.Second)

	// Cancelled context
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	tasks := []DecomposedTask{
		{ID: "sub_1", Description: "Task 1"},
	}

	results, err := de.Dispatch(ctx, tasks)
	if err != nil {
		t.Fatalf("Dispatch should not return error on cancellation: %v", err)
	}

	// Results might or might not have succeeded depending on goroutine timing
	_ = results
}

func TestDispatchEnginePriority(t *testing.T) {
	models := []string{"test-model"}
	de := NewDispatchEngine(models, 5, 30*time.Second)
	ctx := context.Background()

	tasks := []DecomposedTask{
		{ID: "low", Description: "Low priority", Priority: 1},
		{ID: "high", Description: "High priority", Priority: 10},
		{ID: "med", Description: "Medium priority", Priority: 5},
	}

	results, err := de.Dispatch(ctx, tasks)
	if err != nil {
		t.Fatalf("Dispatch failed: %v", err)
	}
	if len(results) != 3 {
		t.Errorf("Expected 3 results, got %d", len(results))
	}
}

func TestLLMDecomposer(t *testing.T) {
	t.Skip("需要真实的 LLM API 才能运行")

	// 设置真实 API URL 后测试:
	// LLMDecomposer{
	//   Model:  "qwen3.6-35b-common",
	//   Prompt: "请将以下任务分解为子任务",
	//   APIURL: "https://ai.zhangtuokeji.top:9090/v1",
	//   APIKey: "sk-xxx",
	// }
}

func TestLLMDecomposerWithContext(t *testing.T) {
	t.Skip("需要真实的 LLM API 才能运行")
}

func TestLLMCompositor(t *testing.T) {
	t.Skip("需要真实的 LLM API 才能运行")
}

func TestLLMCompositorWithFailures(t *testing.T) {
	t.Skip("需要真实的 LLM API 才能运行")
}

func TestCallLLM(t *testing.T) {
	t.Skip("需要网络连接才能运行")
}

func TestCallSmallModel(t *testing.T) {
	t.Skip("需要网络连接才能运行")
}

func TestParseDecomposeResult(t *testing.T) {
	// Test with valid JSON
	result, err := parseDecomposeResult("task-001", `{"subtasks":[{"id":"sub_1","description":"分析数据","expected_output":"结果","priority":5}]}`)
	if err != nil {
		t.Fatalf("parseDecomposeResult JSON failed: %v", err)
	}
	if result.TaskID != "task-001" {
		t.Errorf("Expected TaskID 'task-001', got '%s'", result.TaskID)
	}
	if len(result.Subtasks) != 1 {
		t.Errorf("Expected 1 subtask, got %d", len(result.Subtasks))
	}
	if result.Subtasks[0].ID != "sub_1" {
		t.Errorf("Expected sub_1, got %s", result.Subtasks[0].ID)
	}

	// Test with codeblock JSON
	result2, err2 := parseDecomposeResult("task-002", "```json\n{\"subtasks\":[{\"id\":\"sub_a\",\"description\":\"task A\"}]}\n```")
	if err2 != nil {
		t.Fatalf("parseDecomposeResult codeblock failed: %v", err2)
	}
	if len(result2.Subtasks) != 1 {
		t.Errorf("Expected 1 subtask from codeblock, got %d", len(result2.Subtasks))
	}

	// Test with plain text fallback
	result3, err3 := parseDecomposeResult("task-003", "随便一段文字")
	if err3 != nil {
		t.Fatalf("parseDecomposeResult fallback failed: %v", err3)
	}
	if len(result3.Subtasks) != 1 {
		t.Errorf("Expected 1 fallback subtask, got %d", len(result3.Subtasks))
	}
}

func TestSortTasksByPriority(t *testing.T) {
	tasks := []DecomposedTask{
		{ID: "low", Priority: 1},
		{ID: "high", Priority: 10},
		{ID: "med", Priority: 5},
	}

	sortTasksByPriority(tasks)

	if tasks[0].ID != "high" {
		t.Errorf("Expected first task 'high', got '%s'", tasks[0].ID)
	}
	if tasks[1].ID != "med" {
		t.Errorf("Expected second task 'med', got '%s'", tasks[1].ID)
	}
	if tasks[2].ID != "low" {
		t.Errorf("Expected third task 'low', got '%s'", tasks[2].ID)
	}
}

func TestMin(t *testing.T) {
	if min(1, 2) != 1 {
		t.Error("min(1,2) should be 1")
	}
	if min(5, 3) != 3 {
		t.Error("min(5,3) should be 3")
	}
	if min(4, 4) != 4 {
		t.Error("min(4,4) should be 4")
	}
}

func TestComposerOutputStructure(t *testing.T) {
	output := &TaskComposerOutput{
		TaskID:      "test-output",
		Success:     true,
		Subtasks:    []DecomposedTask{{ID: "sub_1"}},
		Results:     []SubtaskExecution{{SubtaskID: "sub_1", Success: true}},
		FinalResult: "Final answer",
	}

	if output.TaskID != "test-output" {
		t.Errorf("Expected TaskID 'test-output', got '%s'", output.TaskID)
	}
	if !output.Success {
		t.Error("Expected Success to be true")
	}
}

func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
