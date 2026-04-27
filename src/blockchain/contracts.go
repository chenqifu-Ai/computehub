// Package blockchain — Sprint 3 智能合约层
// TaskRegistry, PaymentEscrow, NodeStaking, DisputeResolution
package blockchain

import (
	"fmt"
	"sync"
	"time"
)

// ════════════════════════════════════════════════════════════════════
// Contract 类型常量
// ════════════════════════════════════════════════════════════════════

const (
	ContractStatusActive   = "active"
	ContractStatusExecuted = "executed"
	ContractStatusExpired  = "expired"
	ContractStatusDisputed = "disputed"

	StakeStatusActive   = "active"
	StakeStatusSlashing = "slashing"
	StakeStatusReleased = "released"

	EscrowStatusLocked   = "locked"
	EscrowStatusReleased = "released"
	EscrowStatusRefunded = "refunded"

	TaskStatusPending   = "pending"
	TaskStatusRunning   = "running"
	TaskStatusCompleted = "completed"
	TaskStatusFailed    = "failed"
	TaskStatusDisputed  = "disputed"

	DisputeStatusOpen     = "open"
	DisputeStatusEvidence = "evidence"
	DisputeStatusVoting   = "voting"
	DisputeStatusResolved = "resolved"
	DisputeStatusAppealed = "appealed"

	// 默认参数
	DefaultStakeMinAmount     = 100.0  // 最低质押量
	DefaultStakeLockPeriod    = 7 * 24 * time.Hour
	DefaultSlashPercent       = 0.10   // 惩罚比例 10%
	DefaultRewardPerBlock     = 0.5    // 每区块奖励 0.5 CHB
	DefaultDisputeVotePeriod  = 48 * time.Hour
)

// ════════════════════════════════════════════════════════════════════
// 1. TaskRegistry — 任务登记和状态追踪
// ════════════════════════════════════════════════════════════════════

// TaskRecord 记录任务的完整生命周期
type TaskRecord struct {
	ID             string    `json:"id"`
	ClientAddr     string    `json:"client_addr"`     // 提交者地址
	NodeAddr       string    `json:"node_addr"`       // 执行节点地址
	ResourceType   string    `json:"resource_type"`
	GPUCount       int       `json:"gpu_count"`
	CPUCount       int       `json:"cpu_count"`
	MemoryGB       int       `json:"memory_gb"`
	MaxDurationSec int       `json:"max_duration_sec"`
	Priority       int       `json:"priority"`
	Status         string    `json:"status"`
	Budget         float64   `json:"budget"`          // 预算 (CHB)
	ActualCost     float64   `json:"actual_cost"`     // 实际花费 (CHB)
	CreatedAt      time.Time `json:"created_at"`
	StartedAt      time.Time `json:"started_at,omitempty"`
	CompletedAt    time.Time `json:"completed_at,omitempty"`
	EscrowID       string    `json:"escrow_id,omitempty"` // 对应托管合约
	DisputeID      string    `json:"dispute_id,omitempty"`
	Metadata       string    `json:"metadata,omitempty"`
}

// TaskRegistry 管理任务注册表
type TaskRegistry struct {
	mu     sync.RWMutex
	tasks  map[string]*TaskRecord
}

// NewTaskRegistry 创建任务注册表
func NewTaskRegistry() *TaskRegistry {
	return &TaskRegistry{
		tasks: make(map[string]*TaskRecord),
	}
}

// RegisterTask 登记新任务
func (tr *TaskRegistry) RegisterTask(id, clientAddr string, req TaskRequirement, budget float64, escrowID string) (*TaskRecord, error) {
	tr.mu.Lock()
	defer tr.mu.Unlock()

	if _, exists := tr.tasks[id]; exists {
		return nil, fmt.Errorf("task %s already registered", id)
	}

	task := &TaskRecord{
		ID:             id,
		ClientAddr:     clientAddr,
		ResourceType:   req.ResourceType,
		GPUCount:       req.GPUCount,
		CPUCount:       req.CPUCount,
		MemoryGB:       req.MemoryGB,
		MaxDurationSec: req.MaxDurationSec,
		Priority:       req.Priority,
		Status:         TaskStatusPending,
		Budget:         budget,
		CreatedAt:      time.Now(),
		EscrowID:       escrowID,
	}
	tr.tasks[id] = task
	return task, nil
}

// AssignTask 分配任务给节点
func (tr *TaskRegistry) AssignTask(taskID, nodeAddr string) error {
	tr.mu.Lock()
	defer tr.mu.Unlock()

	task, exists := tr.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}
	if task.Status != TaskStatusPending {
		return fmt.Errorf("task %s is not pending (status: %s)", taskID, task.Status)
	}

	task.NodeAddr = nodeAddr
	task.Status = TaskStatusRunning
	task.StartedAt = time.Now()
	return nil
}

// CompleteTask 完成任务并记录成本
func (tr *TaskRegistry) CompleteTask(taskID string, actualCost float64) error {
	tr.mu.Lock()
	defer tr.mu.Unlock()

	task, exists := tr.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}
	if task.Status != TaskStatusRunning {
		return fmt.Errorf("task %s is not running (status: %s)", taskID, task.Status)
	}

	task.Status = TaskStatusCompleted
	task.ActualCost = actualCost
	task.CompletedAt = time.Now()
	return nil
}

// FailTask 标记任务失败
func (tr *TaskRegistry) FailTask(taskID, reason string) error {
	tr.mu.Lock()
	defer tr.mu.Unlock()

	task, exists := tr.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Status = TaskStatusFailed
	task.CompletedAt = time.Now()
	task.Metadata = reason
	return nil
}

// GetTask 查询任务
func (tr *TaskRegistry) GetTask(taskID string) (*TaskRecord, bool) {
	tr.mu.RLock()
	defer tr.mu.RUnlock()
	task, exists := tr.tasks[taskID]
	return task, exists
}

// ListTasksByClient 查询客户的所有任务
func (tr *TaskRegistry) ListTasksByClient(clientAddr string) []*TaskRecord {
	tr.mu.RLock()
	defer tr.mu.RUnlock()
	var result []*TaskRecord
	for _, t := range tr.tasks {
		if t.ClientAddr == clientAddr {
			result = append(result, t)
		}
	}
	return result
}

// ListTasksByStatus 按状态查询
func (tr *TaskRegistry) ListTasksByStatus(status string) []*TaskRecord {
	tr.mu.RLock()
	defer tr.mu.RUnlock()
	var result []*TaskRecord
	for _, t := range tr.tasks {
		if t.Status == status {
			result = append(result, t)
		}
	}
	return result
}

// TaskStats 返回任务统计数据
func (tr *TaskRegistry) TaskStats() map[string]int {
	tr.mu.RLock()
	defer tr.mu.RUnlock()
	stats := map[string]int{
		"total":     len(tr.tasks),
		"pending":   0, "running": 0, "completed": 0,
		"failed": 0, "disputed": 0,
	}
	for _, t := range tr.tasks {
		stats[t.Status]++
	}
	return stats
}

// ════════════════════════════════════════════════════════════════════
// 2. PaymentEscrow — 资金托管和释放
// ════════════════════════════════════════════════════════════════════

// EscrowRecord 托管记录
type EscrowRecord struct {
	ID            string    `json:"id"`
	ClientAddr    string    `json:"client_addr"`
	NodeAddr      string    `json:"node_addr"`
	TaskID        string    `json:"task_id"`
	Amount        float64   `json:"amount"`
	Status        string    `json:"status"`
	CreatedAt     time.Time `json:"created_at"`
	ReleasedAt    time.Time `json:"released_at,omitempty"`
	RefundAmount  float64   `json:"refund_amount,omitempty"`
	ArbiterAddr   string    `json:"arbiter_addr,omitempty"`
}

// PaymentEscrow 资金托管合约
type PaymentEscrow struct {
	mu        sync.RWMutex
	escrows   map[string]*EscrowRecord
	tokenMgr  *TokenManager
}

// NewPaymentEscrow 创建资金托管合约
func NewPaymentEscrow(tm *TokenManager) *PaymentEscrow {
	return &PaymentEscrow{
		escrows:  make(map[string]*EscrowRecord),
		tokenMgr: tm,
	}
}

// CreateEscrow 创建托管（从客户账户锁定资金）
func (pe *PaymentEscrow) CreateEscrow(clientAddr, nodeAddr, taskID string, amount float64) (*EscrowRecord, error) {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	// 检查客户余额
	balance, exists := pe.tokenMgr.GetBalance(clientAddr)
	if !exists || balance < amount {
		return nil, fmt.Errorf("insufficient balance: %.2f CHB < %.2f CHB", balance, amount)
	}

	id := fmt.Sprintf("escrow-%d", time.Now().UnixNano())

	// 冻结资金 (通过转账到合约地址)
	_, err := pe.tokenMgr.Transfer(clientAddr, fmt.Sprintf("escrow:%s", id), amount)
	if err != nil {
		return nil, fmt.Errorf("lock funds: %w", err)
	}

	record := &EscrowRecord{
		ID:         id,
		ClientAddr: clientAddr,
		NodeAddr:   nodeAddr,
		TaskID:     taskID,
		Amount:     amount,
		Status:     EscrowStatusLocked,
		CreatedAt:  time.Now(),
	}
	pe.escrows[id] = record
	return record, nil
}

// ReleaseEscrow 释放资金给节点
func (pe *PaymentEscrow) ReleaseEscrow(escrowID string, actualCost float64) (*EscrowRecord, error) {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	record, exists := pe.escrows[escrowID]
	if !exists {
		return nil, fmt.Errorf("escrow %s not found", escrowID)
	}
	if record.Status != EscrowStatusLocked {
		return nil, fmt.Errorf("escrow %s is not locked (status: %s)", escrowID, record.Status)
	}

	// 实际花费给节点
	pe.tokenMgr.Transfer(fmt.Sprintf("escrow:%s", record.ID), record.NodeAddr, actualCost)

	// 退还剩余
	refund := record.Amount - actualCost
	if refund > 0.001 {
		pe.tokenMgr.Transfer(fmt.Sprintf("escrow:%s", record.ID), record.ClientAddr, refund)
	}

	record.Status = EscrowStatusReleased
	record.ReleasedAt = time.Now()
	record.RefundAmount = refund

	return record, nil
}

// RefundEscrow 全额退款
func (pe *PaymentEscrow) RefundEscrow(escrowID string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	record, exists := pe.escrows[escrowID]
	if !exists {
		return fmt.Errorf("escrow %s not found", escrowID)
	}

	// 全额退还客户
	pe.tokenMgr.Transfer(fmt.Sprintf("escrow:%s", record.ID), record.ClientAddr, record.Amount)
	record.Status = EscrowStatusRefunded
	record.RefundAmount = record.Amount
	return nil
}

// GetEscrow 查询托管
func (pe *PaymentEscrow) GetEscrow(escrowID string) (*EscrowRecord, bool) {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	r, ok := pe.escrows[escrowID]
	return r, ok
}

// EscrowStats 返回托管统计
func (pe *PaymentEscrow) EscrowStats() map[string]int {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	stats := map[string]int{"total": len(pe.escrows)}
	for _, e := range pe.escrows {
		stats[e.Status]++
	}
	return stats
}

// ════════════════════════════════════════════════════════════════════
// 3. NodeStaking — 节点质押和奖励
// ════════════════════════════════════════════════════════════════════

// StakeRecord 质押记录
type StakeRecord struct {
	NodeAddr     string    `json:"node_addr"`
	Amount       float64   `json:"amount"`
	Status       string    `json:"status"`
	StakedAt     time.Time `json:"staked_at"`
	ReleaseAt    time.Time `json:"release_at"`
	TotalReward  float64   `json:"total_reward"`
	TotalSlash   float64   `json:"total_slash"`
}

// NodeStaking 节点质押合约
type NodeStaking struct {
	mu        sync.RWMutex
	stakes    map[string]*StakeRecord
	tokenMgr  *TokenManager
	rewardPerBlock float64
	minStake       float64
	lockPeriod     time.Duration
	slashPercent   float64

	blockCounter  int64 // 用于奖励分配
}

// NewNodeStaking 创建节点质押合约
func NewNodeStaking(tm *TokenManager) *NodeStaking {
	return &NodeStaking{
		stakes:         make(map[string]*StakeRecord),
		tokenMgr:       tm,
		rewardPerBlock: DefaultRewardPerBlock,
		minStake:       DefaultStakeMinAmount,
		lockPeriod:     DefaultStakeLockPeriod,
		slashPercent:   DefaultSlashPercent,
	}
}

// Stake 节点质押
func (ns *NodeStaking) Stake(nodeAddr string, amount float64) (*StakeRecord, error) {
	ns.mu.Lock()
	defer ns.mu.Unlock()

	if amount < ns.minStake {
		return nil, fmt.Errorf("stake %.2f CHB below minimum %.2f CHB", amount, ns.minStake)
	}

	// 检查余额
	balance, exists := ns.tokenMgr.GetBalance(nodeAddr)
	if !exists || balance < amount {
		return nil, fmt.Errorf("insufficient balance: %.2f CHB", balance)
	}

	// 转账到质押合约
	_, err := ns.tokenMgr.Transfer(nodeAddr, fmt.Sprintf("stake:%s", nodeAddr), amount)
	if err != nil {
		return nil, fmt.Errorf("transfer stake: %w", err)
	}

	record := &StakeRecord{
		NodeAddr:    nodeAddr,
		Amount:      amount,
		Status:      StakeStatusActive,
		StakedAt:    time.Now(),
		ReleaseAt:   time.Now().Add(ns.lockPeriod),
	}
	ns.stakes[nodeAddr] = record
	return record, nil
}

// Unstake 解除质押
func (ns *NodeStaking) Unstake(nodeAddr string) (*StakeRecord, error) {
	ns.mu.Lock()
	defer ns.mu.Unlock()

	record, exists := ns.stakes[nodeAddr]
	if !exists {
		return nil, fmt.Errorf("no stake found for %s", nodeAddr)
	}
	if record.Status != StakeStatusActive {
		return nil, fmt.Errorf("stake for %s is not active (status: %s)", nodeAddr, record.Status)
	}
	if time.Now().Before(record.ReleaseAt) {
		return nil, fmt.Errorf("stake for %s is still locked until %s", nodeAddr, record.ReleaseAt.Format(time.RFC3339))
	}

	// 退还质押 + 奖励
	totalReturn := record.Amount + record.TotalReward - record.TotalSlash
	ns.tokenMgr.Transfer(fmt.Sprintf("stake:%s", nodeAddr), nodeAddr, totalReturn)

	record.Status = StakeStatusReleased
	return record, nil
}

// DistributeRewards 分配区块奖励
func (ns *NodeStaking) DistributeRewards() int {
	ns.mu.Lock()
	defer ns.mu.Unlock()

	ns.blockCounter++
	count := 0
	for addr, record := range ns.stakes {
		if record.Status == StakeStatusActive {
			reward := ns.rewardPerBlock * (record.Amount / ns.minStake)
			record.TotalReward += reward
			count++
		}
		_ = addr
	}
	return count
}

// Slash 惩罚节点
func (ns *NodeStaking) Slash(nodeAddr, reason string, customPercent float64) error {
	ns.mu.Lock()
	defer ns.mu.Unlock()

	record, exists := ns.stakes[nodeAddr]
	if !exists {
		return fmt.Errorf("no stake found for %s", nodeAddr)
	}
	if record.Status != StakeStatusActive {
		return fmt.Errorf("stake for %s is not active", nodeAddr)
	}

	pct := customPercent
	if pct <= 0 {
		pct = ns.slashPercent
	}

	slashAmount := record.Amount * pct
	record.TotalSlash += slashAmount
	record.Status = StakeStatusSlashing

	// 没收部分质押 (转移到系统账户)
	ns.tokenMgr.Transfer(fmt.Sprintf("stake:%s", nodeAddr), "system:slashed", slashAmount)
	record.Amount -= slashAmount

	if record.Amount < ns.minStake {
		record.Status = StakeStatusSlashing
		_ = reason
	}

	return nil
}

// GetStake 查询质押
func (ns *NodeStaking) GetStake(nodeAddr string) (*StakeRecord, bool) {
	ns.mu.RLock()
	defer ns.mu.RUnlock()
	r, ok := ns.stakes[nodeAddr]
	return r, ok
}

// StakingStats 返回质押统计
func (ns *NodeStaking) StakingStats() map[string]interface{} {
	ns.mu.RLock()
	defer ns.mu.RUnlock()
	totalStaked := 0.0
	totalRewards := 0.0
	activeCount := 0
	for _, r := range ns.stakes {
		if r.Status == StakeStatusActive {
			totalStaked += r.Amount
			totalRewards += r.TotalReward
			activeCount++
		}
	}
	return map[string]interface{}{
		"total_stakers":    len(ns.stakes),
		"active_stakers":   activeCount,
		"total_staked":     totalStaked,
		"total_rewards":    totalRewards,
		"block_counter":    ns.blockCounter,
		"reward_per_block": ns.rewardPerBlock,
		"min_stake":        ns.minStake,
		"slash_percent":    ns.slashPercent,
	}
}

// ════════════════════════════════════════════════════════════════════
// 4. DisputeResolution — 争议仲裁
// ════════════════════════════════════════════════════════════════════

// DisputeRecord 争议记录
type DisputeRecord struct {
	ID           string    `json:"id"`
	TaskID       string    `json:"task_id"`
	Requester    string    `json:"requester"`
	Respondent   string    `json:"respondent"`
	Status       string    `json:"status"`
	Reason       string    `json:"reason"`
	Evidence     string    `json:"evidence,omitempty"`
	Votes        []Vote    `json:"votes,omitempty"`
	Result       string    `json:"result,omitempty"`      // favor_requester, favor_respondent, split
	Compensation float64   `json:"compensation,omitempty"` // 赔偿金额
	CreatedAt    time.Time `json:"created_at"`
	ResolvedAt   time.Time `json:"resolved_at,omitempty"`
	VoteDeadline time.Time `json:"vote_deadline"`
	Appeal       bool      `json:"appeal"`
}

// Vote 仲裁投票
type Vote struct {
	Arbiter string `json:"arbiter"`
	Side    string `json:"side"` // favor_requester, favor_respondent
	Reason  string `json:"reason"`
	Weight  int    `json:"weight"` // 投票权重 (基于质押量)
}

// DisputeResolution 争议仲裁合约
type DisputeResolution struct {
	mu          sync.RWMutex
	disputes    map[string]*DisputeRecord
	arbiters    map[string]float64 // arbiter addr -> reputation score
	tokenMgr    *TokenManager
	votePeriod  time.Duration
}

// NewDisputeResolution 创建争议仲裁合约
func NewDisputeResolution(tm *TokenManager) *DisputeResolution {
	return &DisputeResolution{
		disputes:   make(map[string]*DisputeRecord),
		arbiters:   make(map[string]float64),
		tokenMgr:   tm,
		votePeriod: DefaultDisputeVotePeriod,
	}
}

// RegisterArbiter 注册仲裁人
func (dr *DisputeResolution) RegisterArbiter(addr string, initialRep float64) {
	dr.mu.Lock()
	defer dr.mu.Unlock()
	dr.arbiters[addr] = initialRep
}

// OpenDispute 发起争议
func (dr *DisputeResolution) OpenDispute(taskID, requester, respondent, reason string) (*DisputeRecord, error) {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	id := fmt.Sprintf("dispute-%d", time.Now().UnixNano())
	record := &DisputeRecord{
		ID:           id,
		TaskID:       taskID,
		Requester:    requester,
		Respondent:   respondent,
		Status:       DisputeStatusOpen,
		Reason:       reason,
		CreatedAt:    time.Now(),
		VoteDeadline: time.Now().Add(dr.votePeriod),
		Votes:        make([]Vote, 0),
	}
	dr.disputes[id] = record
	return record, nil
}

// SubmitEvidence 提交证据
func (dr *DisputeResolution) SubmitEvidence(disputeID, evidence string) error {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	record, exists := dr.disputes[disputeID]
	if !exists {
		return fmt.Errorf("dispute %s not found", disputeID)
	}
	if record.Status != DisputeStatusOpen {
		return fmt.Errorf("dispute %s cannot accept evidence (status: %s)", disputeID, record.Status)
	}

	record.Evidence = evidence
	record.Status = DisputeStatusEvidence
	return nil
}

// CastVote 投仲裁票
func (dr *DisputeResolution) CastVote(disputeID, arbiter, side string) error {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	record, exists := dr.disputes[disputeID]
	if !exists {
		return fmt.Errorf("dispute %s not found", disputeID)
	}

	// 检查仲裁人资格
	rep, isArbiter := dr.arbiters[arbiter]
	if !isArbiter {
		return fmt.Errorf("%s is not a registered arbiter", arbiter)
	}

	// 检查是否已投票
	for _, v := range record.Votes {
		if v.Arbiter == arbiter {
			return fmt.Errorf("arbiter %s already voted", arbiter)
		}
	}

	weight := int(rep * 10)
	if weight < 1 {
		weight = 1
	}

	vote := Vote{
		Arbiter: arbiter,
		Side:    side,
		Weight:  weight,
	}
	record.Votes = append(record.Votes, vote)
	record.Status = DisputeStatusVoting

	return nil
}

// ResolveDispute 解决争议 (根据投票结果)
func (dr *DisputeResolution) ResolveDispute(disputeID string) (*DisputeRecord, error) {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	record, exists := dr.disputes[disputeID]
	if !exists {
		return nil, fmt.Errorf("dispute %s not found", disputeID)
	}

	if len(record.Votes) == 0 {
		return nil, fmt.Errorf("dispute %s has no votes", disputeID)
	}

	// 计票
	favorRequester := 0
	favorRespondent := 0
	for _, v := range record.Votes {
		switch v.Side {
		case "favor_requester":
			favorRequester += v.Weight
		case "favor_respondent":
			favorRespondent += v.Weight
		}
	}

	switch {
	case favorRequester > favorRespondent:
		record.Result = "favor_requester"
	case favorRespondent > favorRequester:
		record.Result = "favor_respondent"
	default:
		record.Result = "split"
	}

	record.Status = DisputeStatusResolved
	record.ResolvedAt = time.Now()
	return record, nil
}

// AppealDispute 上诉
func (dr *DisputeResolution) AppealDispute(disputeID string) error {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	record, exists := dr.disputes[disputeID]
	if !exists {
		return fmt.Errorf("dispute %s not found", disputeID)
	}

	if record.Status != DisputeStatusResolved {
		return fmt.Errorf("dispute %s is not resolved (status: %s)", disputeID, record.Status)
	}

	record.Appeal = true
	record.Status = DisputeStatusAppealed
	return nil
}

// GetDispute 查询争议
func (dr *DisputeResolution) GetDispute(disputeID string) (*DisputeRecord, bool) {
	dr.mu.RLock()
	defer dr.mu.RUnlock()
	r, ok := dr.disputes[disputeID]
	return r, ok
}

// DisputeStats 返回争议统计
func (dr *DisputeResolution) DisputeStats() map[string]int {
	dr.mu.RLock()
	defer dr.mu.RUnlock()
	stats := map[string]int{"total": len(dr.disputes), "arbiters": len(dr.arbiters)}
	for _, d := range dr.disputes {
		stats[d.Status]++
	}
	return stats
}

// ════════════════════════════════════════════════════════════════════
// 辅助: 任务需求结构 (供 TaskRegistry 使用)
// ════════════════════════════════════════════════════════════════════

// TaskRequirement 任务需求参数
type TaskRequirement struct {
	ResourceType   string `json:"resource_type"`
	GPUCount       int    `json:"gpu_count"`
	CPUCount       int    `json:"cpu_count"`
	MemoryGB       int    `json:"memory_gb"`
	MaxDurationSec int    `json:"max_duration_sec"`
	Priority       int    `json:"priority"`
}
