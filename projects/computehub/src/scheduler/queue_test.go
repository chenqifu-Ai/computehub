package scheduler

import (
	"testing"
)

func TestPriorityQueueBasic(t *testing.T) {
	pq := NewPriorityQueue()

	pq.PushTask("task-1", PriorityHigh, nil)
	pq.PushTask("task-2", PriorityLow, nil)
	pq.PushTask("task-3", PriorityCritical, nil)

	// 应该按优先级取出
	task, ok := pq.PopTask()
	if !ok || task.TaskID != "task-3" {
		t.Errorf("Expected task-3 (Critical), got %s", task.TaskID)
	}

	task, ok = pq.PopTask()
	if !ok || task.TaskID != "task-1" {
		t.Errorf("Expected task-1 (High), got %s", task.TaskID)
	}

	task, ok = pq.PopTask()
	if !ok || task.TaskID != "task-2" {
		t.Errorf("Expected task-2 (Low), got %s", task.TaskID)
	}
}

func TestPriorityQueueSamePriority(t *testing.T) {
	pq := NewPriorityQueue()

	pq.PushTask("task-1", PriorityMedium, nil)
	pq.PushTask("task-2", PriorityMedium, nil)

	task1, _ := pq.PopTask()
	task2, _ := pq.PopTask()

	// 相同优先级应该按时间顺序
	if task1.Submitted.After(task2.Submitted) {
		t.Error("Same priority should be FIFO")
	}
}

func TestPriorityQueuePeek(t *testing.T) {
	pq := NewPriorityQueue()

	pq.PushTask("task-1", PriorityHigh, nil)

	task, ok := pq.PeekTask()
	if !ok || task.TaskID != "task-1" {
		t.Errorf("Expected task-1, got %s", task.TaskID)
	}

	// Peek 不移除
	if pq.Size() != 1 {
		t.Errorf("Expected size 1, got %d", pq.Size())
	}
}

func TestPriorityQueueRemove(t *testing.T) {
	pq := NewPriorityQueue()

	pq.PushTask("task-1", PriorityHigh, nil)
	pq.PushTask("task-2", PriorityLow, nil)

	if !pq.RemoveTask("task-1") {
		t.Error("RemoveTask should return true")
	}

	if pq.Size() != 1 {
		t.Errorf("Expected size 1, got %d", pq.Size())
	}
}

func TestPriorityQueueClear(t *testing.T) {
	pq := NewPriorityQueue()

	pq.PushTask("task-1", PriorityHigh, nil)
	pq.PushTask("task-2", PriorityLow, nil)

	pq.Clear()

	if pq.Size() != 0 {
		t.Errorf("Expected size 0 after clear, got %d", pq.Size())
	}
}

func TestPriorityQueueEmpty(t *testing.T) {
	pq := NewPriorityQueue()

	_, ok := pq.PopTask()
	if ok {
		t.Error("Should return false for empty queue")
	}
}

func TestPriorityScheduler(t *testing.T) {
	ps := NewPriorityScheduler(DefaultConfig())

	// 注册节点
	ps.RegisterNode(&NodeInfo{
		ID:         "node-1",
		Region:     "us-east",
		Status:     "online",
		MaxTasks:   10,
		SuccessRate: 1.0,
	})

	// 提交不同优先级任务
	ps.SubmitTask("high-task", PriorityHigh, nil)
	ps.SubmitTask("low-task", PriorityLow, nil)
	ps.SubmitTask("critical-task", PriorityCritical, nil)

	// 调度
	result, err := ps.ScheduleNext()
	if err != nil {
		t.Fatalf("ScheduleNext failed: %v", err)
	}

	if result.TaskID != "critical-task" {
		t.Errorf("Expected critical-task, got %s", result.TaskID)
	}

	// 验证节点负载增加
	node := ps.nodes["node-1"]
	if node.ActiveTasks != 1 {
		t.Errorf("Expected 1 active task, got %d", node.ActiveTasks)
	}
}

func TestPrioritySchedulerEmptyQueue(t *testing.T) {
	ps := NewPriorityScheduler(DefaultConfig())

	_, err := ps.ScheduleNext()
	if err != ErrQueueEmpty {
		t.Errorf("Expected ErrQueueEmpty, got %v", err)
	}
}

func TestPrioritySchedulerNoNode(t *testing.T) {
	ps := NewPriorityScheduler(DefaultConfig())

	err := ps.SubmitTask("task-1", PriorityHigh, nil)
	if err != ErrNoAvailableNode {
		t.Errorf("Expected ErrNoAvailableNode, got %v", err)
	}
}

func TestPrioritySchedulerAllNodesBusy(t *testing.T) {
	ps := NewPriorityScheduler(DefaultConfig())

	ps.RegisterNode(&NodeInfo{
		ID:         "node-1",
		Region:     "us-east",
		Status:     "online",
		MaxTasks:   1,
		SuccessRate: 1.0,
	})

	ps.SubmitTask("task-1", PriorityHigh, nil)
	ps.ScheduleNext() // 占满节点

	err := ps.SubmitTask("task-2", PriorityCritical, nil)
	if err != ErrNoAvailableNode {
		t.Errorf("Expected ErrNoAvailableNode, got %v", err)
	}
}

func TestPrioritySchedulerPriorityOrder(t *testing.T) {
	ps := NewPriorityScheduler(DefaultConfig())

	ps.RegisterNode(&NodeInfo{
		ID:         "node-1",
		Region:     "us-east",
		Status:     "online",
		MaxTasks:   100,
		SuccessRate: 1.0,
	})

	// 提交顺序相反
	ps.SubmitTask("task-low", PriorityLow, nil)
	ps.SubmitTask("task-high", PriorityHigh, nil)
	ps.SubmitTask("task-critical", PriorityCritical, nil)

	// 应该按优先级取出
	results := make([]string, 0, 3)
	for i := 0; i < 3; i++ {
		result, err := ps.ScheduleNext()
		if err != nil {
			t.Fatalf("ScheduleNext failed at iteration %d: %v", i, err)
		}
		results = append(results, result.TaskID)
	}

	expected := []string{"task-critical", "task-high", "task-low"}
	for i, exp := range expected {
		if results[i] != exp {
			t.Errorf("Expected %s at position %d, got %s", exp, i, results[i])
		}
	}
}

func BenchmarkPriorityQueuePush(b *testing.B) {
	pq := NewPriorityQueue()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		pq.PushTask("", PriorityMedium, nil)
	}
}

func BenchmarkPrioritySchedulerSchedule(b *testing.B) {
	ps := NewPriorityScheduler(DefaultConfig())
	ps.RegisterNode(&NodeInfo{
		ID:         "node-1",
		Region:     "us-east",
		Status:     "online",
		MaxTasks:   1000,
		SuccessRate: 1.0,
	})

	for i := 0; i < b.N; i++ {
		ps.SubmitTask("", PriorityMedium, nil)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ps.ScheduleNext()
	}
}
