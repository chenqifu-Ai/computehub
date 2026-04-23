// Package kernel_test - 确定性内核单元测试
package kernel

import (
	"fmt"
	"testing"
	"time"
)

func TestNewKernel(t *testing.T) {
	k := NewKernelDefaults()
	if k == nil {
		t.Fatal("Kernel should not be nil")
	}
	if k.LinearQueue == nil {
		t.Fatal("LinearQueue should be initialized")
	}
}

func TestKernelStartStop(t *testing.T) {
	k := NewKernelDefaults()
	k.Start()
	time.Sleep(10 * time.Millisecond)
	k.Stop()
}

func TestTaskSubmit(t *testing.T) {
	k := NewKernelDefaults()
	k.Start()
	defer k.Stop()

	task := &ComputeTask{
		Action:       TaskActionSubmit,
		ResourceType: "gpu",
		GPUCount:     1,
		MemoryGB:     8,
		Source:       "test",
	}

	resp := k.Dispatch(task)
	if !resp.Success {
		t.Fatalf("Submit should succeed: %v", resp.Error)
	}

	result, ok := resp.Data.(map[string]any)
	if !ok {
		t.Fatalf("Expected map data, got %T", resp.Data)
	}
	if result["status"] != StatePending {
		t.Errorf("Expected status PENDING, got %v", result["status"])
	}
}

func TestTaskExecute(t *testing.T) {
	k := NewKernelDefaults()
	k.Start()
	defer k.Stop()

	// Submit first
	submitTask := &ComputeTask{
		Action:       TaskActionSubmit,
		ResourceType: "gpu",
		GPUCount:     1,
		Source:       "test",
	}
	submitResp := k.Dispatch(submitTask)
	if !submitResp.Success {
		t.Fatalf("Submit failed: %v", submitResp.Error)
	}

	taskData := submitResp.Data.(map[string]any)
	taskID := fmt.Sprintf("%v", taskData["task_id"])

	// Execute
	execTask := &ComputeTask{
		ID:     taskID,
		Action: TaskActionExecute,
	}
	execResp := k.Dispatch(execTask)
	if !execResp.Success {
		t.Fatalf("Execute failed: %v", execResp.Error)
	}
	if execResp.Data != nil {
		result := execResp.Data.(map[string]any)
		if result["status"] != StateExecuting {
			t.Errorf("Expected EXECUTING, got %v", result["status"])
		}
	}
}

func TestTaskCancel(t *testing.T) {
	k := NewKernelDefaults()
	k.Start()
	defer k.Stop()

	// Submit
	submitTask := &ComputeTask{
		Action:       TaskActionSubmit,
		ResourceType: "cpu",
		GPUCount:     1,
		Source:       "test",
	}
	submitResp := k.Dispatch(submitTask)
	if !submitResp.Success {
		t.Fatalf("Submit failed: %v", submitResp.Error)
	}

	taskData := submitResp.Data.(map[string]any)
	taskID := fmt.Sprintf("%v", taskData["task_id"])

	// Cancel
	cancelTask := &ComputeTask{
		ID:     taskID,
		Action: TaskActionCancel,
	}
	cancelResp := k.Dispatch(cancelTask)
	if !cancelResp.Success {
		t.Fatalf("Cancel failed: %v", cancelResp.Error)
	}
}

func TestTaskStatus(t *testing.T) {
	k := NewKernelDefaults()
	k.Start()
	defer k.Stop()

	// Submit
	submitTask := &ComputeTask{
		Action:       TaskActionSubmit,
		ResourceType: "gpu",
		GPUCount:     1,
		Source:       "test",
	}
	submitResp := k.Dispatch(submitTask)
	if !submitResp.Success {
		t.Fatalf("Submit failed: %v", submitResp.Error)
	}

	taskData := submitResp.Data.(map[string]any)
	taskID := fmt.Sprintf("%v", taskData["task_id"])

	// Status
	statusTask := &ComputeTask{
		ID:     taskID,
		Action: TaskActionStatus,
	}
	statusResp := k.Dispatch(statusTask)
	if !statusResp.Success {
		t.Fatalf("Status query failed: %v", statusResp.Error)
	}
}

func TestTaskNotFound(t *testing.T) {
	k := NewKernelDefaults()
	k.Start()
	defer k.Stop()

	nonExistentTask := &ComputeTask{
		ID:     "task-99999",
		Action: TaskActionExecute,
	}
	resp := k.Dispatch(nonExistentTask)
	if resp.Success {
		t.Fatal("Expected failure for non-existent task")
	}
}

func TestQuotaLimit(t *testing.T) {
	k := NewKernel(10, 10)
	k.SetQuota(Quota{
		MaxGPUs:       2,
		MaxCPUs:       4,
		MaxMemoryGB:   16,
		MaxConcurrent: 2,
		MaxPendingTasks: 5,
	})
	k.Start()
	defer k.Stop()

	// Fill up concurrent tasks
	for i := 0; i < 3; i++ {
		task := &ComputeTask{
			Action:       TaskActionSubmit,
			ResourceType: "gpu",
			GPUCount:     1,
			Source:       "test",
		}
		resp := k.Dispatch(task)
		if !resp.Success && i < 2 {
			t.Fatalf("Task %d submit should succeed: %v", i, resp.Error)
		}
	}
}

func TestInfo(t *testing.T) {
	k := NewKernelDefaults()
	info := k.Info()
	if info["status"] != "RUNNING" {
		t.Errorf("Expected status RUNNING, got %v", info["status"])
	}
	if _, ok := info["total_tasks"]; !ok {
		t.Error("Info should contain total_tasks")
	}
	if _, ok := info["uptime"]; !ok {
		t.Error("Info should contain uptime")
	}
}
