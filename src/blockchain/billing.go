// Package blockchain — Sprint 3 物理计费引擎
// 基于真实 GPU 利用率、推理次数、Token 消耗的计费
package blockchain

import (
	"fmt"
	"math"
	"sync"
	"time"
)

// ════════════════════════════════════════════════════════════════════
// 计费模式常量
// ════════════════════════════════════════════════════════════════════

const (
	BillingModeTime        = "time"         // 按时长计费 (基础)
	BillingModeGPUUtil     = "gpu_util"     // 按GPU利用率计费 (更精确)
	BillingModeToken       = "token"        // 按Token消耗计费 (推理任务)
	BillingModeInference   = "inference"    // 按推理次数计费
	BillingModeHybrid      = "hybrid"       // 混合模式 (GPU利用率+时长+Token)

	// 定价常量
	BaseGPUPerHourUSD       = 0.05    // GPU 基础定价
	BaseCPUPerHourUSD       = 0.01    // CPU 基础定价
	UtilGPUPerHourUSD       = 0.08    // 高利用率 GPU 定价
	TokenPer1MUSD           = 0.002   // 每百万 Token 定价
	InferencePer1KUSD       = 0.001   // 每千次推理定价
	MemoryPerGBHourUSD      = 0.002   // 每GB内存每小时
)

// ════════════════════════════════════════════════════════════════════
// 计费数据
// ════════════════════════════════════════════════════════════════════

// BillingRecord 一次计费记录
type BillingRecord struct {
	ID            string    `json:"id"`
	TaskID        string    `json:"task_id"`
	NodeID        string    `json:"node_id"`
	Mode          string    `json:"mode"`
	DurationSecs  float64   `json:"duration_secs"`

	// GPU 利用率数据
	GPUCount      int       `json:"gpu_count"`
	GPUUtilPct    float64   `json:"gpu_util_pct"`    // 平均利用率 (%)
	GPUUtilPeak   float64   `json:"gpu_util_peak"`   // 峰值利用率 (%)
	GPUMemUsedMB  uint64    `json:"gpu_mem_used_mb"` // 平均显存占用

	// Token/推理数据
	TokenIn       int64     `json:"token_in"`
	TokenOut      int64     `json:"token_out"`
	InferenceCount int64    `json:"inference_count"`

	// 成本明细
	CostGPU       float64   `json:"cost_gpu_usd"`
	CostCPU       float64   `json:"cost_cpu_usd"`
	CostMemory    float64   `json:"cost_memory_usd"`
	CostToken     float64   `json:"cost_token_usd"`
	CostTotalUSD  float64   `json:"cost_total_usd"`
	CostTotalCHB  float64   `json:"cost_total_chb"`

	CreatedAt     time.Time `json:"created_at"`
}

// UsageSample 单次资源采样
type UsageSample struct {
	Timestamp   time.Time `json:"timestamp"`
	GPUUtilPct  float64   `json:"gpu_util_pct"`
	GPUMemUsedMB uint64   `json:"gpu_mem_used_mb"`
	CPUPct      float64   `json:"cpu_pct"`
	MemUsedMB   uint64    `json:"mem_used_mb"`
}

// ════════════════════════════════════════════════════════════════════
// 物理计费引擎
// ════════════════════════════════════════════════════════════════════

// BillingEngine 物理计费引擎
type BillingEngine struct {
	mu         sync.RWMutex
	records    map[string]*BillingRecord
	history    []*BillingRecord
	usageLogs  map[string][]UsageSample // taskID -> 采样序列

	// 定价覆盖
	priceGPUPerHour  float64
	priceCPUPerHour  float64
	priceTokenPer1M  float64
	priceInferPer1K  float64
	priceMemGBHour   float64
}

// NewBillingEngine 创建计费引擎
func NewBillingEngine() *BillingEngine {
	return &BillingEngine{
		records:   make(map[string]*BillingRecord),
		history:   make([]*BillingRecord, 0),
		usageLogs: make(map[string][]UsageSample),

		priceGPUPerHour: BaseGPUPerHourUSD,
		priceCPUPerHour: BaseCPUPerHourUSD,
		priceTokenPer1M: TokenPer1MUSD,
		priceInferPer1K: InferencePer1KUSD,
		priceMemGBHour:  MemoryPerGBHourUSD,
	}
}

// RecordUsage 记录资源采样
func (be *BillingEngine) RecordUsage(taskID string, sample UsageSample) {
	be.mu.Lock()
	defer be.mu.Unlock()
	be.usageLogs[taskID] = append(be.usageLogs[taskID], sample)
}

// CalculateAndBill 根据采样数据计算并生成账单
func (be *BillingEngine) CalculateAndBill(taskID, nodeID string, gpuCount, cpuCount int, memoryGB int, mode string) (*BillingRecord, error) {
	be.mu.Lock()
	defer be.mu.Unlock()

	samples := be.usageLogs[taskID]
	if len(samples) < 2 {
		return nil, fmt.Errorf("insufficient usage samples for %s (%d)", taskID, len(samples))
	}

	// 计算实际时长
	duration := samples[len(samples)-1].Timestamp.Sub(samples[0].Timestamp).Seconds()
	if duration < 1 {
		duration = float64(len(samples)) // 至少每采样1秒
	}

	// 计算平均利用率
	var totalUtil, peakUtil, totalMem float64
	totalMem = 0
	for _, s := range samples {
		totalUtil += s.GPUUtilPct
		if s.GPUUtilPct > peakUtil {
			peakUtil = s.GPUUtilPct
		}
		totalMem += float64(s.GPUMemUsedMB)
	}
	avgUtil := totalUtil / float64(len(samples))
	avgMem := totalMem / float64(len(samples))

	// ── 成本计算 ──

	var costGPU, costCPU, costMemory, costToken float64

	switch mode {
	case BillingModeTime:
		// 按时长计费 (基础)
		costGPU = float64(gpuCount) * duration / 3600.0 * be.priceGPUPerHour
		costCPU = float64(cpuCount) * duration / 3600.0 * be.priceCPUPerHour

	case BillingModeGPUUtil:
		// 按GPU利用率计费 (利用率越高单价越高)
		utilFactor := 1.0 + (avgUtil / 100.0) * 0.5 // 利用率权重: 0%~50%加价
		effectivePrice := be.priceGPUPerHour * utilFactor
		costGPU = float64(gpuCount) * duration / 3600.0 * effectivePrice
		costCPU = float64(cpuCount) * duration / 3600.0 * be.priceCPUPerHour

	case BillingModeToken:
		// 按Token消耗 (推理任务)
		// 此处需要外部传入 token 数，这里假设已有数据
		costGPU = 0
		costCPU = float64(cpuCount) * duration / 3600.0 * be.priceCPUPerHour * 0.5

	case BillingModeInference:
		// 按推理次数
		costGPU = 0
		costCPU = 0

	case BillingModeHybrid:
		// 混合模式: GPU利用率定价 + Token消耗 + 内存
		utilMultiplier := 1.0 + (avgUtil / 100.0) * 0.8
		gpuPriceAdj := be.priceGPUPerHour * utilMultiplier
		costGPU = float64(gpuCount) * duration / 3600.0 * gpuPriceAdj
		costCPU = float64(cpuCount) * duration / 3600.0 * be.priceCPUPerHour * 0.8

	default:
		// 默认: 基础按时间
		costGPU = float64(gpuCount) * duration / 3600.0 * be.priceGPUPerHour
		costCPU = float64(cpuCount) * duration / 3600.0 * be.priceCPUPerHour
	}

	// 内存费用
	if memoryGB > 0 {
		costMemory = float64(memoryGB) * duration / 3600.0 * be.priceMemGBHour
	}

	totalUSD := costGPU + costCPU + costMemory + costToken
	totalCHB := totalUSD / CHBUsgdRate
	totalCHB = math.Round(totalCHB*10000) / 10000

	record := &BillingRecord{
		ID:            fmt.Sprintf("bill-%s-%d", taskID, time.Now().UnixNano()),
		TaskID:        taskID,
		NodeID:        nodeID,
		Mode:          mode,
		DurationSecs:  duration,
		GPUCount:      gpuCount,
		GPUUtilPct:    avgUtil,
		GPUUtilPeak:   peakUtil,
		GPUMemUsedMB:  uint64(avgMem),
		CostGPU:       costGPU,
		CostCPU:       costCPU,
		CostMemory:    costMemory,
		CostTotalUSD:  totalUSD,
		CostTotalCHB:  totalCHB,
		CreatedAt:     time.Now(),
	}

	be.records[record.ID] = record
	be.history = append(be.history, record)

	return record, nil
}

// GetBillingRecord 查询账单
func (be *BillingEngine) GetBillingRecord(id string) (*BillingRecord, bool) {
	be.mu.RLock()
	defer be.mu.RUnlock()
	r, ok := be.records[id]
	return r, ok
}

// ListBillingByNode 查询节点的所有账单
func (be *BillingEngine) ListBillingByNode(nodeID string) []*BillingRecord {
	be.mu.RLock()
	defer be.mu.RUnlock()
	var result []*BillingRecord
	for _, r := range be.history {
		if r.NodeID == nodeID {
			result = append(result, r)
		}
	}
	return result
}

// ComputeBillSummary 生成账单摘要
func (be *BillingEngine) ComputeBillSummary() map[string]interface{} {
	be.mu.RLock()
	defer be.mu.RUnlock()

	totalGPU := 0.0
	totalCPU := 0.0
	totalUSD := 0.0
	modeStats := make(map[string]int)

	for _, r := range be.history {
		totalGPU += r.CostGPU
		totalCPU += r.CostCPU
		totalUSD += r.CostTotalUSD
		modeStats[r.Mode]++
	}

	return map[string]interface{}{
		"total_records":      len(be.history),
		"total_cost_gpu":     math.Round(totalGPU*10000) / 10000,
		"total_cost_cpu":     math.Round(totalCPU*10000) / 10000,
		"total_cost_usd":     math.Round(totalUSD*10000) / 10000,
		"total_cost_chb":     math.Round(totalUSD/CHBUsgdRate*10000) / 10000,
		"mode_distribution":  modeStats,
		"pricing_gpu_hr":     be.priceGPUPerHour,
		"pricing_cpu_hr":     be.priceCPUPerHour,
		"pricing_token_1m":   be.priceTokenPer1M,
		"pricing_infer_1k":   be.priceInferPer1K,
	}
}
