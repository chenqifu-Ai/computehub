// Package visualizer — Phase 4 可视化层
//
// 可视化网关：将全局算力分布、GPU 实时监控、节点发现数据
// 通过 REST API + WebSocket 推送给前端可视化面板。
//
// API 端点:
//   GET  /api/v2/map/global        → 全球算力地图
//   GET  /api/v2/map/region/:name   → 区域详情
//   GET  /api/v2/gpu/realtime       → GPU 实时看板
//   GET  /api/v2/gpu/radar          → GPU 状态雷达图
//   GET  /api/v2/nodes              → 节点列表 + 发现雷达
//   GET  /api/v2/alerts             → 告警列表
//   GET  /api/v2/history            → 历史趋势
//   GET  /api/v2/health             → 系统健康
//   WS   /ws/visual                 → WebSocket 实时推送
package visualizer

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

// ====== 可视化网关 ======

// VisualizerGateway 可视化网关 — 聚合 + 推送
type VisualizerGateway struct {
	// 核心聚合器
	gpm *GlobalPowerMap

	// 模拟数据开关
	simulate bool

	// 模拟数据生成定时器
	simTick *time.Ticker

	// 模拟数据推送定时器
	simPush *time.Ticker

	// 子图锁 (防止同时写入)
	subLock sync.Mutex

	// 子图序列号
	subSeq int
}

// NewVisualizerGateway 创建可视化网关
func NewVisualizerGateway(gpm *GlobalPowerMap, simulate bool) *VisualizerGateway {
	vg := &VisualizerGateway{
		gpm:      gpm,
		simulate: simulate,
		subSeq:   0,
	}

	if simulate {
		// 生成模拟数据
		gpm.GenerateSimulationData()
	}

	return vg
}

// ServeHTTP 实现 http.Handler — 所有可视化 API 路由
func (vg *VisualizerGateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	switch path {
	case "/api/v2/map/global":
		vg.handleGlobalMap(w, r)
	case "/api/v2/map/region":
		vg.handleRegionMap(w, r)
	case "/api/v2/gpu/realtime":
		vg.handleGPURealtime(w, r)
	case "/api/v2/gpu/radar":
		vg.handleGPURadar(w, r)
	case "/api/v2/nodes":
		vg.handleNodes(w, r)
	case "/api/v2/alerts":
		vg.handleAlerts(w, r)
	case "/api/v2/history":
		vg.handleHistory(w, r)
	case "/api/v2/health":
		vg.handleHealth(w, r)
	case "/ws/visual":
		vg.handleWebSocket(w, r)
	default:
		http.NotFound(w, r)
	}
}

// ====== 路由处理函数 ======

// handleGlobalMap 全球算力地图
func (vg *VisualizerGateway) handleGlobalMap(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	regions := vg.gpm.GetAllRegions()
	snapshot := vg.gpm.GetGlobalSnapshot()

	// 计算总 GPU 数
	totalGPUs := 0
	for _, rd := range regions {
		totalGPUs += rd.TotalGPUs
	}

	data := map[string]interface{}{
		"timestamp":     time.Now().Format(time.RFC3339),
		"total_regions": len(regions),
		"total_nodes":   snapshot.TotalNodes,
		"online_nodes":  snapshot.OnlineNodes,
		"total_gpus":    totalGPUs,
		"total_tflops":  snapshot.TotalTFLOPS,
		"avg_gpu_util":  snapshot.AvgGPUUtil,
		"active_tasks":  snapshot.ActiveTasks,
		"regions":       regions,
	}

	vg.sendJSON(w, data)
}

// handleRegionMap 区域地图详情
func (vg *VisualizerGateway) handleRegionMap(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	region := strings.TrimPrefix(r.URL.Path, "/api/v2/map/region")
	if region == "" || region == "/" {
		http.Error(w, "region name required", http.StatusBadRequest)
		return
	}
	region = strings.TrimLeft(region, "/")

	rd := vg.gpm.GetRegionData(region)
	if rd == nil {
		http.Error(w, "region not found", http.StatusNotFound)
		return
	}

	vg.sendJSON(w, rd)
}

// handleGPURealtime GPU 实时监控
func (vg *VisualizerGateway) handleGPURealtime(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	// 获取所有 GPU 实时数据
	snapshots := vg.gpm.GetGPURadars(200)

	// 如果模拟模式且没有数据，用模拟数据
	if len(snapshots) == 0 && vg.simulate {
		snapshots = vg.generateSimGPUSnapshots()
	}

	vg.sendJSON(w, map[string]interface{}{
		"timestamp":  time.Now().Format(time.RFC3339),
		"total_gpus": len(snapshots),
		"hot_gpus":   vg.countHotGPUs(snapshots),
		"cold_gpus":  vg.countColdGPUs(snapshots),
		"batches":    vg.batchByUtilization(snapshots),
		"gpus":       snapshots,
	})
}

// handleGPURadar GPU 雷达图
func (vg *VisualizerGateway) handleGPURadar(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	data := vg.gpm.GetGlobalSnapshot()

	vg.sendJSON(w, map[string]interface{}{
		"timestamp":  time.Now().Format(time.RFC3339),
		"total_gpus": data.TotalGPUs,
		"utilization_distribution": map[string]interface{}{
			"hot":     vg.countHotGPUs(nil),
			"normal":  0,
			"cold":    vg.countColdGPUs(nil),
			"offline": 0,
		},
		"temperature_distribution": map[string]interface{}{
			"normal":   0,
			"warning":  0,
			"critical": 0,
		},
		"memory_distribution": map[string]interface{}{
			"used_gb":  data.MemoryUsedGB,
			"total_gb": data.TotalTFLOPS / 15, // 估算
		},
	})
}

// handleNodes 节点列表
func (vg *VisualizerGateway) handleNodes(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	regions := vg.gpm.GetAllRegions()
	nodes := make([]NodeVisual, 0)
	totalNodes := 0
	onlineNodes := 0

	for _, rd := range regions {
		nodes = append(nodes, rd.Nodes...)
		totalNodes += rd.TotalNodes
		onlineNodes += rd.OnlineNodes
	}

	vg.sendJSON(w, map[string]interface{}{
		"timestamp":    time.Now().Format(time.RFC3339),
		"total_nodes":  totalNodes,
		"online_nodes": onlineNodes,
		"offline_nodes": totalNodes - onlineNodes,
		"regions":      len(regions),
		"nodes":        nodes,
	})
}

// handleAlerts 告警列表
func (vg *VisualizerGateway) handleAlerts(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	alerts := make([]Alert, 0)
	regions := vg.gpm.GetAllRegions()

	for _, rd := range regions {
		alerts = append(alerts, rd.Alerts...)
	}

	// 按严重性排序
	vg.sortAlerts(alerts)

	vg.sendJSON(w, map[string]interface{}{
		"timestamp": time.Now().Format(time.RFC3339),
		"total":     len(alerts),
		"critical":  vg.countAlertsBySeverity(alerts, "critical"),
		"warning":   vg.countAlertsBySeverity(alerts, "warning"),
		"info":      vg.countAlertsBySeverity(alerts, "info"),
		"alerts":    alerts,
	})
}

// handleHistory 历史趋势
func (vg *VisualizerGateway) handleHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	limit := 100
	if v := r.URL.Query().Get("limit"); v != "" {
		fmt.Sscanf(v, "%d", &limit)
	}

	snapshot := vg.gpm.GetGlobalSnapshot()

	vg.sendJSON(w, map[string]interface{}{
		"timestamp": time.Now().Format(time.RFC3339),
		"history":   []*MetricsSnapshot{snapshot},
	})
}

// handleHealth 系统健康
func (vg *VisualizerGateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	snapshot := vg.gpm.GetGlobalSnapshot()
	regions := vg.gpm.GetAllRegions()

	healthyRegions := 0
	degradedRegions := 0

	for _, rd := range regions {
		if len(rd.Alerts) == 0 {
			healthyRegions++
		} else {
			degradedRegions++
		}
	}

	vg.sendJSON(w, map[string]interface{}{
		"timestamp":          time.Now().Format(time.RFC3339),
		"total_nodes":        snapshot.TotalNodes,
		"online_nodes":       snapshot.OnlineNodes,
		"total_gpus":         snapshot.TotalGPUs,
		"total_tflops":       snapshot.TotalTFLOPS,
		"healthy_regions":    healthyRegions,
		"degraded_regions":   degradedRegions,
		"total_alerts":       len(regions),
		"status":             "healthy",
		"visualization":      map[string]string{
			"global_map":     "/api/v2/map/global",
			"gpu_realtime":   "/api/v2/gpu/realtime",
			"nodes":          "/api/v2/nodes",
			"websocket":      "/ws/visual",
		},
	})
}

// handleWebSocket WebSocket 实时推送
func (vg *VisualizerGateway) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	// 检查 WebSocket 升级请求
	if !strings.Contains(r.Header.Get("Upgrade"), "websocket") {
		http.Error(w, "WebSocket upgrade required", http.StatusBadRequest)
		return
	}

	// 生成订阅 ID
	vg.subLock.Lock()
	vg.subSeq++
	subID := fmt.Sprintf("ws_%d", vg.subSeq)
	vg.subLock.Unlock()

	// 注册订阅者
	sub := vg.gpm.Subscribe(subID, "")
	defer vg.gpm.Unsubscribe(subID)

	// 发送初始数据
	snapshot := vg.gpm.GetGlobalSnapshot()
	initialData, _ := json.Marshal(map[string]interface{}{
		"type":       "init",
		"data":       snapshot,
		"timestamp":  time.Now().Format(time.RFC3339),
		"subscribed": subID,
	})
	sub.Chan <- initialData

	// 持续推送
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-r.Context().Done():
			log.Printf("[Visualizer] WebSocket %s closed", subID)
			return
		case <-ticker.C:
			snapshot := vg.gpm.GetGlobalSnapshot()
			payload, _ := json.Marshal(map[string]interface{}{
				"type":      "update",
				"data":      snapshot,
				"timestamp": time.Now().Format(time.RFC3339),
			})
			sub.Chan <- payload
		}
	}
}

// ====== 工具函数 ======

func (vg *VisualizerGateway) sendJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-cache")
	json.NewEncoder(w).Encode(data)
}

func (vg *VisualizerGateway) sortAlerts(alerts []Alert) {
	for i := 0; i < len(alerts); i++ {
		for j := i + 1; j < len(alerts); j++ {
			if alertSeverity(alerts[i].Severity) < alertSeverity(alerts[j].Severity) {
				alerts[i], alerts[j] = alerts[j], alerts[i]
			}
		}
	}
}

func alertSeverity(s string) int {
	switch s {
	case "critical":
		return 3
	case "warning":
		return 2
	case "info":
		return 1
	default:
		return 0
	}
}

func (vg *VisualizerGateway) countAlertsBySeverity(alerts []Alert, severity string) int {
	count := 0
	for _, a := range alerts {
		if a.Severity == severity {
			count++
		}
	}
	return count
}

func (vg *VisualizerGateway) countHotGPUs(snapshots []*GPUSnapshot) int {
	count := 0
	for _, s := range snapshots {
		if s.Utilization > 80 {
			count++
		}
	}
	return count
}

func (vg *VisualizerGateway) countColdGPUs(snapshots []*GPUSnapshot) int {
	count := 0
	for _, s := range snapshots {
		if s.Utilization < 10 {
			count++
		}
	}
	return count
}

func (vg *VisualizerGateway) batchByUtilization(snapshots []*GPUSnapshot) map[string]int {
	batches := map[string]int{
		"0-20":  0,
		"20-40": 0,
		"40-60": 0,
		"60-80": 0,
		"80-100": 0,
	}
	for _, s := range snapshots {
		if s.Utilization <= 20 {
			batches["0-20"]++
		} else if s.Utilization <= 40 {
			batches["20-40"]++
		} else if s.Utilization <= 60 {
			batches["40-60"]++
		} else if s.Utilization <= 80 {
			batches["60-80"]++
		} else {
			batches["80-100"]++
		}
	}
	return batches
}

func (vg *VisualizerGateway) generateSimGPUSnapshots() []*GPUSnapshot {
	count := 50 + vg.gpm.rng.Intn(100)
	result := make([]*GPUSnapshot, count)
	for i := 0; i < count; i++ {
		result[i] = &GPUSnapshot{
			NodeID:      fmt.Sprintf("sim_node_%d", i),
			GPUID:       fmt.Sprintf("sim_gpu_%d", i),
			Model:       []string{"A100", "H100", "V100", "RTX4090"}[vg.gpm.rng.Intn(4)],
			Utilization: float64(vg.gpm.rng.Intn(100)),
			Temperature: float64(40 + vg.gpm.rng.Intn(50)),
			MemoryUsed:  float64(10 + vg.gpm.rng.Intn(50)),
			Timestamp:   time.Now(),
		}
	}
	return result
}

// ====== 启动服务 ======

// Start 启动可视化网关
func (vg *VisualizerGateway) Start(port int) {
	// 注册路由
	http.Handle("/api/v2/", vg)
	http.Handle("/ws/visual", vg)

	log.Printf("[Visualizer] Visualization gateway listening on :%d", port)

	// 如果是模拟模式，启动模拟数据生成器
	if vg.simulate {
		go func() {
			ticker := time.NewTicker(5 * time.Second)
			defer ticker.Stop()
			for {
				<-ticker.C
				// 生成新模拟数据
				snapshot := vg.gpm.GetGlobalSnapshot()
				payload, _ := json.Marshal(map[string]interface{}{
					"type":      "sim_update",
					"data":      snapshot,
					"timestamp": time.Now().Format(time.RFC3339),
				})
				vg.gpm.Broadcast(payload)
			}
		}()
	}

	// 启动 HTTP 服务
	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), nil); err != nil {
		log.Printf("[Visualizer] Fatal error: %v", err)
	}
}
