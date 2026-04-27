// Package blockchain — Sprint 3 合约层测试
package blockchain

import (
	"fmt"
	"testing"
	"time"
)

// ─── 1. TaskRegistry 测试 ──────────────────────────────────────────

func TestNewTaskRegistry(t *testing.T) {
	tr := NewTaskRegistry()
	if tr == nil {
		t.Fatal("TaskRegistry should not be nil")
	}
	stats := tr.TaskStats()
	if stats["total"] != 0 {
		t.Errorf("Expected 0 tasks, got %d", stats["total"])
	}
}

func TestRegisterTask(t *testing.T) {
	tr := NewTaskRegistry()

	req := TaskRequirement{
		ResourceType:   "gpu",
		GPUCount:       2,
		CPUCount:       4,
		MemoryGB:       16,
		MaxDurationSec: 3600,
		Priority:       1,
	}

	task, err := tr.RegisterTask("task-001", "client-A", req, 50.0, "escrow-001")
	if err != nil {
		t.Fatalf("RegisterTask should succeed: %v", err)
	}
	if task.Status != TaskStatusPending {
		t.Errorf("Expected pending status, got %s", task.Status)
	}
	if task.Budget != 50.0 {
		t.Errorf("Expected budget 50, got %.2f", task.Budget)
	}
}

func TestRegisterTask_Duplicate(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "cpu"}
	tr.RegisterTask("dup-001", "client-A", req, 10.0, "")
	_, err := tr.RegisterTask("dup-001", "client-B", req, 20.0, "")
	if err == nil {
		t.Error("RegisterTask should reject duplicate ID")
	}
}

func TestAssignTask(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "gpu", GPUCount: 1}
	tr.RegisterTask("assign-001", "client-A", req, 10.0, "")

	err := tr.AssignTask("assign-001", "node-001")
	if err != nil {
		t.Fatalf("AssignTask should succeed: %v", err)
	}

	task, _ := tr.GetTask("assign-001")
	if task.Status != TaskStatusRunning {
		t.Errorf("Expected running status, got %s", task.Status)
	}
	if task.NodeAddr != "node-001" {
		t.Errorf("Expected node node-001, got %s", task.NodeAddr)
	}
}

func TestAssignTask_NotPending(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "cpu"}
	tr.RegisterTask("fail-assign", "client-A", req, 10.0, "")
	tr.AssignTask("fail-assign", "node-001")

	err := tr.AssignTask("fail-assign", "node-002")
	if err == nil {
		t.Error("AssignTask should fail for non-pending task")
	}
}

func TestCompleteTask(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "gpu", GPUCount: 1}
	tr.RegisterTask("complete-001", "client-A", req, 20.0, "")
	tr.AssignTask("complete-001", "node-001")

	err := tr.CompleteTask("complete-001", 15.0)
	if err != nil {
		t.Fatalf("CompleteTask should succeed: %v", err)
	}

	task, _ := tr.GetTask("complete-001")
	if task.Status != TaskStatusCompleted {
		t.Errorf("Expected completed status, got %s", task.Status)
	}
	if task.ActualCost != 15.0 {
		t.Errorf("Expected cost 15.0, got %.2f", task.ActualCost)
	}
}

func TestFailTask(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "cpu", CPUCount: 2}
	tr.RegisterTask("fail-001", "client-A", req, 5.0, "")

	err := tr.FailTask("fail-001", "OOM error")
	if err != nil {
		t.Fatalf("FailTask should succeed: %v", err)
	}

	task, _ := tr.GetTask("fail-001")
	if task.Status != TaskStatusFailed {
		t.Errorf("Expected failed status, got %s", task.Status)
	}
}

func TestListTasksByClient(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "cpu"}
	tr.RegisterTask("t1", "client-X", req, 5.0, "")
	tr.RegisterTask("t2", "client-X", req, 10.0, "")
	tr.RegisterTask("t3", "client-Y", req, 15.0, "")

	tasks := tr.ListTasksByClient("client-X")
	if len(tasks) != 2 {
		t.Errorf("Expected 2 tasks for client-X, got %d", len(tasks))
	}

	tasks = tr.ListTasksByClient("nonexistent")
	if len(tasks) != 0 {
		t.Errorf("Expected 0 tasks for nonexistent client, got %d", len(tasks))
	}
}

func TestTaskStats(t *testing.T) {
	tr := NewTaskRegistry()
	req := TaskRequirement{ResourceType: "cpu"}

	tr.RegisterTask("s1", "A", req, 1, "")
	tr.RegisterTask("s2", "B", req, 2, "")
	tr.RegisterTask("s3", "C", req, 3, "")
	tr.RegisterTask("s4", "D", req, 4, "")

	tr.AssignTask("s2", "n1")
	tr.AssignTask("s3", "n2")
	tr.CompleteTask("s3", 1.5)
	tr.FailTask("s4", "error")

	stats := tr.TaskStats()
	if stats["pending"] != 1 {
		t.Errorf("Expected 1 pending, got %d", stats["pending"])
	}
	if stats["running"] != 1 {
		t.Errorf("Expected 1 running, got %d", stats["running"])
	}
	if stats["completed"] != 1 {
		t.Errorf("Expected 1 completed, got %d", stats["completed"])
	}
	if stats["failed"] != 1 {
		t.Errorf("Expected 1 failed, got %d", stats["failed"])
	}
}

// ─── 2. PaymentEscrow 测试 ─────────────────────────────────────────

func TestNewPaymentEscrow(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)
	if pe == nil {
		t.Fatal("PaymentEscrow should not be nil")
	}
}

func TestCreateEscrow_Success(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)

	tm.Deposit("client-E1", 100.0, 1.0, "tx-fund")

	escrow, err := pe.CreateEscrow("client-E1", "node-E1", "task-E1", 50.0)
	if err != nil {
		t.Fatalf("CreateEscrow should succeed: %v", err)
	}
	if escrow.Status != EscrowStatusLocked {
		t.Errorf("Expected locked status, got %s", escrow.Status)
	}
	if escrow.Amount != 50.0 {
		t.Errorf("Expected amount 50, got %.2f", escrow.Amount)
	}
}

func TestCreateEscrow_InsufficientBalance(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)

	tm.Deposit("client-poor", 10.0, 0.1, "tx-fund")

	_, err := pe.CreateEscrow("client-poor", "node", "task", 50.0)
	if err == nil {
		t.Error("CreateEscrow should fail with insufficient balance")
	}
}

func TestReleaseEscrow_Full(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)

	tm.Deposit("client-R1", 100.0, 1.0, "tx")

	escrow, _ := pe.CreateEscrow("client-R1", "node-R1", "task-R1", 50.0)

	released, err := pe.ReleaseEscrow(escrow.ID, 50.0)
	if err != nil {
		t.Fatalf("ReleaseEscrow should succeed: %v", err)
	}
	if released.Status != EscrowStatusReleased {
		t.Errorf("Expected released status, got %s", released.Status)
	}
}

func TestReleaseEscrow_PartialRefund(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)

	tm.Deposit("client-R2", 100.0, 1.0, "tx")
	escrow, _ := pe.CreateEscrow("client-R2", "node-R2", "task-R2", 50.0)

	released, err := pe.ReleaseEscrow(escrow.ID, 30.0)
	if err != nil {
		t.Fatalf("ReleaseEscrow should succeed: %v", err)
	}

	// 应该退还 20 CHB
	if released.RefundAmount < 19.9 || released.RefundAmount > 20.1 {
		t.Errorf("Expected refund ~20, got %.2f", released.RefundAmount)
	}
}

func TestRefundEscrow(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)

	tm.Deposit("client-REF", 100.0, 1.0, "tx")
	escrow, _ := pe.CreateEscrow("client-REF", "node-REF", "task-REF", 50.0)

	err := pe.RefundEscrow(escrow.ID)
	if err != nil {
		t.Fatalf("RefundEscrow should succeed: %v", err)
	}

	r, _ := pe.GetEscrow(escrow.ID)
	if r.Status != EscrowStatusRefunded {
		t.Errorf("Expected refunded status, got %s", r.Status)
	}
}

func TestEscrowStats(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)

	// 给足够的余额
	tm.Deposit("client-S1", 100, 1, "tx")
	tm.Deposit("client-S2", 100, 1, "tx")
	tm.Deposit("client-S3", 100, 1, "tx")
	tm.Deposit("client-S4", 100, 1, "tx")

	pe.CreateEscrow("client-S1", "n1", "t1", 10) // locked
	e2, _ := pe.CreateEscrow("client-S2", "n2", "t2", 10)
	pe.ReleaseEscrow(e2.ID, 5)
	e3, _ := pe.CreateEscrow("client-S3", "n3", "t3", 10)
	pe.RefundEscrow(e3.ID)

	stats := pe.EscrowStats()
	if stats["total"] != 3 {
		t.Errorf("Expected 3 total, got %d", stats["total"])
	}
}

// ─── 3. NodeStaking 测试 ───────────────────────────────────────────

func TestNewNodeStaking(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)
	if ns == nil {
		t.Fatal("NodeStaking should not be nil")
	}
}

func TestStake_Success(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	tm.Deposit("staker-001", 500.0, 5.0, "tx")

	record, err := ns.Stake("staker-001", 200.0)
	if err != nil {
		t.Fatalf("Stake should succeed: %v", err)
	}
	if record.Amount != 200.0 {
		t.Errorf("Expected staked amount 200, got %.2f", record.Amount)
	}
	if record.Status != StakeStatusActive {
		t.Errorf("Expected active status, got %s", record.Status)
	}
}

func TestStake_BelowMinimum(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	tm.Deposit("staker-low", 50.0, 0.5, "tx")

	_, err := ns.Stake("staker-low", 10.0)
	if err == nil {
		t.Error("Stake should reject amount below minimum")
	}
}

func TestUnstake_BeforeRelease(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	tm.Deposit("staker-lock", 500.0, 5.0, "tx")
	ns.Stake("staker-lock", 200.0)

	// 锁定期未到，应该失败
	_, err := ns.Unstake("staker-lock")
	if err == nil {
		t.Error("Unstake should fail before lock period expires")
	}
}

func TestDistributeRewards(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	tm.Deposit("staker-r1", 500, 5, "tx")
	tm.Deposit("staker-r2", 500, 5, "tx")

	ns.Stake("staker-r1", 200)
	ns.Stake("staker-r2", 100)

	// 分配3个区块的奖励
	for i := 0; i < 3; i++ {
		ns.DistributeRewards()
	}

	r1, _ := ns.GetStake("staker-r1")
	r2, _ := ns.GetStake("staker-r2")

	// r1 质押了 2 倍最小质押量，所以奖励是 r2 的 2 倍
	if r1.TotalReward <= 0 {
		t.Error("staker-r1 should have earned rewards")
	}
	if r2.TotalReward <= 0 {
		t.Error("staker-r2 should have earned rewards")
	}
}

func TestSlash(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	tm.Deposit("staker-slash", 500, 5, "tx")
	ns.Stake("staker-slash", 200)

	err := ns.Slash("staker-slash", "downtime violation", 0)
	if err != nil {
		t.Fatalf("Slash should succeed: %v", err)
	}

	record, _ := ns.GetStake("staker-slash")
	if record.TotalSlash <= 0 {
		t.Error("Slash amount should be > 0")
	}
}

func TestStakingStats(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	stats := ns.StakingStats()
	if stats["total_stakers"] != 0 {
		t.Errorf("Expected 0 stakers, got %v", stats["total_stakers"])
	}

	tm.Deposit("stat-s1", 500, 5, "tx")
	ns.Stake("stat-s1", 200)

	stats = ns.StakingStats()
	if stats["active_stakers"] != 1 {
		t.Errorf("Expected 1 active staker, got %v", stats["active_stakers"])
	}
}

// ─── 4. DisputeResolution 测试 ─────────────────────────────────────

func TestNewDisputeResolution(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)
	if dr == nil {
		t.Fatal("DisputeResolution should not be nil")
	}
}

func TestOpenDispute(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)

	dispute, err := dr.OpenDispute("task-D1", "client-A", "node-A", "low quality result")
	if err != nil {
		t.Fatalf("OpenDispute should succeed: %v", err)
	}
	if dispute.Status != DisputeStatusOpen {
		t.Errorf("Expected open status, got %s", dispute.Status)
	}
}

func TestOpenDisputeAndSubmitEvidence(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)

	dispute, _ := dr.OpenDispute("task-D2", "client-B", "node-B", "incorrect billing")
	err := dr.SubmitEvidence(dispute.ID, "GPU logs show 50% idle time but charged for 100%")
	if err != nil {
		t.Fatalf("SubmitEvidence should succeed: %v", err)
	}

	d, _ := dr.GetDispute(dispute.ID)
	if d.Status != DisputeStatusEvidence {
		t.Errorf("Expected evidence status, got %s", d.Status)
	}
}

func TestCastVoteAndResolve(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)

	// 注册仲裁人
	dr.RegisterArbiter("arb-001", 8.0)
	dr.RegisterArbiter("arb-002", 6.0)

	dispute, _ := dr.OpenDispute("task-D3", "client-C", "node-C", "disputed quality")

	dr.CastVote(dispute.ID, "arb-001", "favor_requester")
	dr.CastVote(dispute.ID, "arb-002", "favor_respondent")

	resolved, err := dr.ResolveDispute(dispute.ID)
	if err != nil {
		t.Fatalf("ResolveDispute should succeed: %v", err)
	}

	// arb-001 weight=80, arb-002 weight=60, 所以 favor_requester 胜出
	if resolved.Result != "favor_requester" {
		t.Errorf("Expected favor_requester, got %s", resolved.Result)
	}
	if resolved.Status != DisputeStatusResolved {
		t.Errorf("Expected resolved status, got %s", resolved.Status)
	}
}

func TestCastVote_DoubleVote(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)

	dr.RegisterArbiter("arb-double", 5.0)
	dispute, _ := dr.OpenDispute("task-D4", "X", "Y", "test")

	dr.CastVote(dispute.ID, "arb-double", "favor_requester")
	err := dr.CastVote(dispute.ID, "arb-double", "favor_respondent")
	if err == nil {
		t.Error("Double voting should be rejected")
	}
}

func TestDisputeAppeal(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)

	dr.RegisterArbiter("arb-app", 5.0)
	dispute, _ := dr.OpenDispute("task-App", "X", "Y", "appeal test")
	dr.CastVote(dispute.ID, "arb-app", "favor_requester")
	dr.ResolveDispute(dispute.ID)

	err := dr.AppealDispute(dispute.ID)
	if err != nil {
		t.Fatalf("AppealDispute should succeed: %v", err)
	}

	d, _ := dr.GetDispute(dispute.ID)
	if d.Status != DisputeStatusAppealed {
		t.Errorf("Expected appealed status, got %s", d.Status)
	}
}

func TestDisputeStats(t *testing.T) {
	tm := NewTokenManager()
	dr := NewDisputeResolution(tm)

	dr.RegisterArbiter("arb-stat", 5.0)
	dr.OpenDispute("d1", "A", "B", "r1")

	stats := dr.DisputeStats()
	if stats["total"] != 1 {
		t.Errorf("Expected 1 total dispute, got %d", stats["total"])
	}
	if stats["arbiters"] != 1 {
		t.Errorf("Expected 1 arbiter, got %d", stats["arbiters"])
	}
}

// ─── 5. BillingEngine 测试 ─────────────────────────────────────────

func TestNewBillingEngine(t *testing.T) {
	be := NewBillingEngine()
	if be == nil {
		t.Fatal("BillingEngine should not be nil")
	}
}

func TestRecordUsage(t *testing.T) {
	be := NewBillingEngine()
	sample := UsageSample{
		GPUUtilPct:   75.0,
		GPUMemUsedMB: 4096,
		CPUPct:       30.0,
		MemUsedMB:    2048,
	}
	be.RecordUsage("task-util", sample) // no panic
}

func TestCalculateAndBill_TimerMode(t *testing.T) {
	be := NewBillingEngine()

	// 模拟 1 小时 GPU 任务
	now := time.Now()
	for i := 0; i < 60; i++ {
		be.RecordUsage("task-bill-time", UsageSample{
			Timestamp:   now.Add(time.Duration(i) * time.Minute),
			GPUUtilPct:  50.0,
			GPUMemUsedMB: 4096,
			CPUPct:      25.0,
			MemUsedMB:   2048,
		})
	}

	record, err := be.CalculateAndBill("task-bill-time", "node-B1", 1, 4, 8, BillingModeTime)
	if err != nil {
		t.Fatalf("CalculateAndBill should succeed: %v", err)
	}
	if record.CostTotalUSD <= 0 {
		t.Errorf("Expected positive cost, got %.4f", record.CostTotalUSD)
	}
	if record.DurationSecs < 3000 { // ~3600s
		t.Errorf("Expected duration ~3600s, got %.0f", record.DurationSecs)
	}
}

func TestCalculateAndBill_GPUUtilMode(t *testing.T) {
	be := NewBillingEngine()

	now := time.Now()
	for i := 0; i < 30; i++ {
		be.RecordUsage("task-bill-gpu", UsageSample{
			Timestamp:    now.Add(time.Duration(i) * 2 * time.Minute),
			GPUUtilPct:  80.0, // 高利用率
			GPUMemUsedMB: 8192,
		})
	}

	record, err := be.CalculateAndBill("task-bill-gpu", "node-B2", 2, 8, 32, BillingModeGPUUtil)
	if err != nil {
		t.Fatalf("CalculateAndBill should succeed: %v", err)
	}
	// 高利用率应该有溢价
	if record.CostGPU <= 0 {
		t.Errorf("Expected positive GPU cost, got %.4f", record.CostGPU)
	}
}

func TestCalculateAndBill_TokenMode(t *testing.T) {
	be := NewBillingEngine()

	now := time.Now()
	for i := 0; i < 10; i++ {
		be.RecordUsage("task-bill-token", UsageSample{
			Timestamp: now.Add(time.Duration(i) * time.Minute),
		})
	}

	_, err := be.CalculateAndBill("task-bill-token", "node-B3", 0, 4, 8, BillingModeToken)
	if err != nil {
		t.Fatalf("CalculateAndBill should succeed: %v", err)
	}
}

func TestCalculateAndBill_InsufficientSamples(t *testing.T) {
	be := NewBillingEngine()

	be.RecordUsage("task-1sample", UsageSample{})

	_, err := be.CalculateAndBill("task-1sample", "node", 1, 1, 1, BillingModeTime)
	if err == nil {
		t.Error("CalculateAndBill should fail with <2 samples")
	}
}

func TestListBillingByNode(t *testing.T) {
	be := NewBillingEngine()
	now := time.Now()

	be.RecordUsage("n1-t1", UsageSample{Timestamp: now})
	be.RecordUsage("n1-t1", UsageSample{Timestamp: now.Add(time.Minute)})
	be.CalculateAndBill("n1-t1", "node-N1", 1, 1, 1, BillingModeTime)

	be.RecordUsage("n1-t2", UsageSample{Timestamp: now})
	be.RecordUsage("n1-t2", UsageSample{Timestamp: now.Add(time.Minute)})
	be.CalculateAndBill("n1-t2", "node-N1", 1, 1, 1, BillingModeTime)

	bills := be.ListBillingByNode("node-N1")
	if len(bills) != 2 {
		t.Errorf("Expected 2 bills for node-N1, got %d", len(bills))
	}
}

func TestBillSummary(t *testing.T) {
	be := NewBillingEngine()
	now := time.Now()

	for i := 0; i < 3; i++ {
		taskID := fmt.Sprintf("summary-%d", i)
		be.RecordUsage(taskID, UsageSample{Timestamp: now})
		be.RecordUsage(taskID, UsageSample{Timestamp: now.Add(time.Minute)})
		be.CalculateAndBill(taskID, "node-S1", 1, 1, 1, BillingModeTime)
	}

	summary := be.ComputeBillSummary()
	if summary["total_records"] != 3 {
		t.Errorf("Expected 3 total records, got %v", summary["total_records"])
	}
}
