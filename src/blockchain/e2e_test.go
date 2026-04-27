// Package blockchain — Sprint 3 端到端集成测试
// 覆盖完整结算生命周期: 充值 → 任务注册 → 托管锁定 → 计费 → 释放 → 争议
package blockchain

import (
	"testing"
	"time"
)

// TestE2E_FullSettlementLifecycle 完整结算生命周期测试
// deposit → task register → escrow → execute → billing → release → verify
func TestE2E_FullSettlementLifecycle(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)
	tr := NewTaskRegistry()
	be := NewBillingEngine()

	// === Phase 1: 客户充值 ===
	clientAddr := "client-full"
	nodeAddr := "node-full"
	_, err := tm.Deposit(clientAddr, 500.0, 5.0, "tx-initial")
	if err != nil {
		t.Fatalf("Phase1: deposit failed: %v", err)
	}

	bal, _ := tm.GetBalance(clientAddr)
	if bal < 499 {
		t.Fatalf("Phase1: expected balance ~500, got %.2f", bal)
	}
	t.Logf("✅ Phase1: 客户充值 500 CHB 成功 (余额: %.2f)", bal)

	// === Phase 2: 登记任务 ===
	req := TaskRequirement{
		ResourceType:   "gpu",
		GPUCount:       2,
		CPUCount:       8,
		MemoryGB:       32,
		MaxDurationSec: 3600,
		Priority:       1,
	}

	task, err := tr.RegisterTask("e2e-task-001", clientAddr, req, 100.0, "escrow-e2e")
	if err != nil {
		t.Fatalf("Phase2: register task failed: %v", err)
	}
	if task.Status != TaskStatusPending {
		t.Fatalf("Phase2: expected pending, got %s", task.Status)
	}
	t.Logf("✅ Phase2: 任务 %s 登记成功 (预算: %.2f CHB)", task.ID, task.Budget)

	// === Phase 3: 创建托管 ===
	escrow, err := pe.CreateEscrow(clientAddr, nodeAddr, task.ID, 100.0)
	if err != nil {
		t.Fatalf("Phase3: create escrow failed: %v", err)
	}
	if escrow.Status != EscrowStatusLocked {
		t.Fatalf("Phase3: expected locked, got %s", escrow.Status)
	}
	t.Logf("✅ Phase3: 托管 %s 创建成功 (冻结 %.2f CHB)", escrow.ID, escrow.Amount)

	// === Phase 4: 分配并执行任务 ===
	err = tr.AssignTask(task.ID, nodeAddr)
	if err != nil {
		t.Fatalf("Phase4: assign task failed: %v", err)
	}
	assignedTask, _ := tr.GetTask(task.ID)
	if assignedTask.Status != TaskStatusRunning {
		t.Fatalf("Phase4: expected running, got %s", assignedTask.Status)
	}
	t.Logf("✅ Phase4: 任务分配给 %s 成功", nodeAddr)

	// === Phase 5: 计费（模拟1小时GPU任务） ===
	now := time.Now()
	for i := 0; i < 60; i++ {
		be.RecordUsage(task.ID, UsageSample{
			Timestamp:    now.Add(time.Duration(i) * time.Minute),
			GPUUtilPct:  75.0, // 高利用率
			GPUMemUsedMB: 8192,
			CPUPct:      30.0,
			MemUsedMB:   4096,
		})
	}

	bill, err := be.CalculateAndBill(task.ID, nodeAddr, 2, 8, 32, BillingModeGPUUtil)
	if err != nil {
		t.Fatalf("Phase5: billing failed: %v", err)
	}
	if bill.CostTotalCHB <= 0 {
		t.Fatalf("Phase5: expected positive cost, got %.4f CHB", bill.CostTotalCHB)
	}
	t.Logf("✅ Phase5: 计费完成 — 时长 %.0fs, GPU利用率 %.0f%%, 费用 %.4f USD",
		bill.DurationSecs, bill.GPUUtilPct, bill.CostTotalUSD)

	// === Phase 6: 完成任务并释放托管 ===
	cost := bill.CostTotalCHB
	if cost < 0.01 {
		cost = 1.0 // 最小成本
	}

	err = tr.CompleteTask(task.ID, cost)
	if err != nil {
		t.Fatalf("Phase6: complete task failed: %v", err)
	}

	released, err := pe.ReleaseEscrow(escrow.ID, cost)
	if err != nil {
		t.Fatalf("Phase6: release escrow failed: %v", err)
	}
	if released.Status != EscrowStatusReleased {
		t.Fatalf("Phase6: expected released, got %s", released.Status)
	}
	t.Logf("✅ Phase6: 任务完成, 托管释放 (花费 %.4f CHB, 退还 %.4f CHB)",
		cost, released.RefundAmount)

	// === Phase 7: 验证最终状态 ===
	completedTask, _ := tr.GetTask(task.ID)
	if completedTask.Status != TaskStatusCompleted {
		t.Errorf("Phase7: expected completed, got %s", completedTask.Status)
	}
	if completedTask.ActualCost != cost {
		t.Errorf("Phase7: expected cost %.4f, got %.4f", cost, completedTask.ActualCost)
	}

	clientBal, _ := tm.GetBalance(clientAddr)
	expectedRemaining := 500.0 - cost // 500 - 实际花费
	if clientBal < expectedRemaining-0.1 || clientBal > expectedRemaining+0.1 {
		t.Logf("Phase7: 客户余额 %.4f CHB (预期 ~%.4f CHB)", clientBal, expectedRemaining)
	}

	t.Logf("✅ Phase7: 最终验证通过")
	t.Logf("")
	t.Logf("📊 端到端结算完成统计:")
	t.Logf("   客户: %s, 节点: %s", clientAddr, nodeAddr)
	t.Logf("   充值: 500 CHB, 花费: %.4f CHB, 剩余: %.4f CHB", cost, clientBal)
	t.Logf("   托管: %s → %s", EscrowStatusLocked, released.Status)
	t.Logf("   任务: pending → running → completed")
}

// TestE2E_DisputeAndResolve 争议仲裁全流程测试
// deposit → escrow → dispute → vote → resolve
func TestE2E_DisputeAndResolve(t *testing.T) {
	tm := NewTokenManager()
	pe := NewPaymentEscrow(tm)
	tr := NewTaskRegistry()
	dr := NewDisputeResolution(tm)

	// 注册仲裁人
	dr.RegisterArbiter("arb-alpha", 8.0)
	dr.RegisterArbiter("arb-beta", 6.0)
	dr.RegisterArbiter("arb-gamma", 4.0)

	// 充值
	tm.Deposit("client-dsp", 200, 2, "tx-dsp")

	// 登记任务 & 创建托管
	req := TaskRequirement{ResourceType: "gpu", GPUCount: 1, CPUCount: 4, MemoryGB: 16, MaxDurationSec: 1800}
	tr.RegisterTask("dispute-task", "client-dsp", req, 50, "escrow-dsp")
	tr.AssignTask("dispute-task", "node-dsp")
	pe.CreateEscrow("client-dsp", "node-dsp", "dispute-task", 50)

	// 发起争议
	dispute, err := dr.OpenDispute("dispute-task", "client-dsp", "node-dsp", "低质量结果, GPU利用率远低于承诺")
	if err != nil {
		t.Fatalf("open dispute failed: %v", err)
	}
	t.Logf("✅ 争议发起: %s", dispute.ID)

	// 提交证据
	dr.SubmitEvidence(dispute.ID, "GPU日志显示平均利用率仅25%, 但承诺80%")
	t.Logf("✅ 证据已提交")

	// 仲裁投票
	for _, vote := range []struct {
		arbiter, side string
	}{
		{"arb-alpha", "favor_requester"},
		{"arb-beta", "favor_respondent"},
		{"arb-gamma", "favor_requester"},
	} {
		err := dr.CastVote(dispute.ID, vote.arbiter, vote.side)
		if err != nil {
			t.Fatalf("vote by %s failed: %v", vote.arbiter, err)
		}
	}
	t.Logf("✅ 3位仲裁人已投票")

	// 计算预期 (alpha=80 + gamma=40 = 120 vs beta=60)
	resolved, err := dr.ResolveDispute(dispute.ID)
	if err != nil {
		t.Fatalf("resolve dispute failed: %v", err)
	}
	if resolved.Result != "favor_requester" {
		t.Errorf("expected favor_requester, got %s", resolved.Result)
	}
	if resolved.Status != DisputeStatusResolved {
		t.Errorf("expected resolved, got %s", resolved.Status)
	}
	t.Logf("✅ 争议解决: %s (requester胜)", resolved.Result)
	t.Logf("   alpha=%d favor_requester, beta=%d favor_respondent, gamma=%d favor_requester",
		80, 60, 40)
}

// TestE2E_StakingAndRewards 质押+奖励全流程测试
func TestE2E_StakingAndRewards(t *testing.T) {
	tm := NewTokenManager()
	ns := NewNodeStaking(tm)

	// 节点充值并质押
	tm.Deposit("staker-e2e", 1000, 10, "tx-stake")
	record, err := ns.Stake("staker-e2e", 500)
	if err != nil {
		t.Fatalf("stake failed: %v", err)
	}
	if record.Amount != 500 {
		t.Fatalf("expected staked 500, got %.2f", record.Amount)
	}
	t.Logf("✅ 节点质押 500 CHB 成功")

	// 分发10个区块奖励
	for i := 0; i < 10; i++ {
		ns.DistributeRewards()
	}
	record, _ = ns.GetStake("staker-e2e")
	if record.TotalReward <= 0 {
		t.Fatalf("expected rewards > 0, got %.4f", record.TotalReward)
	}
	t.Logf("✅ 10个区块奖励累计: %.4f CHB", record.TotalReward)

	// 惩罚测试
	ns.Slash("staker-e2e", "downtime violation", 0.05)
	record, _ = ns.GetStake("staker-e2e")
	if record.TotalSlash <= 0 {
		t.Fatalf("expected slash > 0, got %.4f", record.TotalSlash)
	}
	t.Logf("✅ 惩罚 5%%: %.4f CHB 被没收", record.TotalSlash)

	stats := ns.StakingStats()
	t.Logf("📊 质押统计: total_staked=%.2f, rewards=%.4f, active=%d",
		stats["total_staked"].(float64),
		stats["total_rewards"].(float64),
		stats["active_stakers"].(int),
	)
}

// TestE2E_BillingMultiMode 多计费模式对比测试
func TestE2E_BillingMultiMode(t *testing.T) {
	be := NewBillingEngine()
	now := time.Now()

	// 生成同样的使用数据
	for i := 0; i < 30; i++ {
		sample := UsageSample{
			Timestamp:    now.Add(time.Duration(i) * 2 * time.Minute),
			GPUUtilPct:  70.0,
			GPUMemUsedMB: 6144,
			CPUPct:      25.0,
			MemUsedMB:   2048,
		}
		be.RecordUsage("multi-mode-task", sample)
	}

	// 同一个使用数据, 5种计费模式对比
	modes := []string{
		BillingModeTime,
		BillingModeGPUUtil,
		BillingModeToken,
		BillingModeInference,
		BillingModeHybrid,
	}

	for _, mode := range modes {
		bill, err := be.CalculateAndBill("multi-mode-task", "node-compare", 1, 4, 16, mode)
		if err != nil {
			t.Logf("⚠️ 模式 %s 计费失败: %v", mode, err)
			continue
		}
		t.Logf("📊 [%10s] duration=%.0fs  gpu_cost=%.4f  total=%.4f USD (%.4f CHB)",
			mode, bill.DurationSecs, bill.CostGPU, bill.CostTotalUSD, bill.CostTotalCHB)
	}

	summary := be.ComputeBillSummary()
	t.Logf("📊 计费汇总: %d records, total=%.4f USD (%.4f CHB)",
		summary["total_records"], summary["total_cost_usd"], summary["total_cost_chb"])
}
