package scheduler

import (
	"container/heap"
	"fmt"
	"sync"
	"time"
)

// ====== 优先级队列 ======

// TaskPriority 任务优先级 (1-10, 10 最高)
type TaskPriority int

const (
	PriorityLow    TaskPriority = 1
	PriorityMedium TaskPriority = 5
	PriorityHigh   TaskPriority = 8
	PriorityCritical TaskPriority = 10
)

// PriorityTask 带优先级的任务
type PriorityTask struct {
	TaskID     string
	Priority   TaskPriority
	Submitted  time.Time
	Payload    interface{}
	Index      int // heap 内部索引
}

// PriorityQueue 优先级队列实现
type PriorityQueue struct {
	mu    sync.Mutex
	items []*PriorityTask
}

func (pq *PriorityQueue) Len() int {
	return len(pq.items)
}

func (pq *PriorityQueue) Less(i, j int) bool {
	// 优先级高的在前，相同优先级先提交的在前
	if pq.items[i].Priority != pq.items[j].Priority {
		return pq.items[i].Priority > pq.items[j].Priority
	}
	return pq.items[i].Submitted.Before(pq.items[j].Submitted)
}

func (pq *PriorityQueue) Swap(i, j int) {
	pq.items[i], pq.items[j] = pq.items[j], pq.items[i]
	pq.items[i].Index = i
	pq.items[j].Index = j
}

func (pq *PriorityQueue) Push(x interface{}) {
	n := len(pq.items)
	task := x.(*PriorityTask)
	task.Index = n
	pq.items = append(pq.items, task)
}

func (pq *PriorityQueue) Pop() interface{} {
	old := pq.items
	n := len(old)
	task := old[n-1]
	old[n-1] = nil
	task.Index = -1
	pq.items = old[:n-1]
	return task
}

// NewPriorityQueue 创建新的优先级队列
func NewPriorityQueue() *PriorityQueue {
	pq := &PriorityQueue{
		items: make([]*PriorityTask, 0),
	}
	heap.Init(pq)
	return pq
}

// PushTask 添加任务到队列
func (pq *PriorityQueue) PushTask(taskID string, priority TaskPriority, payload interface{}) {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	task := &PriorityTask{
		TaskID:   taskID,
		Priority: priority,
		Submitted: time.Now(),
		Payload:  payload,
	}
	heap.Push(pq, task)
}

// PopTask 取出最高优先级的任务
func (pq *PriorityQueue) PopTask() (*PriorityTask, bool) {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	if pq.Len() == 0 {
		return nil, false
	}

	task := heap.Pop(pq).(*PriorityTask)
	return task, true
}

// PeekTask 查看最高优先级任务但不移除
func (pq *PriorityQueue) PeekTask() (*PriorityTask, bool) {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	if pq.Len() == 0 {
		return nil, false
	}

	return pq.items[0], true
}

// RemoveTask 移除指定任务
func (pq *PriorityQueue) RemoveTask(taskID string) bool {
	pq.mu.Lock()
	defer pq.mu.Unlock()

	for i, task := range pq.items {
		if task.TaskID == taskID {
			heap.Remove(pq, i)
			return true
		}
	}
	return false
}

// Size 返回队列长度
func (pq *PriorityQueue) Size() int {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	return pq.Len()
}

// Clear 清空队列
func (pq *PriorityQueue) Clear() {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	pq.items = make([]*PriorityTask, 0)
}

// ====== 优先级调度器 ======

type PriorityScheduler struct {
	config SchedulerConfig
	mu     sync.Mutex
	queue  *PriorityQueue
	nodes  map[string]*NodeInfo
}

// NewPriorityScheduler 创建优先级调度器
func NewPriorityScheduler(config SchedulerConfig) *PriorityScheduler {
	return &PriorityScheduler{
		config: config,
		queue:  NewPriorityQueue(),
		nodes:  make(map[string]*NodeInfo),
	}
}

// RegisterNode 注册节点
func (ps *PriorityScheduler) RegisterNode(info *NodeInfo) {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	ps.nodes[info.ID] = info
}

// SubmitTask 提交任务到优先级队列
func (ps *PriorityScheduler) SubmitTask(taskID string, priority TaskPriority, payload interface{}) error {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	// 检查是否有可用节点
	hasAvailableNode := false
	for _, node := range ps.nodes {
		if node.Status == "online" && node.ActiveTasks < node.MaxTasks {
			hasAvailableNode = true
			break
		}
	}

	if !hasAvailableNode {
		return ErrNoAvailableNode
	}

	ps.queue.PushTask(taskID, priority, payload)
	return nil
}

// ScheduleNext 调度下一个最高优先级任务
func (ps *PriorityScheduler) ScheduleNext() (*ScheduleResult, error) {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	// 取出最高优先级任务
	task, ok := ps.queue.PopTask()
	if !ok {
		return nil, ErrQueueEmpty
	}

	// 找到最佳节点（带优先级感知）
	bestNode := ps.findBestNode(task.Priority)
	if bestNode == nil {
		// 没有可用节点，放回去
		ps.queue.PushTask(task.TaskID, task.Priority, task.Payload)
		return &ScheduleResult{
			Reason: "no available node for priority " + string(rune(task.Priority)),
		}, ErrNoAvailableNode
	}

	// 分配任务
	bestNode.ActiveTasks++

	return &ScheduleResult{
		NodeID:   bestNode.ID,
		TaskID:   task.TaskID,
		Priority: int(task.Priority),
		Reason:   "high priority task dispatched",
	}, nil
}

// findBestNode 根据优先级找到最佳节点
func (ps *PriorityScheduler) findBestNode(priority TaskPriority) *NodeInfo {
	var best *NodeInfo
	bestScore := -1.0

	for _, node := range ps.nodes {
		if node.Status != "online" {
			continue
		}
		if node.ActiveTasks >= node.MaxTasks {
			continue
		}

		score := ps.nodeScore(node, priority)
		if score > bestScore {
			bestScore = score
			best = node
		}
	}

	return best
}

// nodeScore 计算节点评分（考虑优先级）
func (ps *PriorityScheduler) nodeScore(node *NodeInfo, priority TaskPriority) float64 {
	var score float64

	// 高优先级任务选择负载较低的节点
	loadRatio := float64(node.ActiveTasks) / float64(node.MaxTasks)
	score += (1.0 - loadRatio) * 50.0

	// 低延迟优先
	score += float64(200-node.NetworkLatency) / 200.0 * 30.0

	// 高成功率优先
	score += node.SuccessRate * 20.0

	// 高优先级任务加权重
	score += float64(priority) / 10.0 * 10.0

	return score
}

// GetQueueStats 获取队列统计
func (ps *PriorityScheduler) GetQueueStats() map[string]interface{} {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	return map[string]interface{}{
		"queue_size":   ps.queue.Size(),
		"total_nodes":  len(ps.nodes),
		"online_nodes": ps.countOnlineNodes(),
	}
}

func (ps *PriorityScheduler) countOnlineNodes() int {
	count := 0
	for _, node := range ps.nodes {
		if node.Status == "online" {
			count++
		}
	}
	return count
}

// 错误定义
var (
	ErrNoAvailableNode = fmt.Errorf("no available node")
	ErrQueueEmpty      = fmt.Errorf("queue is empty")
)
