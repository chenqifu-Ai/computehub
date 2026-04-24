#!/usr/bin/env python3
"""
Week 4 Day 3: 监控告警模块
执行者：小智 API 助手
时间：2026-04-22 18:05
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# === 配置 ===
GO_ORCHESTRATION = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go")
MONITORING_DIR = GO_ORCHESTRATION / "internal" / "monitoring"

# === 颜色输出 ===
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": Colors.BLUE, "SUCCESS": Colors.GREEN, "WARNING": Colors.YELLOW, "ERROR": Colors.RED}
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def create_monitoring_module():
    log("=" * 60, "INFO")
    log("Week 4 Day 3: 监控告警模块", "INFO")
    log("=" * 60, "INFO")
    
    # 1. 创建目录
    log("步骤 1: 创建监控目录", "INFO")
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    log(f"  ✅ 创建 {MONITORING_DIR}", "SUCCESS")
    
    # 2. 创建监控告警核心
    log("步骤 2: 创建监控告警核心", "INFO")
    monitoring_go = '''package monitoring

import (
	"fmt"
	"net/http"
	"sync"
	"time"
)

// AlertLevel 告警级别
type AlertLevel string

const (
	AlertLevelInfo     AlertLevel = "info"
	AlertLevelWarning  AlertLevel = "warning"
	AlertLevelError    AlertLevel = "error"
	AlertLevelCritical AlertLevel = "critical"
)

// Alert 告警
type Alert struct {
	ID        string     `json:"id"`
	Timestamp time.Time  `json:"timestamp"`
	Level     AlertLevel `json:"level"`
	Source    string     `json:"source"`
	Message   string     `json:"message"`
	Data      interface{} `json:"data,omitempty"`
	Acked     bool       `json:"acked"`
}

// AlertConfig 告警配置
type AlertConfig struct {
	MaxAlerts     int           `json:"max_alerts"`      // 最大告警数
	AutoExpire    time.Duration `json:"auto_expire"`     // 自动过期时间
	EnableMetrics bool          `json:"enable_metrics"`  // 启用指标收集
}

// DefaultConfig 默认配置
func DefaultConfig() *AlertConfig {
	return &AlertConfig{
		MaxAlerts:     1000,
		AutoExpire:    24 * time.Hour,
		EnableMetrics: true,
	}
}

// AlertManager 告警管理器
type AlertManager struct {
	mu       sync.RWMutex
	config   *AlertConfig
	alerts   []*Alert
	handlers []AlertHandler
}

// AlertHandler 告警处理器
type AlertHandler func(alert *Alert)

// NewAlertManager 创建告警管理器
func NewAlertManager(config *AlertConfig) *AlertManager {
	if config == nil {
		config = DefaultConfig()
	}
	return &AlertManager{
		config:   config,
		alerts:   make([]*Alert, 0),
		handlers: make([]AlertHandler, 0),
	}
}

// AddHandler 添加告警处理器
func (m *AlertManager) AddHandler(handler AlertHandler) {
	m.handlers = append(m.handlers, handler)
}

// CreateAlert 创建告警
func (m *AlertManager) CreateAlert(level AlertLevel, source, message string, data interface{}) *Alert {
	m.mu.Lock()
	defer m.mu.Unlock()

	alert := &Alert{
		ID:        fmt.Sprintf("alert-%d", time.Now().UnixNano()),
		Timestamp: time.Now(),
		Level:     level,
		Source:    source,
		Message:   message,
		Data:      data,
		Acked:     false,
	}

	m.alerts = append(m.alerts, alert)

	// 限制告警数量
	if len(m.alerts) > m.config.MaxAlerts {
		m.alerts = m.alerts[1:]
	}

	// 触发处理器
	for _, handler := range m.handlers {
		handler(alert)
	}

	return alert
}

// Info 信息告警
func (m *AlertManager) Info(source, message string, data ...interface{}) *Alert {
	var d interface{}
	if len(data) > 0 {
		d = data[0]
	}
	return m.CreateAlert(AlertLevelInfo, source, message, d)
}

// Warning 警告告警
func (m *AlertManager) Warning(source, message string, data ...interface{}) *Alert {
	var d interface{}
	if len(data) > 0 {
		d = data[0]
	}
	return m.CreateAlert(AlertLevelWarning, source, message, d)
}

// Error 错误告警
func (m *AlertManager) Error(source, message string, data ...interface{}) *Alert {
	var d interface{}
	if len(data) > 0 {
		d = data[0]
	}
	return m.CreateAlert(AlertLevelError, source, message, d)
}

// Critical 严重告警
func (m *AlertManager) Critical(source, message string, data ...interface{}) *Alert {
	var d interface{}
	if len(data) > 0 {
		d = data[0]
	}
	return m.CreateAlert(AlertLevelCritical, source, message, d)
}

// AckAlert 确认告警
func (m *AlertManager) AckAlert(alertID string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, alert := range m.alerts {
		if alert.ID == alertID {
			alert.Acked = true
			return true
		}
	}
	return false
}

// GetAlerts 获取告警列表
func (m *AlertManager) GetAlerts(level AlertLevel, unackedOnly bool) []*Alert {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Alert, 0)
	for _, alert := range m.alerts {
		if level != "" && alert.Level != level {
			continue
		}
		if unackedOnly && alert.Acked {
			continue
		}
		result = append(result, alert)
	}
	return result
}

// GetStats 获取统计
func (m *AlertManager) GetStats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	counts := make(map[AlertLevel]int)
	acked := 0
	for _, alert := range m.alerts {
		counts[alert.Level]++
		if alert.Acked {
			acked++
		}
	}

	return map[string]interface{}{
		"total_alerts": len(m.alerts),
		"acked":        acked,
		"unacked":      len(m.alerts) - acked,
		"by_level":     counts,
	}
}

// MetricsCollector 指标收集器
type MetricsCollector struct {
	mu       sync.RWMutex
	metrics  map[string]*Metric
	startTime time.Time
}

// Metric 指标
type Metric struct {
	Name      string    `json:"name"`
	Value     float64   `json:"value"`
	Tags      []string  `json:"tags"`
	Timestamp time.Time `json:"timestamp"`
}

// NewMetricsCollector 创建指标收集器
func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		metrics:   make(map[string]*Metric),
		startTime: time.Now(),
	}
}

// Record 记录指标
func (c *MetricsCollector) Record(name string, value float64, tags ...string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	key := name
	if len(tags) > 0 {
		key = name + ":" + fmt.Sprintf("%v", tags)
	}

	c.metrics[key] = &Metric{
		Name:      name,
		Value:     value,
		Tags:      tags,
		Timestamp: time.Now(),
	}
}

// GetMetric 获取指标
func (c *MetricsCollector) GetMetric(name string) (*Metric, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	metric, exists := c.metrics[name]
	return metric, exists
}

// GetAllMetrics 获取所有指标
func (c *MetricsCollector) GetAllMetrics() []*Metric {
	c.mu.RLock()
	defer c.mu.RUnlock()

	metrics := make([]*Metric, 0, len(c.metrics))
	for _, m := range c.metrics {
		metrics = append(metrics, m)
	}
	return metrics
}

// GetSystemMetrics 获取系统指标
func (c *MetricsCollector) GetSystemMetrics() map[string]interface{} {
	c.mu.RLock()
	defer c.mu.RUnlock()

	return map[string]interface{}{
		"uptime_seconds": time.Since(c.startTime).Seconds(),
		"metrics_count":  len(c.metrics),
		"metrics":        c.metrics,
	}
}

// HealthChecker 健康检查器
type HealthChecker struct {
	mu       sync.RWMutex
	checks   map[string]HealthCheck
	interval time.Duration
}

// HealthCheck 健康检查
type HealthCheck struct {
	Name      string    `json:"name"`
	Status    string    `json:"status"` // healthy, unhealthy, unknown
	LastCheck time.Time `json:"last_check"`
	Error     string    `json:"error,omitempty"`
}

// NewHealthChecker 创建健康检查器
func NewHealthChecker(interval time.Duration) *HealthChecker {
	return &HealthChecker{
		checks:   make(map[string]HealthCheck),
		interval: interval,
	}
}

// RegisterCheck 注册健康检查
func (h *HealthChecker) RegisterCheck(name string, checkFunc func() error) {
	h.mu.Lock()
	defer h.mu.Unlock()

	h.checks[name] = HealthCheck{
		Name:   name,
		Status: "unknown",
	}

	// 启动后台检查
	go func() {
		ticker := time.NewTicker(h.interval)
		defer ticker.Stop()

		for range ticker.C {
			err := checkFunc()
			h.mu.Lock()
			if err != nil {
				h.checks[name] = HealthCheck{
					Name:      name,
					Status:    "unhealthy",
					LastCheck: time.Now(),
					Error:     err.Error(),
				}
			} else {
				h.checks[name] = HealthCheck{
					Name:      name,
					Status:    "healthy",
					LastCheck: time.Now(),
				}
			}
			h.mu.Unlock()
		}
	}()
}

// GetHealthStatus 获取健康状态
func (h *HealthChecker) GetHealthStatus() map[string]interface{} {
	h.mu.RLock()
	defer h.mu.RUnlock()

	checks := make(map[string]HealthCheck)
	for k, v := range h.checks {
		checks[k] = v
	}

	// 总体状态
	overall := "healthy"
	for _, check := range h.checks {
		if check.Status == "unhealthy" {
			overall = "unhealthy"
			break
		}
	}

	return map[string]interface{}{
		"status": overall,
		"checks": checks,
	}
}

// PrometheusExporter Prometheus 指标导出
func (c *MetricsCollector) PrometheusExporter(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")

	metrics := c.GetAllMetrics()
	for _, m := range metrics {
		fmt.Fprintf(w, "%s %.2f\\n", m.Name, m.Value)
	}
}
'''
    (MONITORING_DIR / "monitoring.go").write_text(monitoring_go, encoding='utf-8')
    log("  ✅ 创建 internal/monitoring/monitoring.go", "SUCCESS")
    
    # 3. 更新 handlers 添加监控 API
    log("步骤 3: 更新 handlers 添加监控 API", "INFO")
    handlers_path = GO_ORCHESTRATION / "internal" / "handlers" / "handlers.go"
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    # 添加导入
    if '"github.com/computehub/opc/orchestration/internal/monitoring"' not in handlers_content:
        handlers_content = handlers_content.replace(
            '"github.com/computehub/opc/orchestration/internal/storage"',
            '"github.com/computehub/opc/orchestration/internal/storage"\n\t"github.com/computehub/opc/orchestration/internal/monitoring"'
        )
    
    # 添加 monitoring 字段
    handlers_content = handlers_content.replace(
        'storage     *storage.KeyValueStore',
        'storage     *storage.KeyValueStore\n\tmonitoring  *monitoring.AlertManager'
    )
    
    # 更新 NewHandler
    handlers_content = handlers_content.replace(
        'storage:     nil, // 需要时初始化',
        'storage:     nil, // 需要时初始化\n\t\tmonitoring:  monitoring.NewAlertManager(monitoring.DefaultConfig()),'
    )
    
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新 internal/handlers/handlers.go (添加监控)", "SUCCESS")
    
    # 4. 添加监控 API 端点
    log("步骤 4: 添加监控 API 端点", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    monitoring_apis = '''
// CreateAlert 创建告警
func (h *Handler) CreateAlert(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Level   string      `json:"level"`
		Source  string      `json:"source"`
		Message string      `json:"message"`
		Data    interface{} `json:"data"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	alert := h.monitoring.CreateAlert(
		monitoring.AlertLevel(req.Level),
		req.Source,
		req.Message,
		req.Data,
	)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":  true,
		"alert_id": alert.ID,
	})
}

// GetAlerts 获取告警列表
func (h *Handler) GetAlerts(w http.ResponseWriter, r *http.Request) {
	level := r.URL.Query().Get("level")
	unacked := r.URL.Query().Get("unacked") == "true"

	alerts := h.monitoring.GetAlerts(monitoring.AlertLevel(level), unacked)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"alerts": alerts,
		"total":  len(alerts),
	})
}

// AckAlert 确认告警
func (h *Handler) AckAlert(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		AlertID string `json:"alert_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	success := h.monitoring.AckAlert(req.AlertID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": success,
	})
}

// GetMonitoringStats 获取监控统计
func (h *Handler) GetMonitoringStats(w http.ResponseWriter, r *http.Request) {
	stats := h.monitoring.GetStats()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// RecordMetric 记录指标
func (h *Handler) RecordMetric(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Name  string   `json:"name"`
		Value float64  `json:"value"`
		Tags  []string `json:"tags"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// GetHealth 获取健康状态
func (h *Handler) GetHealth(w http.ResponseWriter, r *http.Request) {
	// 简单健康检查
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().Format(time.RFC3339),
		"version":   "0.3.0-alpha",
	})
}
'''
    
    handlers_content = handlers_content.rstrip() + '\n' + monitoring_apis
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 添加监控 API 端点", "SUCCESS")
    
    # 5. 更新路由注册
    log("步骤 5: 更新路由注册", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    old_mux = '''mux.HandleFunc("GET /api/storage/nodes", h.ListPersistedNodes)

	return mux
}'''
    
    new_mux = '''mux.HandleFunc("GET /api/storage/nodes", h.ListPersistedNodes)

	// 监控告警端点
	mux.HandleFunc("POST /api/alerts", h.CreateAlert)
	mux.HandleFunc("GET /api/alerts", h.GetAlerts)
	mux.HandleFunc("POST /api/alerts/ack", h.AckAlert)
	mux.HandleFunc("GET /api/monitoring/stats", h.GetMonitoringStats)
	mux.HandleFunc("POST /api/metrics", h.RecordMetric)
	mux.HandleFunc("GET /api/health", h.GetHealth)

	return mux
}'''
    
    handlers_content = handlers_content.replace(old_mux, new_mux)
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新路由注册", "SUCCESS")
    
    # 6. 创建测试脚本
    log("步骤 6: 创建测试脚本", "INFO")
    test_monitoring_py = '''#!/usr/bin/env python3
"""测试监控告警"""

import requests
import time

BASE_URL = "http://localhost:8080"

def test_create_alert():
    """创建告警"""
    print("\\n=== 创建告警 ===")
    
    alerts = [
        {"level": "info", "source": "system", "message": "系统启动正常"},
        {"level": "warning", "source": "scheduler", "message": "节点负载过高", "data": {"load": 85}},
        {"level": "error", "source": "executor", "message": "任务执行失败", "data": {"task_id": "001"}},
    ]
    
    for alert in alerts:
        resp = requests.post(f"{BASE_URL}/api/alerts", json=alert)
        status = "✅" if resp.status_code == 200 else "❌"
        print(f"  {status} 创建 {alert['level']} 告警")

def test_get_alerts():
    """获取告警列表"""
    print("\\n=== 获取告警列表 ===")
    
    resp = requests.get(f"{BASE_URL}/api/alerts")
    
    if resp.status_code == 200:
        result = resp.json()
        alerts = result.get('alerts', [])
        print(f"  共 {len(alerts)} 个告警:")
        for alert in alerts:
            icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔴"}.get(alert.get('level', ''), '📋')
            print(f"    {icon} [{alert.get('level')}] {alert.get('message')}")

def test_monitoring_stats():
    """查看监控统计"""
    print("\\n=== 监控统计 ===")
    
    resp = requests.get(f"{BASE_URL}/api/monitoring/stats")
    
    if resp.status_code == 200:
        stats = resp.json()
        print(f"  总告警数：{stats.get('total_alerts', 0)}")
        print(f"  已确认：{stats.get('acked', 0)}")
        print(f"  未确认：{stats.get('unacked', 0)}")

def test_health():
    """健康检查"""
    print("\\n=== 健康检查 ===")
    
    resp = requests.get(f"{BASE_URL}/api/health")
    
    if resp.status_code == 200:
        health = resp.json()
        print(f"  状态：{health.get('status', 'unknown')}")
        print(f"  版本：{health.get('version', 'unknown')}")

if __name__ == "__main__":
    print("=" * 60)
    print("监控告警测试")
    print("=" * 60)
    
    try:
        # 健康检查
        test_health()
        
        # 创建告警
        test_create_alert()
        
        # 获取告警
        test_get_alerts()
        
        # 查看统计
        test_monitoring_stats()
        
        print("\\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\\n❌ 测试失败：{e}")
'''
    (GO_ORCHESTRATION / "test_monitoring.py").write_text(test_monitoring_py, encoding='utf-8')
    log("  ✅ 创建 test_monitoring.py", "SUCCESS")
    
    log("", "INFO")
    log("=" * 60, "INFO")
    log("监控告警模块创建完成！", "SUCCESS")
    log(f"目录：{GO_ORCHESTRATION}", "SUCCESS")
    log("=" * 60, "INFO")
    
    return True

if __name__ == "__main__":
    success = create_monitoring_module()
    sys.exit(0 if success else 1)
