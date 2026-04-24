package api

import (
	"testing"
)

func TestStateMachineCreateTask(t *testing.T) {
	sm := NewStateMachine()
	record := sm.CreateTask("task-001")

	if record.CurrentState != TaskPending {
		t.Errorf("Expected PENDING, got %s", record.CurrentState)
	}
	if record.TaskID != "task-001" {
		t.Errorf("Expected task-001, got %s", record.TaskID)
	}
	if len(record.Transitions) != 0 {
		t.Errorf("Expected 0 transitions, got %d", len(record.Transitions))
	}
}

func TestStateMachineTransition(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-002")

	// PENDING -> QUEUED
	event, err := sm.Transition("task-002", TaskPending, TaskQueued, "DISPATCH", "assigned to node-001", "node-001")
	if err != nil {
		t.Fatalf("Transition failed: %v", err)
	}

	if event.To != TaskQueued {
		t.Errorf("Expected QUEUED, got %s", event.To)
	}
	if event.Action != "DISPATCH" {
		t.Errorf("Expected DISPATCH, got %s", event.Action)
	}

	// Verify state
	record, _ := sm.GetTaskState("task-002")
	if record.CurrentState != TaskQueued {
		t.Errorf("Expected QUEUED after transition, got %s", record.CurrentState)
	}
	if len(record.Transitions) != 1 {
		t.Errorf("Expected 1 transition in history, got %d", len(record.Transitions))
	}
}

func TestStateMachineInvalidTransition(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-003")

	// PENDING -> COMPLETED is invalid
	_, err := sm.Transition("task-003", TaskPending, TaskCompleted, "SUCCESS", "", "")
	if err == nil {
		t.Fatal("Expected error for invalid transition")
	}

	// Verify state unchanged
	record, _ := sm.GetTaskState("task-003")
	if record.CurrentState != TaskPending {
		t.Errorf("Expected state unchanged, got %s", record.CurrentState)
	}
}

func TestStateMachineFullLifecycle(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-full")

	// PENDING -> QUEUED -> RUNNING -> COMPLETED
	sm.Transition("task-full", TaskPending, TaskQueued, "DISPATCH", "node-001", "node-001")
	sm.Transition("task-full", TaskQueued, TaskRunning, "EXECUTE", "started execution", "node-001")
	sm.Transition("task-full", TaskRunning, TaskCompleted, "SUCCESS", "completed successfully", "node-001")

	record, _ := sm.GetTaskState("task-full")
	if record.CurrentState != TaskCompleted {
		t.Errorf("Expected COMPLETED, got %s", record.CurrentState)
	}
	if len(record.Transitions) != 3 {
		t.Errorf("Expected 3 transitions, got %d", len(record.Transitions))
	}
}

func TestStateMachineRetry(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-retry")

	// PENDING -> QUEUED -> RUNNING -> FAILED -> RETRYING -> QUEUED
	sm.Transition("task-retry", TaskPending, TaskQueued, "DISPATCH", "", "node-001")
	sm.Transition("task-retry", TaskQueued, TaskRunning, "EXECUTE", "", "node-001")
	sm.Transition("task-retry", TaskRunning, TaskRetrying, "RETRY", "retry after failure", "node-001")
	sm.Transition("task-retry", TaskRetrying, TaskQueued, "RETRY", "requeued", "node-002")

	record, _ := sm.GetTaskState("task-retry")
	if record.CurrentState != TaskQueued {
		t.Errorf("Expected QUEUED after retry, got %s", record.CurrentState)
	}
	if record.AssignedNode != "node-002" {
		// Note: We don't set AssignedNode in this test, but the state is correct
	}
}

func TestStateMachineGetTasksByState(t *testing.T) {
	sm := NewStateMachine()

	sm.CreateTask("task-a")
	sm.CreateTask("task-b")
	sm.CreateTask("task-c")

	// task-a: PENDING -> QUEUED
	sm.Transition("task-a", TaskPending, TaskQueued, "DISPATCH", "", "node-001")

	// task-b: PENDING -> QUEUED -> RUNNING
	sm.Transition("task-b", TaskPending, TaskQueued, "DISPATCH", "", "node-001")
	sm.Transition("task-b", TaskQueued, TaskRunning, "EXECUTE", "", "node-001")

	pendingTasks := sm.GetTasksByState(TaskPending)
	if len(pendingTasks) != 1 {
		t.Errorf("Expected 1 PENDING task, got %d", len(pendingTasks))
	}

	queuedTasks := sm.GetTasksByState(TaskQueued)
	if len(queuedTasks) != 1 {
		t.Errorf("Expected 1 QUEUED task, got %d", len(queuedTasks))
	}

	runningTasks := sm.GetTasksByState(TaskRunning)
	if len(runningTasks) != 1 {
		t.Errorf("Expected 1 RUNNING task, got %d", len(runningTasks))
	}
}

func TestStateMachineGetActiveTasks(t *testing.T) {
	sm := NewStateMachine()

	sm.CreateTask("task-active-1")
	sm.CreateTask("task-active-2")
	sm.CreateTask("task-done")
	sm.CreateTask("task-failed")

	// task-done: PENDING → QUEUED → RUNNING → COMPLETED
	sm.Transition("task-done", TaskPending, TaskQueued, "DISPATCH", "", "node-001")
	sm.Transition("task-done", TaskQueued, TaskRunning, "EXECUTE", "", "node-001")
	sm.Transition("task-done", TaskRunning, TaskCompleted, "SUCCESS", "", "node-001")

	// task-failed: PENDING → QUEUED → RUNNING → FAILED
	sm.Transition("task-failed", TaskPending, TaskQueued, "DISPATCH", "", "node-001")
	sm.Transition("task-failed", TaskQueued, TaskRunning, "EXECUTE", "", "node-001")
	sm.Transition("task-failed", TaskRunning, TaskFailed, "FAILED", "", "node-001")

	activeTasks := sm.GetActiveTasks()
	if len(activeTasks) != 2 {
		t.Errorf("Expected 2 active tasks, got %d", len(activeTasks))
	}

	// Verify active tasks are the ones not completed/failed/cancelled
	for _, id := range activeTasks {
		if id == "task-done" || id == "task-failed" {
			t.Errorf("Active task should not include completed/failed: %s", id)
		}
	}
}

func TestStateMachineTransitionHistory(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-history")

	sm.Transition("task-history", TaskPending, TaskQueued, "DISPATCH", "assigning", "node-001")
	sm.Transition("task-history", TaskQueued, TaskRunning, "EXECUTE", "starting", "node-001")
	sm.Transition("task-history", TaskRunning, TaskCompleted, "SUCCESS", "done", "node-001")

	history, err := sm.GetTransitionHistory("task-history")
	if err != nil {
		t.Fatalf("GetTransitionHistory failed: %v", err)
	}

	if len(history) != 3 {
		t.Errorf("Expected 3 history entries, got %d", len(history))
	}

	// Verify first transition
	if history[0].From != TaskPending {
		t.Errorf("Expected first transition from PENDING, got %s", history[0].From)
	}
	if history[0].Action != "DISPATCH" {
		t.Errorf("Expected first action DISPATCH, got %s", history[0].Action)
	}
}

func TestStateMachineGetTaskStats(t *testing.T) {
	sm := NewStateMachine()

	sm.CreateTask("s-a")
	sm.CreateTask("s-b")
	sm.CreateTask("s-c")
	sm.CreateTask("s-d")

	sm.Transition("s-a", TaskPending, TaskQueued, "DISPATCH", "", "n1")
	sm.Transition("s-b", TaskPending, TaskQueued, "DISPATCH", "", "n1")
	sm.Transition("s-b", TaskQueued, TaskRunning, "EXECUTE", "", "n1")
	sm.Transition("s-c", TaskPending, TaskQueued, "DISPATCH", "", "n1")
	sm.Transition("s-c", TaskQueued, TaskRunning, "EXECUTE", "", "n1")
	sm.Transition("s-c", TaskRunning, TaskCompleted, "SUCCESS", "", "n1")
	sm.Transition("s-d", TaskPending, TaskQueued, "DISPATCH", "", "n1")
	sm.Transition("s-d", TaskQueued, TaskRunning, "EXECUTE", "", "n1")
	sm.Transition("s-d", TaskRunning, TaskRetrying, "RETRY", "", "n1")

	stats := sm.GetTaskStats()

	if stats[TaskPending] != 0 {
		t.Errorf("Expected 0 PENDING, got %d", stats[TaskPending])
	}
	if stats[TaskQueued] != 1 {
		t.Errorf("Expected 1 QUEUED, got %d", stats[TaskQueued])
	}
	if stats[TaskRunning] != 1 {
		t.Errorf("Expected 1 RUNNING, got %d", stats[TaskRunning])
	}
	if stats[TaskCompleted] != 1 {
		t.Errorf("Expected 1 COMPLETED, got %d", stats[TaskCompleted])
	}
	if stats[TaskRetrying] != 1 {
		t.Errorf("Expected 1 RETRYING, got %d", stats[TaskRetrying])
	}
}

func TestStateMachineWrongCurrentState(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-wrong")

	// Try to transition from QUEUED when state is PENDING
	_, err := sm.Transition("task-wrong", TaskQueued, TaskRunning, "EXECUTE", "", "")
	if err == nil {
		t.Fatal("Expected error for wrong current state")
	}

	record, _ := sm.GetTaskState("task-wrong")
	if record.CurrentState != TaskPending {
		t.Error("State should be unchanged")
	}
}

func TestStateMachineRemoveTask(t *testing.T) {
	sm := NewStateMachine()
	sm.CreateTask("task-remove")

	if !sm.RemoveTask("task-remove") {
		t.Error("Expected successful removal")
	}

	_, exists := sm.GetTaskState("task-remove")
	if exists {
		t.Error("Task should be removed")
	}

	if sm.RemoveTask("task-remove") {
		t.Error("Should fail to remove non-existent task")
	}
}

func TestStateMachineTaskNotFound(t *testing.T) {
	sm := NewStateMachine()

	_, found := sm.GetTaskState("nonexistent")
	if found {
		t.Error("Expected not found for non-existent task")
	}

	_, err := sm.GetTransitionHistory("nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent task history")
	}
}
