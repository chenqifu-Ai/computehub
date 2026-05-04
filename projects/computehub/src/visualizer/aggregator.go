// Package visualizer 提供全局算力分布可视化层。
//
// 整合 scheduler/discover/monitor/health 的底层数据，
// 通过 REST + WebSocket 对外输出可视化所需的全量指标。
//
// Phase 4 - ComputeHub Core
package visualizer

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"net"
	"sync"
	"time"

	"github.com/computehub/opc/src/discover"
	"github.com/computehub/opc/src/health"
	"github.com/computehub/opc/src/monitor"
	"github.com/computehub/opc/src/scheduler"
)

// ====== 全局算力地图数据 ======

// GlobalPowerMap 全局算力地图 — 所有可视化数据的唯一聚合源
type GlobalPowerMap struct {
	mu         sync.RWMutex
	regions    map[string]*RegionData
	totalNodes int
	totalGPUs  int
	totalCPU   int
	totalRAM   float64 // GB

	// 实时 GPU 监控快照
	gpuSnapshots map[string][]*GPUSnapshot
	gpuLock      sync.RWMutex

	// 可视化订阅者
	subscribers map[string]*Subscriber

	// 历史数据 (环形缓冲区)
	metricsHistory []*MetricsSnapshot
	historyMax     int

	// 随机种子用于模拟数据
	rng *rand.Rand

	// 模拟模式 — 用于没有真实节点时的演示
	simulate bool
}

// RegionData 区域数据
type RegionData struct {
	Name         string         `json:"name"`
	Country      string         `json:"country"`
	Lat          float64        `json:"lat"`
	Lng          float64        `json:"lng"`
	TotalNodes   int            `json:"total_nodes"`
	OnlineNodes  int            `json:"online_nodes"`
	TotalGPUs    int            `json:"total_gpus"`
	TotalCPU     int            `json:"total_cpu_cores"`
	TotalRAMGB   float64        `json:"total_ram_gb"`
	TotalTFLOPS  float64        `json:"total_tflops"` // 总算力 TFLOPS
	AvgGPUUtil   float64        `json:"avg_gpu_util"` // 平均 GPU 利用率
	AvgTemp      float64        `json:"avg_temp"`     // 平均温度
	ActiveTasks  int            `json:"active_tasks"`
	TotalTasks   int            `json:"total_tasks"`
	Nodes        []NodeVisual   `json:"nodes"`
	Status       string         `json:"status"` // "healthy" | "degraded" | "critical"
	Alerts       []Alert        `json:"alerts"`
	LastUpdate   time.Time      `json:"last_update"`
}

// NodeVisual 节点可视化数据
type NodeVisual struct {
	ID           string             `json:"id"`
	Region       string             `json:"region"`
	Country      string             `json:"country"`
	IPAddress    string             `json:"ip_address"`
	Status       string             `json:"status"`
	GPUType      string             `json:"gpu_type"`
	GPUs         []GPUInfo          `json:"gpus"`
	CPUCores     int                `json:"cpu_cores"`
	MemoryGB     float64            `json:"memory_gb"`
	Load         float64            `json:"load"` // 0-100
	NetworkLatMS int64              `json:"network_latency_ms"`
	ActiveTasks  int                `json:"active_tasks"`
	MaxTasks     int                `json:"max_tasks"`
	SuccessRate  float64            `json:"success_rate"`
	HealthStatus string             `json:"health_status"` // "healthy" | "degraded" | "unhealthy"
	RegisteredAt string             `json:"registered_at"`
}

// GPUInfo GPU 可视化信息
type GPUInfo struct {
	ID          string  `json:"id"`
	Model       string  `json:"model"`
	Utilization float64 `json:"utilization"` // 0-100
	Temperature float64 `json:"temperature"` // Celsius
	MemoryUsed  float64 `json:"memory_used_gb"`
	MemoryTotal float64 `json:"memory_total_gb"`
	PowerWatts  float64 `json:"power_watts"`
	Status      string  `json:"status"` // "idle" | "busy" | "critical" | "offline"
}

// GPUSnapshot GPU 实时快照
type GPUSnapshot struct {
	NodeID      string    `json:"node_id"`
	GPUID       string    `json:"gpu_id"`
	Model       string    `json:"model"`
	Utilization float64   `json:"utilization"`
	Temperature float64   `json:"temperature"`
	MemoryUsed  float64   `json:"memory_used_gb"`
	Timestamp   time.Time `json:"timestamp"`
}

// MetricsSnapshot 历史指标快照
type MetricsSnapshot struct {
	Timestamp  time.Time                  `json:"timestamp"`
	TotalNodes int                        `json:"total_nodes"`
	OnlineNodes int                       `json:"online_nodes"`
	TotalGPUs  int                        `json:"total_gpus"`
	TotalTFLOPS float64                   `json:"total_tflops"`
	AvgGPUUtil float64                   `json:"avg_gpu_util"`
	ActiveTasks int                      `json:"active_tasks"`
	MemoryUsedGB float64                 `json:"memory_used_gb"`
}

// Alert 告警
type Alert struct {
	ID        string    `json:"alert_id"`
	AlertID   string    `json:"id,omitempty"`  // alias 兼容
	Type      string    `json:"type"`  // "temperature" | "utilization" | "offline" | "failure_rate"
	Severity  string    `json:"severity"` // "info" | "warning" | "critical"
	Message   string    `json:"message"`
	Source    string    `json:"source"`
	NodeID    string    `json:"node_id"`
	Timestamp time.Time `json:"timestamp"`
}

// Subscriber WebSocket 订阅者
type Subscriber struct {
	ID       string
	Chan     chan []byte
	Country  string // 可选：只订阅特定区域
}

// ====== 创建聚合引擎 ======

// NewGlobalPowerMap 创建全局算力地图聚合器
func NewGlobalPowerMap(simulate bool) *GlobalPowerMap {
	if simulate {
		log.Println("[Visualizer] Running in SIMULATION mode")
	}
	return &GlobalPowerMap{
		regions:        make(map[string]*RegionData),
		gpuSnapshots:   make(map[string][]*GPUSnapshot),
		subscribers:    make(map[string]*Subscriber),
		metricsHistory: make([]*MetricsSnapshot, 0, 500),
		historyMax:     500,
		rng:            rand.New(rand.NewSource(time.Now().UnixNano())),
		simulate:       simulate,
	}
}

// ====== 数据注册 ======

// RegisterNode 注册节点数据
func (gpm *GlobalPowerMap) RegisterNode(node *scheduler.NodeInfo) {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	region := node.Region
	if _, exists := gpm.regions[region]; !exists {
		gpm.regions[region] = &RegionData{
			Name:       region,
			Country:    regionToCountry(region),
			Lat:        regionToLat(region),
			Lng:        regionToLng(region),
		}
	}

	rd := gpm.regions[region]
	rd.TotalNodes++
	if node.Status == "online" {
		rd.OnlineNodes++
	}
	rd.Nodes = append(rd.Nodes, nodeToVisual(node))

	gpm.totalNodes++
	gpm.totalGPUs += 8 // 假设每节点 8 卡
	gpm.totalCPU += node.CPUCores
	gpm.totalRAM += node.MemoryGB
}

// RegisterNodeDiscovery 从 node discover 模块注册节点
func (gpm *GlobalPowerMap) RegisterNodeDiscovery(node *discover.NodeInfo) {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	region := node.Region
	if _, exists := gpm.regions[region]; !exists {
		gpm.regions[region] = &RegionData{
			Name:   region,
			Country: regionToCountry(region),
			Lat:    regionToLat(region),
			Lng:    regionToLng(region),
		}
	}

	rd := gpm.regions[region]
	rd.TotalNodes++
	rd.Nodes = append(rd.Nodes, NodeVisual{
		ID:         node.NodeID,
		Region:     node.Region,
		Country:    rd.Country,
		IPAddress:  node.IPAddress,
		Status:     "online",
		GPUType:    node.GPUType,
		CPUCores:   16, // default
		MemoryGB:   64,
		Load:       0,
		RegisteredAt: node.RegisteredAt.Format(time.RFC3339),
	})

	gpm.totalNodes++
	gpm.totalGPUs += 4
}

// RegisterNodeFromKernel 从 kernel 节点管理器注册节点
func (gpm *GlobalPowerMap) RegisterNodeFromKernel(nv *NodeVisual) {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	region := nv.Region
	if _, exists := gpm.regions[region]; !exists {
		gpm.regions[region] = &RegionData{
			Name:    region,
			Country: regionToCountry(region),
			Lat:     regionToLat(region),
			Lng:     regionToLng(region),
		}
	}

	rd := gpm.regions[region]
	rd.TotalNodes++
	if nv.Status == "online" {
		rd.OnlineNodes++
	}

	// Replace existing node if same ID, else append
	found := false
	for i, existing := range rd.Nodes {
		if existing.ID == nv.ID {
			rd.Nodes[i] = *nv
			found = true
			break
		}
	}
	if !found {
		rd.Nodes = append(rd.Nodes, *nv)
	}

	rd.TotalGPUs = 0
	for _, n := range rd.Nodes {
		if n.Status == "online" {
			rd.TotalGPUs += len(n.GPUs)
		}
	}

	// 更新汇总
	gpm.totalNodes = 0
	gpm.totalGPUs = 0
	for _, r := range gpm.regions {
		gpm.totalNodes += r.TotalNodes
		gpm.totalGPUs += r.TotalGPUs
	}
}

// UpdateGPU 更新 GPU 监控数据
func (gpm *GlobalPowerMap) UpdateGPU(snapshot *monitor.GPUMetrics) {
	gpm.gpuLock.Lock()
	defer gpm.gpuLock.Unlock()

	// 更新节点级别的 GPU 快照
	gpuKey := snapshot.DeviceID
	gpm.gpuSnapshots[gpuKey] = append(gpm.gpuSnapshots[gpuKey], &GPUSnapshot{
		NodeID:      "unknown", // 需要从映射中查找
		GPUID:       snapshot.DeviceID,
		Model:       snapshot.Model,
		Utilization: snapshot.Utilization,
		Temperature: snapshot.Temperature,
		MemoryUsed:  snapshot.MemoryUsedMB / 1024,
		Timestamp:   snapshot.MeasuredAt,
	})

	// 限制快照数量
	if len(gpm.gpuSnapshots[gpuKey]) > 100 {
		gpm.gpuSnapshots[gpuKey] = gpm.gpuSnapshots[gpuKey][1:]
	}
}

// UpdateHealth 更新节点健康状态
func (gpm *GlobalPowerMap) UpdateHealth(health *health.NodeHealth) {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	for region := range gpm.regions {
		for i := range gpm.regions[region].Nodes {
			if gpm.regions[region].Nodes[i].ID == health.NodeID {
				gpm.regions[region].Nodes[i].HealthStatus = health.Status
				break
			}
		}
	}
}

// AddAlert 添加告警
func (gpm *GlobalPowerMap) AddAlert(alert Alert) {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	for _, rd := range gpm.regions {
		for _, n := range rd.Nodes {
			if n.ID == alert.Source {
				rd.Alerts = append(rd.Alerts, alert)
				if len(rd.Alerts) > 20 {
					rd.Alerts = rd.Alerts[1:]
				}
				break
			}
		}
	}
}

// ====== 数据查询 ======

// GetGlobalSnapshot 获取全局算力快照
func (gpm *GlobalPowerMap) GetGlobalSnapshot() *MetricsSnapshot {
	gpm.mu.RLock()
	defer gpm.mu.RUnlock()

	totalTFLOPS := 0.0
	totalGPUUtil := 0.0
	regionCount := 0

	for _, rd := range gpm.regions {
		totalTFLOPS += rd.TotalTFLOPS
		totalGPUUtil += rd.AvgGPUUtil
		regionCount++
	}

	return &MetricsSnapshot{
		Timestamp:  time.Now(),
		TotalNodes: gpm.totalNodes,
		OnlineNodes: func() int {
			count := 0
			for _, rd := range gpm.regions {
				count += rd.OnlineNodes
			}
			return count
		}(),
		TotalGPUs:  gpm.totalGPUs,
		TotalTFLOPS: totalTFLOPS,
		AvgGPUUtil: func() float64 {
			if regionCount > 0 {
				return totalGPUUtil / float64(regionCount)
			}
			return 0
		}(),
		ActiveTasks: func() int {
			count := 0
			for _, rd := range gpm.regions {
				count += rd.ActiveTasks
			}
			return count
		}(),
		MemoryUsedGB: gpm.totalRAM * 0.65, // 估算 65% 已使用
	}
}

// GetRegionData 获取指定区域数据
func (gpm *GlobalPowerMap) GetRegionData(region string) *RegionData {
	gpm.mu.RLock()
	defer gpm.mu.RUnlock()

	if rd, exists := gpm.regions[region]; exists {
		// 深拷贝 (注意：make + append 会翻倍，必须用 make([]T, 0, len) 或直接 copy)
		copy := *rd
		copy.Nodes = append([]NodeVisual{}, rd.Nodes...)
		copy.Alerts = append([]Alert{}, rd.Alerts...)
		return &copy
	}
	return nil
}

// GetAllRegions 获取所有区域数据
func (gpm *GlobalPowerMap) GetAllRegions() map[string]*RegionData {
	gpm.mu.RLock()
	defer gpm.mu.RUnlock()

	result := make(map[string]*RegionData)
	for name, rd := range gpm.regions {
		copy := *rd
		copy.Nodes = append([]NodeVisual{}, rd.Nodes...)
		copy.Alerts = append([]Alert{}, rd.Alerts...)
		result[name] = &copy
	}
	return result
}

// GetGPURadars 获取 GPU 实时状态雷达 (用于可视化)
func (gpm *GlobalPowerMap) GetGPURadars(limit int) []*GPUSnapshot {
	gpm.gpuLock.RLock()
	defer gpm.gpuLock.RUnlock()

	count := 0
	for _, snaps := range gpm.gpuSnapshots {
		count += len(snaps)
	}

	if count == 0 {
		return nil
	}

	if limit <= 0 || limit > count {
		limit = count
	}

	result := make([]*GPUSnapshot, 0, limit)
	for _, snaps := range gpm.gpuSnapshots {
		for i := len(snaps) - 1; i >= 0 && len(result) < limit; i-- {
			result = append(result, snaps[i])
		}
	}
	return result
}

// ====== WebSocket 订阅 ======

// Subscribe 注册 WebSocket 订阅者
func (gpm *GlobalPowerMap) Subscribe(id string, country string) *Subscriber {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	sub := &Subscriber{
		ID:      id,
		Chan:    make(chan []byte, 100),
		Country: country,
	}
	gpm.subscribers[id] = sub
	log.Printf("[Visualizer] Subscribed: %s (country=%s)", id, country)
	return sub
}

// Unsubscribe 注销订阅者
func (gpm *GlobalPowerMap) Unsubscribe(id string) {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	if sub, exists := gpm.subscribers[id]; exists {
		close(sub.Chan)
		delete(gpm.subscribers, id)
		log.Printf("[Visualizer] Unsubscribed: %s", id)
	}
}

// Broadcast 广播数据给所有订阅者
func (gpm *GlobalPowerMap) Broadcast(data interface{}) {
	gpm.mu.RLock()
	defer gpm.mu.RUnlock()

	payload, err := json.Marshal(data)
	if err != nil {
		return
	}

	for _, sub := range gpm.subscribers {
		select {
		case sub.Chan <- payload:
		default:
			// 发送失败，跳过
		}
	}
}

// ====== 模拟模式 ======

// GenerateSimulationData 生成模拟数据用于演示
func (gpm *GlobalPowerMap) GenerateSimulationData() {
	if !gpm.simulate {
		return
	}

	regions := []struct {
		name, country string
		lat, lng      float64
		nodeCount     int
	}{
		{"us-east", "USA", 37.7749, -122.4194, 15},
		{"us-west", "USA", 34.0522, -118.2437, 12},
		{"eu-west", "Germany", 52.5200, 13.4050, 20},
		{"eu-north", "UK", 51.5074, -0.1278, 10},
		{"ap-southeast", "Singapore", 1.3521, 103.8198, 18},
		{"ap-east", "Japan", 35.6762, 139.6503, 14},
		{"ap-south", "India", 19.0760, 72.8777, 8},
		{"cn-east", "China", 31.2304, 121.4737, 25},
		{"cn-north", "China", 39.9042, 116.4074, 20},
	}

	for _, r := range regions {
		regionName := r.name
		if _, exists := gpm.regions[regionName]; exists {
			continue
		}

		rd := &RegionData{
			Name:        regionName,
			Country:     r.country,
			Lat:         r.lat,
			Lng:         r.lng,
			TotalNodes:  r.nodeCount,
			OnlineNodes: int(float64(r.nodeCount) * (0.85 + gpm.rng.Float64()*0.15)),
			TotalGPUs:   r.nodeCount * 8,
			TotalCPU:    r.nodeCount * 128,
			TotalRAMGB:  float64(r.nodeCount) * 512,
			TotalTFLOPS: float64(r.nodeCount) * 1000,
			Nodes:       make([]NodeVisual, 0, r.nodeCount),
		}

		for i := 0; i < r.nodeCount; i++ {
			status := "online"
			if gpm.rng.Float64() < 0.05 {
				status = "offline"
			}
			online := status == "online"

			gpuType := []string{"A100", "H100", "V100", "RTX4090", "H200"}[gpm.rng.Intn(5)]

			gpus := make([]GPUInfo, 0, 8)
			for j := 0; j < 8; j++ {
				util := gpm.rng.Float64() * 100
				temp := 50 + gpm.rng.Float64()*30
				gpus = append(gpus, GPUInfo{
					ID:          fmt.Sprintf("gpu_%d", j),
					Model:       gpuType,
					Utilization: math.Round(util*100) / 100,
					Temperature: math.Round(temp*100) / 100,
					MemoryUsed:  math.Round(32 + gpm.rng.Float64()*32),
					MemoryTotal: 64,
					PowerWatts:  300 + gpm.rng.Float64()*150,
					Status:      gpuStatus(temp, util),
				})
			}

			load := gpm.rng.Float64() * 100
			rd.Nodes = append(rd.Nodes, NodeVisual{
				ID:           fmt.Sprintf("node_%s_%d", regionName, i),
				Region:       regionName,
				Country:      r.country,
				IPAddress:    fmt.Sprintf("%d.%d.%d.%d", 10+gpm.rng.Intn(200), gpm.rng.Intn(256), gpm.rng.Intn(256), gpm.rng.Intn(256)),
				Status:       status,
				GPUType:      gpuType,
				GPUs:         gpus,
				CPUCores:     128,
				MemoryGB:     512,
				Load:         math.Round(load*100) / 100,
				NetworkLatMS: int64(10 + gpm.rng.Intn(150)),
				ActiveTasks:  func() int {
					if online {
						return int(load * 5)
					}
					return 0
				}(),
				MaxTasks:    50,
				SuccessRate: math.Round((0.85 + gpm.rng.Float64()*0.15)*100) / 100,
				HealthStatus: healthStatus(load, temp(gpus)),
				RegisteredAt: time.Now().Add(-time.Duration(gpm.rng.Intn(365)) * 24 * time.Hour).Format(time.RFC3339),
			})
		}

		gpm.regions[regionName] = rd
		gpm.totalNodes += r.nodeCount
		gpm.totalGPUs += r.nodeCount * 8
		gpm.totalCPU += r.nodeCount * 128
		gpm.totalRAM += float64(r.nodeCount) * 512
	}

	log.Printf("[Visualizer] Simulation data generated: %d regions, %d nodes, %d GPUs",
		len(gpm.regions), gpm.totalNodes, gpm.totalGPUs)
}

// ====== 工具函数 ======

func nodeToVisual(n *scheduler.NodeInfo) NodeVisual {
	gpus := []GPUInfo{
		{
			ID:          "gpu_0",
			Model:       n.GPUType,
			Utilization: n.GPUUtil,
			Temperature: n.Temperature,
			MemoryUsed:  n.GPUMemoryGB * (n.GPUUtil / 100),
			MemoryTotal: n.GPUMemoryGB,
			PowerWatts:  300,
			Status:      gpuStatus(n.Temperature, n.GPUUtil),
		},
	}

	return NodeVisual{
		ID:           n.ID,
		Region:       n.Region,
		Country:      regionToCountry(n.Region),
		IPAddress:    "192.168.1." + n.ID[len(n.ID)-1:],
		Status:       n.Status,
		GPUType:      n.GPUType,
		GPUs:         gpus,
		CPUCores:     n.CPUCores,
		MemoryGB:     n.MemoryGB,
		Load:         n.CPUUtil,
		NetworkLatMS: n.NetworkLatency,
		ActiveTasks:  n.ActiveTasks,
		MaxTasks:     n.MaxTasks,
		SuccessRate:  n.SuccessRate,
		HealthStatus: healthStatus(n.CPUUtil, n.Temperature),
		RegisteredAt: n.AssignedAt.Format(time.RFC3339),
	}
}

func gpuStatus(temp, util float64) string {
	if temp > 90 {
		return "critical"
	} else if temp > 80 {
		return "degraded"
	} else if util > 90 {
		return "busy"
	} else if util > 10 {
		return "idle"
	}
	return "offline"
}

func healthStatus(load, temp float64) string {
	if temp > 90 || load > 95 {
		return "critical"
	} else if temp > 80 || load > 80 {
		return "degraded"
	}
	return "healthy"
}

func temp(gpus []GPUInfo) float64 {
	if len(gpus) == 0 {
		return 0
	}
	sum := 0.0
	for _, g := range gpus {
		sum += g.Temperature
	}
	return sum / float64(len(gpus))
}

func regionToCountry(region string) string {
	switch {
	case region == "cn-east" || region == "cn-north":
		return "China"
	case region == "us-east" || region == "us-west":
		return "USA"
	case region == "eu-west":
		return "Germany"
	case region == "eu-north":
		return "UK"
	case region == "ap-southeast":
		return "Singapore"
	case region == "ap-east":
		return "Japan"
	case region == "ap-south":
		return "India"
	default:
		return "Unknown"
	}
}

func regionToLat(region string) float64 {
	switch region {
	case "cn-east":
		return 31.2304
	case "cn-north":
		return 39.9042
	case "us-east":
		return 37.7749
	case "us-west":
		return 34.0522
	case "eu-west":
		return 52.5200
	case "eu-north":
		return 51.5074
	case "ap-southeast":
		return 1.3521
	case "ap-east":
		return 35.6762
	case "ap-south":
		return 19.0760
	default:
		return 0
	}
}

func regionToLng(region string) float64 {
	switch region {
	case "cn-east":
		return 121.4737
	case "cn-north":
		return 116.4074
	case "us-east":
		return -122.4194
	case "us-west":
		return -118.2437
	case "eu-west":
		return 13.4050
	case "eu-north":
		return -0.1278
	case "ap-southeast":
		return 103.8198
	case "ap-east":
		return 139.6503
	case "ap-south":
		return 72.8777
	default:
		return 0
	}
}

// ====== 网络地址工具 ======

func localIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "127.0.0.1"
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return "127.0.0.1"
}

// RemoveNode 从模拟/视觉数据中删除节点
func (gpm *GlobalPowerMap) RemoveNode(nodeID string) error {
	gpm.mu.Lock()
	defer gpm.mu.Unlock()

	for region, rd := range gpm.regions {
		for i, n := range rd.Nodes {
			if n.ID == nodeID {
				rd.Nodes = append(rd.Nodes[:i], rd.Nodes[i+1:]...)
				rd.TotalNodes--
				if n.Status == "online" {
					rd.OnlineNodes--
				}
				gpm.totalNodes--
				// Re-count GPUs
				gpuCount := len(n.GPUs)
				gpm.totalGPUs -= gpuCount
				rd.TotalGPUs -= gpuCount

				log.Printf("[Visualizer] Removed simulated node %s from region %s", nodeID, region)
				return nil
			}
		}
	}
	return fmt.Errorf("node %s not found in visualizer data", nodeID)
}
