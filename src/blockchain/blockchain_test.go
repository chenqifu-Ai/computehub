// Package blockchain - comprehensive tests for settlement layer
package blockchain

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// ─── 基础功能测试 ───

func TestNewBlockchain(t *testing.T) {
	tmpDir := t.TempDir()
	chainFile := filepath.Join(tmpDir, "chain.json")

	bc := NewBlockchain(chainFile)
	if bc == nil {
		t.Fatal("Blockchain should not be nil")
	}

	info := bc.GetChainInfo()
	if info["height"] != int64(0) {
		t.Errorf("Expected height 0, got %v", info["height"])
	}
	if info["total_blocks"] != int64(1) {
		t.Errorf("Expected 1 genesis block, got %v", info["total_blocks"])
	}
}

func TestBlockchainPersist(t *testing.T) {
	tmpDir := t.TempDir()
	chainFile := filepath.Join(tmpDir, "chain.json")

	bc := NewBlockchain(chainFile)

	// Add a transaction
	bc.AddTransaction(Transaction{
		FromNode: "node-001",
		ToNode:   "node-002",
		Amount:   10.0,
		Token:    TokenSymbol,
		Type:     "payment",
	})

	// Mine a block
	block, err := bc.MineBlock()
	if err != nil {
		t.Fatalf("MineBlock should succeed: %v", err)
	}
	if block == nil {
		t.Fatal("Block should not be nil")
	}
	if block.Index != 1 {
		t.Errorf("Expected block index 1, got %d", block.Index)
	}

	// Verify chain was persisted
	if _, err := os.Stat(chainFile); err != nil {
		t.Fatal("Chain file should exist after mining")
	}
}

// ─── 结算计算测试 ───

func TestCalculateSettlement_GPU(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	record := &SettlementRecord{
		TaskID:       "gpu-001",
		NodeID:       "node-001",
		ResourceType: "gpu",
		GPUCount:     2,
		DurationSecs: 3600, // 1 hour
	}

	if err := bc.CalculateSettlement(record); err != nil {
		t.Fatalf("CalculateSettlement should succeed: %v", err)
	}

	// Cost = 2 GPUs * 1 hour * $0.05/GPU-hr = $0.10
	expectedUSD := 0.10
	if record.CostUSD != expectedUSD {
		t.Errorf("Expected USD %.4f, got %.4f", expectedUSD, record.CostUSD)
	}
	if record.Status != "pending" {
		t.Errorf("Expected status pending, got %s", record.Status)
	}
}

func TestCalculateSettlement_CPU(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	record := &SettlementRecord{
		TaskID:       "cpu-001",
		NodeID:       "node-001",
		ResourceType: "cpu",
		CPUCount:     4,
		DurationSecs: 7200, // 2 hours
	}

	if err := bc.CalculateSettlement(record); err != nil {
		t.Fatalf("CalculateSettlement should succeed: %v", err)
	}

	// Cost = 4 CPUs * 2 hours * $0.01/CPU-hr = $0.08
	expectedUSD := 0.08
	if record.CostUSD != expectedUSD {
		t.Errorf("Expected USD %.4f, got %.4f", expectedUSD, record.CostUSD)
	}
}

func TestCalculateSettlement_Custom(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	record := &SettlementRecord{
		TaskID:       "custom-001",
		NodeID:       "node-001",
		ResourceType: "custom",
		MemoryGB:     16,
		DurationSecs: 86400, // 1 day
	}

	if err := bc.CalculateSettlement(record); err != nil {
		t.Fatalf("CalculateSettlement should succeed: %v", err)
	}
	if record.CostUSD < 0 {
		t.Error("Cost should be non-negative")
	}
}

// ─── 钱包管理测试 ───

func TestGetOrCreateWallet(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	wallet := bc.GetOrCreateWallet("wallet-test-001")
	if wallet == nil {
		t.Fatal("Wallet should not be nil")
	}
	if wallet.Balance != 0.0 {
		t.Errorf("Expected 0 balance, got %.4f", wallet.Balance)
	}
}

func TestCreditWallet(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	wallet, err := bc.CreditWallet("cred-001", 100.0)
	if err != nil {
		t.Fatalf("CreditWallet should succeed: %v", err)
	}
	if wallet.Balance != 100.0 {
		t.Errorf("Expected balance 100, got %.4f", wallet.Balance)
	}
	if wallet.TotalEarned != 100.0 {
		t.Errorf("Expected total_earned 100, got %.4f", wallet.TotalEarned)
	}
}

func TestDebitWallet_Success(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	bc.CreditWallet("debit-001", 50.0)

	wallet, err := bc.DebitWallet("debit-001", 30.0)
	if err != nil {
		t.Fatalf("DebitWallet should succeed: %v", err)
	}
	if wallet.Balance != 20.0 {
		t.Errorf("Expected balance 20, got %.4f", wallet.Balance)
	}
	if wallet.TotalSpent != 30.0 {
		t.Errorf("Expected total_spent 30, got %.4f", wallet.TotalSpent)
	}
}

func TestDebitWallet_InsufficientFunds(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	bc.CreditWallet("debit-fail-001", 10.0)

	_, err := bc.DebitWallet("debit-fail-001", 50.0)
	if err == nil {
		t.Error("DebitWallet should fail with insufficient funds")
	}
}

// ─── 交易处理测试 ───

func TestMineBlock(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	// Add transactions
	bc.AddTransaction(Transaction{FromNode: "A", ToNode: "B", Amount: 5.0, Type: "payment"})
	bc.AddTransaction(Transaction{FromNode: "C", ToNode: "D", Amount: 10.0, Type: "payment"})

	block, err := bc.MineBlock()
	if err != nil {
		t.Fatalf("MineBlock should succeed: %v", err)
	}

	if block.Index != 1 {
		t.Errorf("Expected block index 1, got %d", block.Index)
	}
	if len(block.Transactions) != 2 {
		t.Errorf("Expected 2 transactions in block, got %d", len(block.Transactions))
	}
}

func TestMempoolClearedAfterMine(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	bc.AddTransaction(Transaction{FromNode: "A", ToNode: "B", Amount: 5.0})

	bc.MineBlock()

	info := bc.GetChainInfo()
	if info["mempool_size"] != 0 {
		t.Errorf("Expected empty mempool, got %d", info["mempool_size"])
	}
}

// ─── 结算执行测试 ───

func TestExecuteSettlement(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	// Credit a client wallet
	bc.CreditWallet("client-001", 50.0)

	record := &SettlementRecord{
		TaskID:       "exec-001",
		NodeID:       "node-001",
		ResourceType: "gpu",
		GPUCount:     1,
		DurationSecs: 3600,
	}

	err := bc.ExecuteSettlement(record)
	if err != nil {
		t.Fatalf("ExecuteSettlement should succeed: %v", err)
	}

	// Verify settlement was recorded
	saved, ok := bc.GetSettlement(record.ID)
	if !ok {
		t.Fatal("Settlement should be retrievable")
	}
	if saved.CostUSD <= 0 {
		t.Error("Settlement should have positive cost")
	}
}

// ─── 争议处理测试 ───

func TestDisputeSettlement(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	bc.CreditWallet("dispute-client", 50.0)

	record := &SettlementRecord{
		TaskID:       "dispute-001",
		NodeID:       "node-001",
		ResourceType: "cpu",
		CPUCount:     2,
		DurationSecs: 3600,
	}

	bc.ExecuteSettlement(record)

	// Dispute the settlement
	err := bc.DisputeSettlement(record.ID)
	if err != nil {
		t.Fatalf("DisputeSettlement should succeed: %v", err)
	}

	saved, _ := bc.GetSettlement(record.ID)
	if saved.Status != "disputed" {
		t.Errorf("Expected disputed status, got %s", saved.Status)
	}
}

func TestDisputeNonexistent(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	err := bc.DisputeSettlement("nonexistent")
	if err == nil {
		t.Error("DisputeSettlement should fail for nonexistent record")
	}
}

// ─── 批量结算测试 ───

func TestSettleAllPending(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	// Create wallet with funds
	bc.CreditWallet("batch-client", 100.0)

	// Create pending settlement records directly (bypass ExecuteSettlement which already settles)
	for i := 0; i < 3; i++ {
		record := &SettlementRecord{
			ID:           fmt.Sprintf("batch-pending-%d", i),
			TaskID:       fmt.Sprintf("batch-task-%d", i),
			NodeID:       "node-001",
			ResourceType: "cpu",
			CPUCount:     1,
			DurationSecs: 1800,
			CostCHB:      1.0, // Pre-calculated
			Status:       "pending",
		}
		bc.settlements[record.ID] = record
	}

	settled := bc.SettleAllPending()
	if settled != 3 {
		t.Errorf("Expected 3 settled, got %d", settled)
	}
}

// ─── 链信息测试 ───

func TestGetChainInfo(t *testing.T) {
	tmpDir := t.TempDir()
	bc := NewBlockchain(filepath.Join(tmpDir, "chain.json"))

	info := bc.GetChainInfo()
	if info["token_symbol"] != TokenSymbol {
		t.Errorf("Expected token symbol %s, got %v", TokenSymbol, info["token_symbol"])
	}
	if info["height"] != int64(0) {
		t.Errorf("Expected height 0, got %v", info["height"])
	}
}

// ─── 价格计算测试 ───

func TestGetPrices(t *testing.T) {
	if DefaultGPUPricePerHour != 0.05 {
		t.Errorf("Expected GPU price $0.05/hr, got $%f", DefaultGPUPricePerHour)
	}
	if DefaultCPPricePerHour != 0.01 {
		t.Errorf("Expected CPU price $0.01/hr, got $%f", DefaultCPPricePerHour)
	}
	if DefaultStoragePerGB != 0.10 {
		t.Errorf("Expected storage price $0.10/GB/mo, got $%f", DefaultStoragePerGB)
	}
}
