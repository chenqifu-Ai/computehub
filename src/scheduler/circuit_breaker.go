package scheduler

import (
	"fmt"
	"sync"
	"time"
)

// CircuitBreaker 区域熔断器实现
// 基于物理指标自动熔断故障区域，防止任务分配到坏节点

// CircuitState 熔断状态
type CircuitState int

const (
	CircuitClosed   CircuitState = iota // 正常，流量通过
	CircuitOpen                         // 熔断，流量阻断
	CircuitHalfOpen                     // 半开，试探性恢复
)

func (s CircuitState) String() string {
	switch s {
	case CircuitClosed:
		return "closed"
	case CircuitOpen:
		return "open"
	case CircuitHalfOpen:
		return "half-open"
	default:
		return "unknown"
	}
}

// RegionCircuit 单个区域的熔断器
type RegionCircuit struct {
	Region      string        `json:"region"`
	State       CircuitState  `json:"state"`
	SuccessCount   int           `json:"success_count"`
	FailureCount   int           `json:"failure_count"`
	TotalAttempts  int           `json:"total_attempts"`
	LastFailure    time.Time     `json:"last_failure"`
	LastRecovery   time.Time     `json:"last_recovery"`
	OpenSince      time.Time     `json:"open_since"`
	SuccessRate    float64       `json:"success_rate"`
}

// CircuitBreaker 区域熔断管理器
type CircuitBreaker struct {
	mu               sync.RWMutex
	regions          map[string]*RegionCircuit
	stateThreshold   float64 // 成功率低于此值触发熔断
	openDuration     time.Duration
	halfOpenMax      int     // 半开状态最大尝试次数
	halfOpenWindow   time.Duration
}

// CircuitBreakerConfig 熔断器配置
type CircuitBreakerConfig struct {
	// 成功率阈值 (0-1)，低于此值触发熔断
	SuccessThreshold float64 `json:"success_threshold"`

	// 熔断持续时间，超过后进入半开状态
	OpenDuration time.Duration `json:"open_duration"`

	// 半开状态窗口
	HalfOpenMax      int           `json:"half_open_max"`
	HalfOpenWindow   time.Duration `json:"half_open_window"`
}

// DefaultCircuitBreakerConfig 默认配置
func DefaultCircuitBreakerConfig() CircuitBreakerConfig {
	return CircuitBreakerConfig{
		SuccessThreshold: 0.7, // 70% 成功率
		OpenDuration:     5 * time.Minute,
		HalfOpenMax:      3,
		HalfOpenWindow:   2 * time.Minute,
	}
}

// NewCircuitBreaker 创建新的熔断器
func NewCircuitBreaker(config CircuitBreakerConfig) *CircuitBreaker {
	if config.SuccessThreshold == 0 {
		config.SuccessThreshold = DefaultCircuitBreakerConfig().SuccessThreshold
	}
	if config.OpenDuration == 0 {
		config.OpenDuration = DefaultCircuitBreakerConfig().OpenDuration
	}

	return &CircuitBreaker{
		regions:          make(map[string]*RegionCircuit),
		stateThreshold:   config.SuccessThreshold,
		openDuration:     config.OpenDuration,
		halfOpenMax:      config.HalfOpenMax,
		halfOpenWindow:   config.HalfOpenWindow,
	}
}

// EnsureRegion 确保区域已初始化
func (cb *CircuitBreaker) EnsureRegion(region string) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	if _, exists := cb.regions[region]; !exists {
		cb.regions[region] = &RegionCircuit{
			Region:  region,
			State:   CircuitClosed,
		}
	}
}

// RecordSuccess 记录成功任务
func (cb *CircuitBreaker) RecordSuccess(region string) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	circuit, exists := cb.regions[region]
	if !exists {
		cb.regions[region] = &RegionCircuit{
			Region:  region,
			State:   CircuitClosed,
		}
		return
	}

	circuit.TotalAttempts++
	circuit.SuccessCount++

	if circuit.State == CircuitHalfOpen {
		circuit.SuccessRate = float64(circuit.SuccessCount) / float64(circuit.TotalAttempts)
		if circuit.SuccessCount >= cb.halfOpenMax {
			// 半开成功，恢复正常
			cb.recoverRegion(circuit)
		}
	} else if circuit.State == CircuitClosed {
		circuit.SuccessRate = float64(circuit.SuccessCount) / float64(circuit.TotalAttempts)
	}
}

// RecordFailure 记录失败任务
func (cb *CircuitBreaker) RecordFailure(region string) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	circuit, exists := cb.regions[region]
	if !exists {
		cb.regions[region] = &RegionCircuit{
			Region:        region,
			State:         CircuitClosed,
			TotalAttempts: 1,
			FailureCount:  1,
			SuccessRate:   0,
		}
		return
	}

	// 先检查状态转换 (open -> half-open)
	if circuit.State == CircuitOpen && time.Since(circuit.OpenSince) >= cb.openDuration {
		cb.halfOpenRegion(circuit)
	}

	circuit.TotalAttempts++
	circuit.FailureCount++
	circuit.LastFailure = time.Now()

	circuit.SuccessRate = float64(circuit.SuccessCount) / float64(circuit.TotalAttempts)

	// 半开状态下失败次数达到上限，重新熔断
	if circuit.State == CircuitHalfOpen && circuit.FailureCount >= cb.halfOpenMax {
		cb.openRegion(circuit)
		return
	}

	// 检查是否触发熔断
	if circuit.SuccessRate < cb.stateThreshold && circuit.State == CircuitClosed {
		cb.openRegion(circuit)
	}
}

// CheckRegion 检查区域状态
func (cb *CircuitBreaker) CheckRegion(region string) (CircuitState, error) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	circuit, exists := cb.regions[region]
	if !exists {
		return CircuitClosed, nil
	}

	// 检查是否需要从熔断恢复到半开
	if circuit.State == CircuitOpen {
		if time.Since(circuit.OpenSince) >= cb.openDuration {
			cb.halfOpenRegion(circuit)
			return CircuitHalfOpen, nil
		}
		return CircuitOpen, nil
	}

	// 半开状态检查
	if circuit.State == CircuitHalfOpen {
		if circuit.TotalAttempts >= cb.halfOpenMax {
			if circuit.SuccessRate < cb.stateThreshold {
				// 半开失败，重新熔断
				cb.openRegion(circuit)
				return CircuitOpen, nil
			} else {
				// 半开成功，恢复正常
				cb.recoverRegion(circuit)
				return CircuitClosed, nil
			}
		}
	}

	return circuit.State, nil
}

// IsOpen 检查区域是否熔断
func (cb *CircuitBreaker) IsOpen(region string) bool {
	state, _ := cb.CheckRegion(region)
	return state == CircuitOpen
}

// ForceOpen 强制熔断区域
func (cb *CircuitBreaker) ForceOpen(region string) {
	cb.EnsureRegion(region)
	cb.mu.Lock()
	defer cb.mu.Unlock()

	circuit := cb.regions[region]
	cb.openRegion(circuit)
}

// ForceClose 强制关闭区域熔断
func (cb *CircuitBreaker) ForceClose(region string) {
	cb.EnsureRegion(region)
	cb.mu.Lock()
	defer cb.mu.Unlock()

	circuit := cb.regions[region]
	cb.recoverRegion(circuit)
}

// ResetRegion 重置区域熔断状态
func (cb *CircuitBreaker) ResetRegion(region string) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	if circuit, exists := cb.regions[region]; exists {
		circuit.State = CircuitClosed
		circuit.SuccessCount = 0
		circuit.FailureCount = 0
		circuit.TotalAttempts = 0
		circuit.SuccessRate = 1.0
	}
}

// GetAllCircuits 获取所有熔断器状态
func (cb *CircuitBreaker) GetAllCircuits() map[string]*RegionCircuit {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	result := make(map[string]*RegionCircuit)
	for k, v := range cb.regions {
		circuit := *v
		result[k] = &circuit
	}
	return result
}

// GetStats 获取熔断器统计
func (cb *CircuitBreaker) GetStats() map[string]interface{} {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	openCount := 0
	halfOpenCount := 0
	closedCount := 0

	for _, circuit := range cb.regions {
		switch circuit.State {
		case CircuitOpen:
			openCount++
		case CircuitHalfOpen:
			halfOpenCount++
		case CircuitClosed:
			closedCount++
		}
	}

	return map[string]interface{}{
		"total_regions":     len(cb.regions),
		"open_regions":      openCount,
		"half_open_regions": halfOpenCount,
		"closed_regions":    closedCount,
		"success_threshold": cb.stateThreshold,
	}
}

// ====== 内部方法 ======

func (cb *CircuitBreaker) openRegion(circuit *RegionCircuit) {
	circuit.State = CircuitOpen
	circuit.OpenSince = time.Now()
}

func (cb *CircuitBreaker) halfOpenRegion(circuit *RegionCircuit) {
	circuit.State = CircuitHalfOpen
	circuit.SuccessCount = 0
	circuit.FailureCount = 0
	circuit.TotalAttempts = 0
}

func (cb *CircuitBreaker) recoverRegion(circuit *RegionCircuit) {
	circuit.State = CircuitClosed
	circuit.SuccessRate = 1.0
	circuit.LastRecovery = time.Now()
}

// ====== 与调度器集成 ======

// ScheduledTask 带熔断感知的调度结果
type ScheduledTask struct {
	TaskID       string
	NodeID       string
	Region       string
	AssignedAt   time.Time
	State        CircuitState
	RetryCount   int
	MaxRetries   int
}

// TrackTaskResult 记录任务结果并更新熔断状态
func (cb *CircuitBreaker) TrackTaskResult(task *ScheduledTask, success bool) {
	if success {
		cb.RecordSuccess(task.Region)
	} else {
		cb.RecordFailure(task.Region)
		task.RetryCount++

		// 检查是否可以重试
		if task.RetryCount >= task.MaxRetries {
			// 达到最大重试，标记为永久失败
			return
		}

		// 如果区域熔断，不能重试
		if cb.IsOpen(task.Region) {
			fmt.Printf("[CircuitBreaker] Region %s is circuit broken, task %s cannot retry\n",
				task.Region, task.TaskID)
		}
	}
}

// RetryTask 重试任务 (切换到可用区域)
func (cb *CircuitBreaker) RetryTask(task *ScheduledTask, availableRegions []string) *ScheduledTask {
	// 跳过熔断区域
	for _, region := range availableRegions {
		if !cb.IsOpen(region) {
			task.Region = region
			task.RetryCount = 0
			return task
		}
	}
	return nil // 没有可用区域
}
