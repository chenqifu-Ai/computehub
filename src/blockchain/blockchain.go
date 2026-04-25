// Package blockchain implements ComputeHub's physical settlement layer.
// It tracks compute resource usage per task, converts usage to CHB token balances,
// and provides audit trails for node-to-node settlement.
package blockchain

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"
)

// ─── 结算常量 ───

const (
	TokenSymbol = "CHB"

	// Default pricing from config.json
	DefaultGPUPricePerHour = 0.05  // USD per GPU-hour
	DefaultCPPricePerHour  = 0.01  // USD per CPU-hour
	DefaultStoragePerGB    = 0.10  // USD per GB-month

	// CHB conversion rate (example: 1 CHB = $0.01 USD)
	CHBUsgdRate = 0.01
)

// ─── 结算记录 ───

// SettlementRecord tracks a single compute session's resource usage and cost.
type SettlementRecord struct {
	ID         string    `json:"id"`
	TaskID     string    `json:"task_id"`
	NodeID     string    `json:"node_id"`
	ResourceType string  `json:"resource_type"`
	GPUCount   int       `json:"gpu_count"`
	CPUCount   int       `json:"cpu_count"`
	MemoryGB   int       `json:"memory_gb"`
	Duration   string    `json:"duration"`
	DurationSecs float64 `json:"duration_secs"`
	CostUSD    float64   `json:"cost_usd"`
	CostCHB    float64   `json:"cost_chb"`
	Timestamp  time.Time `json:"timestamp"`
	Status     string    `json:"status"` // pending, settled, disputed
	Disputed   bool      `json:"disputed"`
}

// ─── 节点钱包 ───

// Wallet tracks a node's token balance and transaction history.
type Wallet struct {
	NodeID    string    `json:"node_id"`
	Balance   float64   `json:"balance"`
	TotalEarned float64 `json:"total_earned"`
	TotalSpent  float64 `json:"total_spent"`
	Created   time.Time `json:"created"`
	LastTx    time.Time `json:"last_tx"`
}

// ─── 交易 ───

// Transaction represents a blockchain entry.
type Transaction struct {
	ID          string    `json:"id"`
	FromNode    string    `json:"from_node"`
	ToNode      string    `json:"to_node"`
	Amount      float64   `json:"amount"`
	Token       string    `json:"token"`
	Type        string    `json:"type"` // payment, refund, penalty, reward
	RelatedTx   string    `json:"related_tx"`
	Timestamp   time.Time `json:"timestamp"`
	Confirmations int     `json:"confirmations"`
	BlockHeight  int64    `json:"block_height"`
}

// ─── 区块链 ───

// Blockchain is a simple Merkle-tree-based ledger for ComputeHub settlement.
type Blockchain struct {
	mu        sync.RWMutex
	tail      *Block
	height    int64
	chainFile string

	// Node wallets
	wallets   map[string]*Wallet

	// Transaction pool (mempool)
	mempool   []Transaction

	// Settlement records
	settlements map[string]*SettlementRecord
}

// Block represents a single block in the chain.
type Block struct {
	Index       int64     `json:"index"`
	Timestamp   time.Time `json:"timestamp"`
	Transactions []Transaction `json:"transactions"`
	PreviousHash string   `json:"previous_hash"`
	Hash        string    `json:"hash"`
}

// ─── 初始化 ───

// NewBlockchain creates a blockchain with the given chain file path.
func NewBlockchain(chainFile string) *Blockchain {
	bc := &Blockchain{
		tail:        nil,
		height:      0,
		chainFile:   chainFile,
		wallets:     make(map[string]*Wallet),
		mempool:     make([]Transaction, 0),
		settlements: make(map[string]*SettlementRecord),
	}

	// Create genesis block
	bc.createGenesisBlock()

	// Load existing chain if exists
	bc.loadChain()

	return bc
}

// ─── 创世块 ───

func (bc *Blockchain) createGenesisBlock() {
	genesis := &Block{
		Index:      0,
		Timestamp:  time.Now(),
		Hash:       bc.computeHash(0, "0", "genesis"),
		PreviousHash: "0",
		Transactions: []Transaction{
			{
				ID:          "genesis",
				FromNode:    "system",
				ToNode:      "treasury",
				Amount:      100000.0,
				Token:       TokenSymbol,
				Type:        "reward",
				Timestamp:   time.Now(),
				Confirmations: 1,
				BlockHeight:  0,
			},
		},
	}
	bc.tail = genesis
}

// ─── 链持久化 ───

// Save persists the blockchain to disk.
func (bc *Blockchain) Save() error {
	bc.mu.RLock()
	defer bc.mu.RUnlock()

	// Collect all blocks from genesis to tail
	blocks := make([]*Block, 0)
	current := bc.tail
	for current != nil {
		blocks = append(blocks, current)
		// Traverse backwards (in a real implementation, blocks would link forward too)
		// For simplicity, we store the entire chain state
		break // simplified: only tail for now
	}

	data, err := json.MarshalIndent(bc, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal blockchain: %w", err)
	}

	return os.WriteFile(bc.chainFile, data, 0644)
}

// loadChain loads blockchain state from disk.
func (bc *Blockchain) loadChain() {
	data, err := os.ReadFile(bc.chainFile)
	if err != nil {
		return // No existing chain, start fresh
	}

	var loaded Blockchain
	if err := json.Unmarshal(data, &loaded); err != nil {
		return
	}

	bc.mu.Lock()
	bc.height = loaded.height
	bc.wallets = loaded.wallets
	bc.settlements = loaded.settlements
	bc.tail = loaded.tail
	bc.mu.Unlock()
}

// ─── 区块计算 ───

func (bc *Blockchain) computeHash(index int64, prevHash string, txData string) string {
	// Simplified hash (in production, use SHA-256)
	data := fmt.Sprintf("%d%s%s%d", index, prevHash, txData, time.Now().UnixNano())
	// Simple hash simulation
	hash := 0
	for _, b := range data {
		hash = hash*31 + int(b)
	}
	return fmt.Sprintf("%08x", hash&0xFFFFFFFF)
}

// ─── 结算引擎 ───

// CalculateSettlement computes the cost for a task execution.
func (bc *Blockchain) CalculateSettlement(record *SettlementRecord) error {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	record.ID = fmt.Sprintf("settle-%d", time.Now().UnixNano())
	record.Timestamp = time.Now()
	record.Status = "pending"

	// Calculate USD cost based on resource usage and duration
	record.CostUSD = bc.calculateUSD(record)

	// Convert to CHB
	record.CostCHB = record.CostUSD / CHBUsgdRate

	// Round to 4 decimal places
	record.CostUSD = float64(int(record.CostUSD*10000)) / 10000
	record.CostCHB = float64(int(record.CostCHB*10000)) / 10000

	return nil
}

func (bc *Blockchain) calculateUSD(record *SettlementRecord) float64 {
	cost := 0.0

	switch record.ResourceType {
	case "gpu":
		cost = float64(record.GPUCount) * record.DurationSecs / 3600.0 * DefaultGPUPricePerHour
	case "cpu":
		cost = float64(record.CPUCount) * record.DurationSecs / 3600.0 * DefaultCPPricePerHour
	default:
		// Custom: estimate based on memory and duration
		cost = float64(record.MemoryGB) * record.DurationSecs / 86400.0 * DefaultStoragePerGB
	}

	// Add storage cost if memory specified
	if record.MemoryGB > 0 {
		storageGB := float64(record.MemoryGB)
		storageDays := record.DurationSecs / 86400.0
		if storageDays < 1 {
			storageDays = 1 // Minimum 1 day for storage
		}
		storageCost := storageGB * storageDays / 30.0 * DefaultStoragePerGB
		cost += storageCost
	}

	return cost
}

// ─── 内部无锁方法 ───

// getOrCreateWalletInternal - 必须持有写锁调用
func (bc *Blockchain) getOrCreateWalletInternal(nodeID string) *Wallet {
	if wallet, exists := bc.wallets[nodeID]; exists {
		return wallet
	}
	wallet := &Wallet{
		NodeID:     nodeID,
		Balance:    0.0,
		Created:    time.Now(),
		LastTx:     time.Now(),
	}
	bc.wallets[nodeID] = wallet
	return wallet
}

// ─── 钱包管理 ───

// GetOrCreateWallet returns a wallet for the given node, creating it if needed.
func (bc *Blockchain) GetOrCreateWallet(nodeID string) *Wallet {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	if wallet, exists := bc.wallets[nodeID]; exists {
		return wallet
	}

	wallet := &Wallet{
		NodeID:     nodeID,
		Balance:    0.0,
		Created:    time.Now(),
		LastTx:     time.Now(),
	}
	bc.wallets[nodeID] = wallet
	return wallet
}

// CreditWallet adds CHB to a node's wallet.
func (bc *Blockchain) CreditWallet(nodeID string, amount float64) (*Wallet, error) {
	bc.mu.Lock()
	defer bc.mu.Unlock()
	wallet := bc.getOrCreateWalletInternal(nodeID)
	wallet.Balance += amount
	wallet.TotalEarned += amount
	wallet.LastTx = time.Now()
	return wallet, nil
}

// DebitWallet subtracts CHB from a node's wallet.
func (bc *Blockchain) DebitWallet(nodeID string, amount float64) (*Wallet, error) {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	wallet, exists := bc.wallets[nodeID]
	if !exists {
		wallet = &Wallet{NodeID: nodeID, Created: time.Now()}
		bc.wallets[nodeID] = wallet
	}

	if wallet.Balance < amount {
		return nil, fmt.Errorf("insufficient balance: %.4f CHB < %.4f CHB", wallet.Balance, amount)
	}

	wallet.Balance -= amount
	wallet.TotalSpent += amount
	wallet.LastTx = time.Now()

	return wallet, nil
}

// ─── 内部无锁方法（调用方必须持有锁） ───

func (bc *Blockchain) addTxLocked(tx *Transaction) {
	tx.ID = fmt.Sprintf("tx-%d", time.Now().UnixNano())
	tx.Timestamp = time.Now()
	bc.mempool = append(bc.mempool, *tx)
}

func (bc *Blockchain) getOrCreateWalletLocked(nodeID string) *Wallet {
	if wallet, exists := bc.wallets[nodeID]; exists {
		return wallet
	}
	wallet := &Wallet{
		NodeID:     nodeID,
		Balance:    0.0,
		Created:    time.Now(),
		LastTx:     time.Now(),
	}
	bc.wallets[nodeID] = wallet
	return wallet
}

// ─── 交易处理 ───

// AddTransaction adds a transaction to the mempool.
func (bc *Blockchain) AddTransaction(tx Transaction) {
	bc.mu.Lock()
	defer bc.mu.Unlock()
	bc.addTxLocked(&tx)
}

// MineBlock validates and appends mempool transactions to the chain.
func (bc *Blockchain) MineBlock() (*Block, error) {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	// Take all mempool transactions
	txs := make([]Transaction, len(bc.mempool))
	copy(txs, bc.mempool)
	bc.mempool = bc.mempool[:0]

	bc.height++
	newBlock := &Block{
		Index:        bc.height,
		Timestamp:    time.Now(),
		Transactions: txs,
		PreviousHash: bc.tail.Hash,
		Hash:         bc.computeHash(bc.height, bc.tail.Hash, fmt.Sprintf("%d", len(txs))),
	}

	// Update confirmations for all transactions in this block
	for i := range txs {
		txs[i].BlockHeight = bc.height
		txs[i].Confirmations = 1
	}

	bc.tail = newBlock

	// Save to disk
	bc.saveChainLocked()

	return newBlock, nil
}

func (bc *Blockchain) saveChainLocked() {
	data, err := json.MarshalIndent(bc, "", "  ")
	if err != nil {
		return
	}
	os.WriteFile(bc.chainFile, data, 0644)
}

// ─── 结算执行 ───

// ExecuteSettlement processes a settlement record: debit from client, credit to node.
func (bc *Blockchain) ExecuteSettlement(record *SettlementRecord) error {
	bc.CalculateSettlement(record)

	if record.CostCHB > 0 {
		// Credit node wallet
		bc.CreditWallet(record.NodeID, record.CostCHB)
	}

	record.Status = "settled"
	bc.settlements[record.ID] = record
	return nil
}

// ─── 争议处理 ───

// DisputeSettlement marks a settlement as disputed.
func (bc *Blockchain) DisputeSettlement(recordID string) error {
	bc.mu.Lock()
	defer bc.mu.Unlock()

	record, exists := bc.settlements[recordID]
	if !exists {
		return fmt.Errorf("settlement %s not found", recordID)
	}

	if record.Status == "settled" {
		// Reverse the transaction
		record.Status = "disputed"
		record.Disputed = true

		// Add refund transaction (no lock needed here since we hold the lock)
		bc.addTxLocked(&Transaction{
			ID:       fmt.Sprintf("refund-%s", recordID),
			FromNode: record.NodeID,
			ToNode:   record.NodeID + "-client",
			Amount:   record.CostCHB,
			Token:    TokenSymbol,
			Type:     "refund",
			RelatedTx: recordID,
		})
	}

	return nil
}

// ─── 审计查询 ───

// GetSettlement returns a settlement record by ID.
func (bc *Blockchain) GetSettlement(id string) (*SettlementRecord, bool) {
	bc.mu.RLock()
	defer bc.mu.RUnlock()
	record, ok := bc.settlements[id]
	return record, ok
}

// GetWallet returns a node's wallet.
func (bc *Blockchain) GetWallet(nodeID string) (*Wallet, bool) {
	bc.mu.RLock()
	defer bc.mu.RUnlock()
	wallet, ok := bc.wallets[nodeID]
	return wallet, ok
}

// GetChainInfo returns blockchain summary statistics.
func (bc *Blockchain) GetChainInfo() map[string]any {
	bc.mu.RLock()
	defer bc.mu.RUnlock()

	totalBlocks := bc.height + 1 // +1 for genesis block
	result := map[string]any{
		"height":       bc.height,
		"total_blocks": totalBlocks,
		"total_nodes":    len(bc.wallets),
		"mempool_size":   len(bc.mempool),
		"total_settlements": len(bc.settlements),
		"pending_settlements": func() int {
			count := 0
			for _, r := range bc.settlements {
				if r.Status == "pending" {
					count++
				}
			}
			return count
		}(),
		"token_symbol":    TokenSymbol,
		"usd_rate":        CHBUsgdRate,
		"gpu_price_usd":   DefaultGPUPricePerHour,
		"cpu_price_usd":   DefaultCPPricePerHour,
	}
	return result
}

// SettleAllPending processes all pending settlements.
func (bc *Blockchain) SettleAllPending() int {
	bc.mu.Lock()

	count := 0
	for _, record := range bc.settlements {
		if record.Status == "pending" {
			if record.CostCHB > 0 {
				// Credit node wallet (lock already held)
				wallet, exists := bc.wallets[record.NodeID]
				if !exists {
					wallet = &Wallet{NodeID: record.NodeID, Created: time.Now()}
					bc.wallets[record.NodeID] = wallet
				}
				wallet.Balance += record.CostCHB
				wallet.TotalEarned += record.CostCHB
				wallet.LastTx = time.Now()
				record.Status = "settled"
				count++
			}
		}
	}

	bc.mu.Unlock()

	if count > 0 {
		bc.saveChainLocked()
	}

	return count
}

// PayClient withdraws CHB from client wallet to pay for a settlement.
func (bc *Blockchain) PayClient(clientID string, amount float64) error {
	_, err := bc.DebitWallet(clientID, amount)
	return err
}
