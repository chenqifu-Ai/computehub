package scheduler

import (
	"sync"
	"time"
)

// PreemptResult 抢占结果
type PreemptResult struct {
	PreemptedTaskID string // 被抢占的任务ID
	NewTaskID       string // 抢占者任务ID
	NodeID          string // 节点ID
	Reason          string // 原因
}

// PreemptManager 抢占管理器
type PreemptManager struct {
	mu      sync.Mutex
	queue   *PriorityQueue
	nodes   map[string]*NodeInfo
}

// NewPreemptManager 创建抢占管理器
func NewPreemptManager(queue *PriorityQueue) *PreemptManager {
	return &PreemptManager{
		queue: queue,
		nodes: make(map[string]*NodeInfo),
	}
}

// RegisterNode 注册节点
func (pm *PreemptManager) RegisterNode(node *NodeInfo) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	pm.nodes[node.ID] = node
}

// TryPreempt 尝试抢占低优先级任务
// 返回被抢占的任务ID（需外部优雅终止）
func (pm *PreemptManager) TryPreempt(newTaskID string, newPriority TaskPriority, payload interface{}) (*PreemptResult, error) {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	// 1. 查找所有节点上运行的最低优先级任务
	var lowestNodeID string
	var lowestTaskID string
	var lowestPriority TaskPriority = PriorityCritical + 1 // 初始化为比最高还高

	for nodeID, node := range pm.nodes {
		if node.Status != "online" {
			continue
		}
		// 简化：每节点只看是否有活跃任务，不精确追踪每个任务的优先级
		// 真正的实现需要任务级优先级追踪
		if node.ActiveTasks > 0 {
			// 负载高的节点优先被抢占
			loadRatio := float64(node.ActiveTasks) / float64(node.MaxTasks)
			if loadRatio > 0.5 && lowestPriority > PriorityLow {
				// 找到一个高负载节点，记录
				if lowestNodeID == "" || loadRatio > float64(node.ActiveTasks)/float64(node.MaxTasks) {
					lowestNodeID = nodeID
					lowestTaskID = newTaskID + "-placeholder"
					lowestPriority = PriorityLow
				}
			}
		}
	}

	// 简化处理：没有节点运行任务，直接放队列
	if lowestNodeID == "" {
		pm.queue.PushTask(newTaskID, newPriority, payload)
		return nil, nil
	}

	// 2. 检查新任务优先级是否高于被占用的任务
	// 简化：如果节点负载高且新任务是 Critical 或 High，直接抢占
	if newPriority >= PriorityHigh {
		// 记录被抢占的节点
		result := &PreemptResult{
			PreemptedTaskID: lowestTaskID,
			NewTaskID:       newTaskID,
			NodeID:          lowestNodeID,
			Reason:          "high priority preemption",
		}

		// 将新任务放入队列（调度时会优先分配）
		pm.queue.PushTask(newTaskID, newPriority, payload)

		return result, nil
	}

	// 3. 优先级不够，放队列等待
	pm.queue.PushTask(newTaskID, newPriority, payload)
	return nil, nil
}

// OnTaskCompleted 任务完成回调 - 检查是否有任务可以调度
func (pm *PreemptManager) OnTaskCompleted(nodeID string) *PreemptResult {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	// 检查队列是否有等待的任务
	task, ok := pm.queue.PeekTask()
	if !ok {
		return nil
	}

	node, exists := pm.nodes[nodeID]
	if !exists || node.Status != "online" {
		return nil
	}

	// 有空间调度新任务
	if node.ActiveTasks < node.MaxTasks {
		pm.queue.PopTask() // 出队
		return &PreemptResult{
			NewTaskID: task.TaskID,
			NodeID:    nodeID,
			Reason:    "task completed, new task scheduled",
		}
	}

	return nil
}

// ====== 时间片轮转 (GPU-Share 预研) ======

// TimeSliceManager GPU 时间片管理器 (未来实现)
type TimeSliceManager struct {
	mu           sync.Mutex
	timeSlice    time.Duration // 每个时间片长度 (默认 10ms)
	activeTasks  map[string]time.Time // taskID -> last scheduled
}

func NewTimeSliceManager() *TimeSliceManager {
	return &TimeSliceManager{
		timeSlice:   10 * time.Millisecond,
		activeTasks: make(map[string]time.Time),
	}
}

// AllocateTimeSlice 分配时间片
func (tsm *TimeSliceManager) AllocateTimeSlice(taskID string) bool {
	tsm.mu.Lock()
	defer tsm.mu.Unlock()

	lastScheduled, exists := tsm.activeTasks[taskID]
	now := time.Now()

	if !exists || now.Sub(lastScheduled) >= tsm.timeSlice {
		tsm.activeTasks[taskID] = now
		return true
	}

	return false
}
