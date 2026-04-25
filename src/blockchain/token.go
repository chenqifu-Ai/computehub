// Package blockchain implements ComputeHub's Token economic model and settlement layer.
package blockchain

import (
	"fmt"
	"sync"
	"time"
)

// ─── Token 经济模型常量 ───

const (
	// CHB Token 总供应量 (100,000,000 CHB)
	TotalSupply = 100000000.0

	// 最小充值金额 (10 CHB)
	MinDeposit = 10.0

	// 最小提现金额 (1 CHB)
	MinWithdraw = 1.0

	// 提现手续费率 (1%)
	WithdrawFeeRate = 0.01

	// 每日提现限额 (10000 CHB)
	DailyWithdrawLimit = 10000.0
)

// ─── Token 账户 ───

// TokenAccount represents a CHB Token account.
type TokenAccount struct {
	Address    string    `json:"address"`
	Balance    float64   `json:"balance"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
	TotalIn    float64   `json:"total_in"`    // 累计充值
	TotalOut   float64   `json:"total_out"`   // 累计提现
	IsMint     bool      `json:"is_mint"`     // 是否为铸造账户
	Minted     float64   `json:"minted"`      // 已铸造量
}

// ─── 充值记录 ───

// DepositRecord tracks a token recharge.
type DepositRecord struct {
	ID          string    `json:"id"`
	Address     string    `json:"address"`
	Amount      float64   `json:"amount"`
	USDEquiv    float64   `json:"usd_equiv"` // 等值 USD
	Timestamp   time.Time `json:"timestamp"`
	Status      string    `json:"status"` // pending, completed, failed
	Transaction string    `json:"transaction"`
}

// ─── 提现记录 ───

// WithdrawRecord tracks a token withdrawal.
type WithdrawRecord struct {
	ID           string    `json:"id"`
	Address      string    `json:"address"`
	Amount       float64   `json:"amount"`
	Fee          float64   `json:"fee"`
	NetAmount    float64   `json:"net_amount"` // 实际到账
	USDEquiv     float64   `json:"usd_equiv"`
	ToAddress    string    `json:"to_address"`
	Timestamp    time.Time `json:"timestamp"`
	Status       string    `json:"status"` // pending, completed, failed
	Transaction  string    `json:"transaction"`
}

// ─── 交易记录 ───

// TokenTransaction represents a token transfer.
type TokenTransaction struct {
	ID         string    `json:"id"`
	From       string    `json:"from"`
	To         string    `json:"to"`
	Amount     float64   `json:"amount"`
	Type       string    `json:"type"` // deposit, withdraw, transfer, settlement, refund, reward, penalty
	Metadata   string    `json:"metadata"`
	Timestamp  time.Time `json:"timestamp"`
	BlockHash  string    `json:"block_hash"`
	Confirmations int    `json:"confirmations"`
}

// ─── Token 管理器 ───

// TokenManager manages CHB Token economy.
type TokenManager struct {
	mu sync.RWMutex

	// Token 账户
	accounts map[string]*TokenAccount

	// 交易记录
	txHistory []TokenTransaction

	// 充值记录
	deposits map[string]*DepositRecord

	// 提现记录
	withdrawals map[string]*WithdrawRecord

	// 每日提现限额跟踪
	dailyWithdraw map[string]float64 // address -> daily total

	// 区块高度 (用于交易确认)
	blockHeight int64

	// 区块存储
	blocks map[int64]*Block
}

// ─── 初始化 ───

// NewTokenManager creates a new token manager.
func NewTokenManager() *TokenManager {
	tm := &TokenManager{
		accounts:      make(map[string]*TokenAccount),
		txHistory:     make([]TokenTransaction, 0),
		deposits:      make(map[string]*DepositRecord),
		withdrawals:   make(map[string]*WithdrawRecord),
		dailyWithdraw: make(map[string]float64),
		blocks:        make(map[int64]*Block),
	}

	// 创建系统铸造账户
	tm.createSystemAccount()

	return tm
}

// ─── 系统账户 ───

func (tm *TokenManager) createSystemAccount() {
	tm.accounts["system"] = &TokenAccount{
		Address:   "system",
		Balance:   TotalSupply,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsMint:    true,
		Minted:    TotalSupply,
	}
}

// ─── 账户管理 ───

// GetOrCreateAccount returns a token account, creating it if needed.
func (tm *TokenManager) GetOrCreateAccount(address string) *TokenAccount {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	if account, exists := tm.accounts[address]; exists {
		return account
	}

	account := &TokenAccount{
		Address:   address,
		Balance:   0,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsMint:    false,
	}
	tm.accounts[address] = account
	return account
}

// GetAccount returns a token account by address.
func (tm *TokenManager) GetAccount(address string) (*TokenAccount, bool) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	account, exists := tm.accounts[address]
	return account, exists
}

// GetBalance returns the balance of an account.
func (tm *TokenManager) GetBalance(address string) (float64, bool) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	account, exists := tm.accounts[address]
	if !exists {
		return 0, false
	}
	return account.Balance, true
}

// ─── 充值 ───

// Deposit processes a token deposit.
func (tm *TokenManager) Deposit(address string, amount float64, usdEquiv float64, transaction string) (*DepositRecord, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	// Validate amount
	if amount < MinDeposit {
		return nil, fmt.Errorf("deposit amount %.2f CHB below minimum %.2f CHB", amount, MinDeposit)
	}

	// Get or create account
	account, exists := tm.accounts[address]
	if !exists {
		account = &TokenAccount{
			Address:   address,
			Balance:   0,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
			IsMint:    false,
		}
		tm.accounts[address] = account
	}

	// Create deposit record
	record := &DepositRecord{
		ID:          fmt.Sprintf("dep-%d", time.Now().UnixNano()),
		Address:     address,
		Amount:      amount,
		USDEquiv:    usdEquiv,
		Timestamp:   time.Now(),
		Status:      "completed",
		Transaction: transaction,
	}
	tm.deposits[record.ID] = record

	// Update account balance
	account.Balance += amount
	account.TotalIn += amount
	account.UpdatedAt = time.Now()

	// Record transaction
	tx := TokenTransaction{
		ID:          fmt.Sprintf("tx-dep-%d", time.Now().UnixNano()),
		From:        "system",
		To:          address,
		Amount:      amount,
		Type:        "deposit",
		Metadata:    record.ID,
		Timestamp:   time.Now(),
		Confirmations: 1,
	}
	tm.txHistory = append(tm.txHistory, tx)
	record.Transaction = tx.ID

	return record, nil
}

// ─── 提现 ───

// Withdraw processes a token withdrawal.
func (tm *TokenManager) Withdraw(address string, amount float64, toAddress string) (*WithdrawRecord, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	// Validate amount
	if amount < MinWithdraw {
		return nil, fmt.Errorf("withdrawal amount %.2f CHB below minimum %.2f CHB", amount, MinWithdraw)
	}

	// Get account
	account, exists := tm.accounts[address]
	if !exists {
		return nil, fmt.Errorf("account %s not found", address)
	}

	// Check balance
	if account.Balance < amount {
		return nil, fmt.Errorf("insufficient balance: %.2f CHB available, %.2f CHB requested", account.Balance, amount)
	}

	// Check daily limit
	dailyTotal := tm.dailyWithdraw[address]
	if dailyTotal+amount > DailyWithdrawLimit {
		return nil, fmt.Errorf("daily withdrawal limit exceeded: %.2f/%.2f CHB used", dailyTotal+amount, DailyWithdrawLimit)
	}

	// Calculate fee
	fee := amount * WithdrawFeeRate
	netAmount := amount - fee

	// Create withdrawal record
	record := &WithdrawRecord{
		ID:          fmt.Sprintf("wd-%d", time.Now().UnixNano()),
		Address:     address,
		Amount:      amount,
		Fee:         fee,
		NetAmount:   netAmount,
		USDEquiv:    amount * CHBUsgdRate,
		ToAddress:   toAddress,
		Timestamp:   time.Now(),
		Status:      "completed",
		Transaction: fmt.Sprintf("tx-wd-%d", time.Now().UnixNano()),
	}
	tm.withdrawals[record.ID] = record

	// Update account balance
	account.Balance -= amount
	account.TotalOut += amount
	account.UpdatedAt = time.Now()

	// Update daily withdrawal tracking
	tm.dailyWithdraw[address] = dailyTotal + amount

	// Record transaction
	tx := TokenTransaction{
		ID:          record.Transaction,
		From:        address,
		To:          toAddress,
		Amount:      netAmount,
		Type:        "withdraw",
		Metadata:    record.ID,
		Timestamp:   time.Now(),
		Confirmations: 1,
	}
	tm.txHistory = append(tm.txHistory, tx)

	return record, nil
}

// ─── 转账 ───

// Transfer transfers tokens between accounts.
func (tm *TokenManager) Transfer(from, to string, amount float64) (*TokenTransaction, error) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	// Get source account
	fromAccount, exists := tm.accounts[from]
	if !exists {
		return nil, fmt.Errorf("source account %s not found", from)
	}

	// Check balance
	if fromAccount.Balance < amount {
		return nil, fmt.Errorf("insufficient balance: %.2f CHB available, %.2f CHB requested", fromAccount.Balance, amount)
	}

	// Get or create destination account
	toAccount, exists := tm.accounts[to]
	if !exists {
		toAccount = &TokenAccount{
			Address:   to,
			Balance:   0,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
			IsMint:    false,
		}
		tm.accounts[to] = toAccount
	}

	// Transfer
	fromAccount.Balance -= amount
	fromAccount.UpdatedAt = time.Now()
	toAccount.Balance += amount
	toAccount.UpdatedAt = time.Now()

	// Record transaction
	tx := TokenTransaction{
		ID:          fmt.Sprintf("tx-transfer-%d", time.Now().UnixNano()),
		From:        from,
		To:          to,
		Amount:      amount,
		Type:        "transfer",
		Timestamp:   time.Now(),
		Confirmations: 1,
	}
	tm.txHistory = append(tm.txHistory, tx)

	return &tx, nil
}

// ─── 交易记录 ───

// GetTransaction returns a transaction by ID.
func (tm *TokenManager) GetTransaction(id string) (*TokenTransaction, bool) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	for _, tx := range tm.txHistory {
		if tx.ID == id {
			return &tx, true
		}
	}
	return nil, false
}

// GetTransactionHistory returns transaction history for an account.
func (tm *TokenManager) GetTransactionHistory(address string, limit int) []TokenTransaction {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	var history []TokenTransaction
	for _, tx := range tm.txHistory {
		if tx.From == address || tx.To == address {
			history = append(history, tx)
		}
	}

	// Limit results
	if limit > 0 && len(history) > limit {
		history = history[len(history)-limit:]
	}

	return history
}

// ─── 统计 ───

// GetTokenStats returns token economy statistics.
func (tm *TokenManager) GetTokenStats() map[string]interface{} {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	totalAccounts := len(tm.accounts)
	totalDeposits := float64(0)
	totalWithdrawals := float64(0)
	for _, account := range tm.accounts {
		totalDeposits += account.TotalIn
		totalWithdrawals += account.TotalOut
	}

	return map[string]interface{}{
		"total_supply":      TotalSupply,
		"circulating_supply":  TotalSupply - totalWithdrawals,
		"total_accounts":    totalAccounts,
		"total_deposits":    totalDeposits,
		"total_withdrawals": totalWithdrawals,
		"total_transactions": len(tm.txHistory),
		"token_symbol":       TokenSymbol,
		"usd_rate":           CHBUsgdRate,
	}
}

// ─── 时间重置 ───

// ResetDailyLimits should be called daily to reset withdrawal limits.
func (tm *TokenManager) ResetDailyLimits() {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	tm.dailyWithdraw = make(map[string]float64)
}
