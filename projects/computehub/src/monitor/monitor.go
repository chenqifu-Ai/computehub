package monitor

import (
	"fmt"
	"math"
	"sync"
	"time"
)

// ====== 硬件指标 ======

type GPUMetrics struct {
	DeviceID     string    `json:"device_id"`
	Model        string    `json:"model"`
	Utilization  float64   `json:"utilization"` // 0-100
	Temperature  float64   `json:"temperature"` // Celsius
	MemoryUsedMB float64   `json:"memory_used_mb"`
	MemoryTotalMB float64  `json:"memory_total_mb"`
	PowerWatts   float64   `json:"power_watts"`
	PCIeBandwidth float64  `json:"pcie_bandwidth"` // GB/s
	GPUVoltage   float64   `json:"gpu_voltage"`    // Volts
	 FanSpeed    float64   `json:"fan_speed"`      // RPM or percentage
	 MeasuredAt  time.Time `json:"measured_at"`
}

type CPUMetrics struct {
	Cores        int       `json:"cores"`
	Utilization  float64   `json:"utilization"` // 0-100 per core average
	LoadAverage1 float64   `json:"load_avg_1"`  // 1 minute
	LoadAverage5 float64   `json:"load_avg_5"`  // 5 minutes
	LoadAverage15 float64  `json:"load_avg_15"` // 15 minutes
	Temperature  float64   `json:"temperature"` // Celsius (all cores avg)
	MeasuredAt   time.Time `json:"measured_at"`
}

type DiskMetrics struct {
	Device     string    `json:"device"`
	TotalGB    float64   `json:"total_gb"`
	UsedGB     float64   `json:"used_gb"`
	ReadSpeed  float64   `json:"read_speed_mbps"` // MB/s
	WriteSpeed float64   `json:"write_speed_mbps"` // MB/s
	IOUtil     float64   `json:"io_utilization"` // 0-100
	MeasuredAt time.Time `json:"measured_at"`
}

type NetworkMetrics struct {
	Interface   string    `json:"interface"`
	BytesSent   float64   `json:"bytes_sent"` // MB
	BytesRecv   float64   `json:"bytes_recv"` // MB
	ThroughputUp float64  `json:"throughput_up_mbps"` // Mbps
	ThroughputDown float64 `json:"throughput_down_mbps"` // Mbps
	PacketLoss   float64   `json:"packet_loss"` // percentage
	PingMS       float64   `json:"ping_ms"` // latency to gateway
	MeasuredAt   time.Time `json:"measured_at"`
}

type SystemMetrics struct {
	Hostname   string        `json:"hostname"`
	OS         string        `json:"os"`
	Uptime     string        `json:"uptime"`
	MemUsedGB  float64       `json:"mem_used_gb"`
	MemTotalGB float64       `json:"mem_total_gb"`
	SwapUsedGB float64       `json:"swap_used_gb"`
	SwapTotalGB float64      `json:"swap_total_gb"`
	GPU        []GPUMetrics  `json:"gpu"`
	CPU        CPUMetrics    `json:"cpu"`
	Disk       []DiskMetrics `json:"disk"`
	Network    []NetworkMetrics `json:"network"`
	MeasuredAt time.Time     `json:"measured_at"`
}

// ====== 监控器配置 ======

type MonitorConfig struct {
	// 采集间隔
	CollectionInterval int `json:"collection_interval"` // seconds, default 30

	// 告警阈值
	TemperatureWarning float64 `json:"temperature_warning"` // Celsius, default 80
	TemperatureCritical float64 `json:"temperature_critical"` // Celsius, default 95
	GPUUtilWarning    float64 `json:"gpu_util_warning"` // 0-100, default 95
	MemoryWarning     float64 `json:"memory_warning"` // GB, default 60

	// 心跳配置
	HeartbeatInterval int `json:"heartbeat_interval"` // seconds, default 10

	// 指标保留时间
	HistoryRetention int `json:"history_retention"` // hours, default 24
}

func DefaultMonitorConfig() MonitorConfig {
	return MonitorConfig{
		CollectionInterval:  30,
		TemperatureWarning:  80.0,
		TemperatureCritical: 95.0,
		GPUUtilWarning:      95.0,
		MemoryWarning:       60.0,
		HeartbeatInterval:   10,
		HistoryRetention:    24,
	}
}

// ====== 告警 ======

type AlertLevel int

const (
	AlertInfo AlertLevel = iota
	AlertWarning
	AlertCritical
	AlertResolved
)

func (a AlertLevel) String() string {
	switch a {
	case AlertInfo:
		return "INFO"
	case AlertWarning:
		return "WARNING"
	case AlertCritical:
		return "CRITICAL"
	case AlertResolved:
		return "RESOLVED"
	default:
		return "UNKNOWN"
	}
}

type Alert struct {
	ID        string    `json:"id"`
	Timestamp time.Time `json:"timestamp"`
	Level     AlertLevel `json:"level"`
	Component string    `json:"component"`
	Message   string    `json:"message"`
	Value     float64   `json:"value"`
	Threshold float64   `json:"threshold"`
	NodeID    string    `json:"node_id"`
}

// ====== 物理心跳 ======

type PhysicalHeartbeat struct {
	NodeID      string         `json:"node_id"`
	Timestamp   time.Time      `json:"timestamp"`
	System      SystemMetrics  `json:"system"`
	HealthScore float64        `json:"health_score"` // 0-100
	Status      string         `json:"status"`       // "healthy" | "warning" | "critical" | "offline"
	Alerts      []Alert        `json:"alerts"`
}

// ====== 物理心跳监控系统 ======

type HealthMonitor struct {
	config     MonitorConfig
	mu         sync.RWMutex
	nodeStates map[string]*NodeState
	alerts     []Alert
	maxAlerts  int
}

type NodeState struct {
	NodeID        string        `json:"node_id"`
	LastHeartbeat time.Time     `json:"last_heartbeat"`
	CurrentMetrics SystemMetrics `json:"current_metrics"`
	HealthScore   float64       `json:"health_score"`
	Status        string        `json:"status"`
	AlertHistory  []Alert       `json:"alert_history"`
	MetricsHistory []SystemMetrics `json:"metrics_history"`
}

// NewHealthMonitor 创建新的监控系统
func NewHealthMonitor(config MonitorConfig) *HealthMonitor {
	return &HealthMonitor{
		config:     config,
		nodeStates: make(map[string]*NodeState),
		maxAlerts:  1000,
	}
}

// ====== 核心监控逻辑 ======

// UpdateHeartbeat 接收节点心跳并评估健康度
func (m *HealthMonitor) UpdateHeartbeat(nodeID string, system *SystemMetrics) *PhysicalHeartbeat {
	m.mu.Lock()
	defer m.mu.Unlock()

	// 获取或创建节点状态
	state, exists := m.nodeStates[nodeID]
	if !exists {
		state = &NodeState{
			NodeID:       nodeID,
			AlertHistory: make([]Alert, 0),
		}
		m.nodeStates[nodeID] = state
	}

	// 更新状态
	state.LastHeartbeat = time.Now()
	state.CurrentMetrics = *system

	// 计算健康度
	healthScore := m.calculateHealthScore(system)
	state.HealthScore = healthScore

	// 生成告警
	alerts := m.generateAlerts(nodeID, system)
	state.AlertHistory = append(state.AlertHistory, alerts...)

	// 保留最近告警
	if len(state.AlertHistory) > 50 {
		state.AlertHistory = state.AlertHistory[len(state.AlertHistory)-50:]
	}

	// 记录历史指标
	state.MetricsHistory = append(state.MetricsHistory, *system)
	if len(state.MetricsHistory) > 288 { // 24 hours at 5-min intervals
		state.MetricsHistory = state.MetricsHistory[len(state.MetricsHistory)-288:]
	}

	// 确定状态
	status := "healthy"
	if healthScore < 70 {
		status = "warning"
	}
	if healthScore < 50 {
		status = "critical"
	}

	// 持久化状态到节点
	state.Status = status

	// 保存告警到全局列表
	m.alerts = append(m.alerts, alerts...)
	if len(m.alerts) > m.maxAlerts {
		m.alerts = m.alerts[len(m.alerts)-m.maxAlerts:]
	}

	return &PhysicalHeartbeat{
		NodeID:      nodeID,
		Timestamp:   time.Now(),
		System:      *system,
		HealthScore: healthScore,
		Status:      status,
		Alerts:      alerts,
	}
}

// calculateHealthScore 计算节点健康度评分 (0-100)
func (m *HealthMonitor) calculateHealthScore(system *SystemMetrics) float64 {
	var score float64 = 100.0

	// GPU 温度扣分
	for _, gpu := range system.GPU {
		if gpu.Temperature > m.config.TemperatureCritical {
			// 严重过热：扣 30-40 分
			score -= 30
		} else if gpu.Temperature > m.config.TemperatureWarning {
			// 警告温度：扣 20-25 分（更严厉）
			score -= 25
		}
	}

	// CPU 温度扣分
	if system.CPU.Temperature > m.config.TemperatureCritical {
		score -= 30
	} else if system.CPU.Temperature > m.config.TemperatureWarning {
		score -= 15
	}

	// GPU 利用率过高 + 高温叠加
	for _, gpu := range system.GPU {
		if gpu.Utilization > m.config.GPUUtilWarning && gpu.Temperature > m.config.TemperatureWarning {
			score -= 10 // 高温下高利用率叠加风险
		}
	}

	// 内存使用扣分
	memPercent := (system.MemUsedGB / system.MemTotalGB) * 100
	if memPercent > 95 {
		score -= 20
	} else if memPercent > 90 {
		score -= 12
	} else if memPercent > 85 {
		score -= 8
	}

	// 磁盘 IO 压力
	for _, disk := range system.Disk {
		if disk.IOUtil > 95 {
			score -= 10
		}
	}

	// 网络延迟
	for _, net := range system.Network {
		if net.PingMS > 500 {
			score -= 15
		} else if net.PingMS > 200 {
			score -= 8
		}
		if net.PacketLoss > 5 {
			score -= 15
		} else if net.PacketLoss > 1 {
			score -= 8
		}
	}

	// 确保分数在 0-100 之间
	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}

	return math.Round(score*10) / 10
}

// generateAlerts 根据指标生成告警
func (m *HealthMonitor) generateAlerts(nodeID string, system *SystemMetrics) []Alert {
	var alerts []Alert

	// GPU 温度告警
	for _, gpu := range system.GPU {
		if gpu.Temperature > m.config.TemperatureCritical {
			alerts = append(alerts, Alert{
				ID:        fmt.Sprintf("gpu-temp-critical-%s-%d", nodeID, time.Now().Unix()),
				Timestamp: time.Now(),
				Level:     AlertCritical,
				Component: "gpu",
				Message:   fmt.Sprintf("GPU %s 温度临界: %.1f°C", gpu.Model, gpu.Temperature),
				Value:     gpu.Temperature,
				Threshold: m.config.TemperatureCritical,
				NodeID:    nodeID,
			})
		} else if gpu.Temperature > m.config.TemperatureWarning {
			alerts = append(alerts, Alert{
				ID:        fmt.Sprintf("gpu-temp-warning-%s-%d", nodeID, time.Now().Unix()),
				Timestamp: time.Now(),
				Level:     AlertWarning,
				Component: "gpu",
				Message:   fmt.Sprintf("GPU %s 温度警告: %.1f°C", gpu.Model, gpu.Temperature),
				Value:     gpu.Temperature,
				Threshold: m.config.TemperatureWarning,
				NodeID:    nodeID,
			})
		}
	}

	// CPU 温度告警
	if system.CPU.Temperature > m.config.TemperatureWarning {
		alerts = append(alerts, Alert{
			ID:        fmt.Sprintf("cpu-temp-warning-%s-%d", nodeID, time.Now().Unix()),
			Timestamp: time.Now(),
			Level:     AlertWarning,
			Component: "cpu",
			Message:   fmt.Sprintf("CPU 温度警告: %.1f°C", system.CPU.Temperature),
			Value:     system.CPU.Temperature,
			Threshold: m.config.TemperatureWarning,
			NodeID:    nodeID,
		})
	}

	// 内存告警
	memPercent := (system.MemUsedGB / system.MemTotalGB) * 100
	if memPercent > 95 {
		alerts = append(alerts, Alert{
			ID:        fmt.Sprintf("mem-critical-%s-%d", nodeID, time.Now().Unix()),
			Timestamp: time.Now(),
			Level:     AlertCritical,
			Component: "memory",
			Message:   fmt.Sprintf("内存使用临界: %.1f%% (%.1f/%.1f GB)", memPercent, system.MemUsedGB, system.MemTotalGB),
			Value:     memPercent,
			Threshold: 95.0,
			NodeID:    nodeID,
		})
	}

	// 网络丢包告警
	for _, net := range system.Network {
		if net.PacketLoss > 5 {
			alerts = append(alerts, Alert{
				ID:        fmt.Sprintf("net-packet-loss-%s-%d", nodeID, time.Now().Unix()),
				Timestamp: time.Now(),
				Level:     AlertCritical,
				Component: "network",
				Message:   fmt.Sprintf("网络丢包严重: %.1f%%", net.PacketLoss),
				Value:     net.PacketLoss,
				Threshold: 5.0,
				NodeID:    nodeID,
			})
		} else if net.PacketLoss > 1 {
			alerts = append(alerts, Alert{
				ID:        fmt.Sprintf("net-packet-loss-%s-%d", nodeID, time.Now().Unix()),
				Timestamp: time.Now(),
				Level:     AlertWarning,
				Component: "network",
				Message:   fmt.Sprintf("网络丢包: %.1f%%", net.PacketLoss),
				Value:     net.PacketLoss,
				Threshold: 1.0,
				NodeID:    nodeID,
			})
		}
	}

	return alerts
}

// ====== 查询接口 ======

// GetNodeStatus 获取节点状态
func (m *HealthMonitor) GetNodeStatus(nodeID string) (*NodeState, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	state, exists := m.nodeStates[nodeID]
	if !exists {
		return nil, false
	}

	// 深拷贝
	cp := *state
	cp.AlertHistory = make([]Alert, len(state.AlertHistory))
	copy(cp.AlertHistory, state.AlertHistory)
	cp.MetricsHistory = make([]SystemMetrics, len(state.MetricsHistory))
	copy(cp.MetricsHistory, state.MetricsHistory)

	return &cp, true
}

// GetAllNodes 获取所有节点状态
func (m *HealthMonitor) GetAllNodes() map[string]*NodeState {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make(map[string]*NodeState)
	for id, state := range m.nodeStates {
		cp := *state
		cp.AlertHistory = make([]Alert, len(state.AlertHistory))
		copy(cp.AlertHistory, state.AlertHistory)
		cp.MetricsHistory = make([]SystemMetrics, len(state.MetricsHistory))
		copy(cp.MetricsHistory, state.MetricsHistory)
		result[id] = &cp
	}

	return result
}

// GetRecentAlerts 获取最近告警
func (m *HealthMonitor) GetRecentAlerts(limit int) []Alert {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if limit > len(m.alerts) {
		limit = len(m.alerts)
	}

	result := make([]Alert, limit)
	copy(result, m.alerts[len(m.alerts)-limit:])

	return result
}

// GetAlertsByLevel 按级别获取告警
func (m *HealthMonitor) GetAlertsByLevel(level AlertLevel) []Alert {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var result []Alert
	for _, alert := range m.alerts {
		if alert.Level == level {
			result = append(result, alert)
		}
	}

	return result
}

// ClearAlert 清除指定告警
func (m *HealthMonitor) ClearAlert(alertID string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	for i, alert := range m.alerts {
		if alert.ID == alertID {
			m.alerts = append(m.alerts[:i], m.alerts[i+1:]...)
			break
		}
	}
}

// ====== 统计信息 ======

// GetMonitorStats 获取监控系统统计
func (m *HealthMonitor) GetMonitorStats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	totalNodes := len(m.nodeStates)
	healthyNodes := 0
	warningNodes := 0
	criticalNodes := 0
	offlineNodes := 0

	for _, state := range m.nodeStates {
		switch state.Status {
		case "healthy":
			healthyNodes++
		case "warning":
			warningNodes++
		case "critical":
			criticalNodes++
		}

		// 检查离线
		if time.Since(state.LastHeartbeat).Minutes() > 5 {
			offlineNodes++
		}
	}

	return map[string]interface{}{
		"total_nodes":    totalNodes,
		"healthy_nodes":  healthyNodes,
		"warning_nodes":  warningNodes,
		"critical_nodes": criticalNodes,
		"offline_nodes":  offlineNodes,
		"total_alerts":   len(m.alerts),
	}
}
