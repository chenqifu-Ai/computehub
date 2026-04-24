package discover

import (
	"fmt"
	"net"
	"sync"
	"time"
)

// ====== 节点发现模块 ======
// 支持广播发现、多播发现和手动注册三种发现方式

// NodeInfo 节点发现信息
type NodeInfo struct {
	NodeID       string            `json:"node_id"`
	IPAddress    string            `json:"ip_address"`
	Port         int               `json:"port"`
	GPUType      string            `json:"gpu_type"`
	Region       string            `json:"region"`
	RegisteredAt time.Time         `json:"registered_at"`
	LastSeen     time.Time         `json:"last_seen"`
	Capacity     map[string]float64 `json:"capacity"` // GPU hours available
	Labels       map[string]string `json:"labels"`   // 自定义标签
}

// DiscoveryResult 发现结果
type DiscoveryResult struct {
	Nodes       []*NodeInfo `json:"nodes"`
	TotalFound  int         `json:"total_found"`
	SearchTime  time.Duration `json:"search_time"`
	Method      string      `json:"method"` // "broadcast" | "multicast" | "manual"
}

// Discoverer 节点发现器
type Discoverer struct {
	mu          sync.RWMutex
	nodes       map[string]*NodeInfo
	broadcast   bool
	multicast   bool
	manualNodes map[string]*NodeInfo
}

// DiscovererConfig 发现器配置
type DiscovererConfig struct {
	DiscoverPort   int           // 广播/多播端口
	Timeout        time.Duration // 等待响应超时
	MulticastGroup string        // 多播组地址
}

// DefaultConfig 默认配置
func DefaultConfig() DiscovererConfig {
	return DiscovererConfig{
		DiscoverPort:   8283,
		Timeout:        5 * time.Second,
		MulticastGroup: "239.255.255.250",
	}
}

// NewDiscoverer 创建节点发现器
func NewDiscoverer(config DiscovererConfig) *Discoverer {
	return &Discoverer{
		nodes:       make(map[string]*NodeInfo),
		manualNodes: make(map[string]*NodeInfo),
	}
}

// RegisterNode 注册节点到发现器
func (d *Discoverer) RegisterNode(node *NodeInfo) {
	d.mu.Lock()
	defer d.mu.Unlock()

	node.RegisteredAt = time.Now()
	node.LastSeen = time.Now()
	d.nodes[node.NodeID] = node
	d.manualNodes[node.NodeID] = node

	fmt.Printf("[Discoverer] Node registered: %s at %s:%d\n",
		node.NodeID, node.IPAddress, node.Port)
}

// UnregisterNode 注销节点
func (d *Discoverer) UnregisterNode(nodeID string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	delete(d.nodes, nodeID)
	delete(d.manualNodes, nodeID)
}

// GetAllNodes 获取所有已知节点
func (d *Discoverer) GetAllNodes() []*NodeInfo {
	d.mu.RLock()
	defer d.mu.RUnlock()

	nodes := make([]*NodeInfo, 0, len(d.nodes))
	for _, node := range d.nodes {
		c := *node
		nodes = append(nodes, &c)
	}
	return nodes
}

// GetNode 获取指定节点信息
func (d *Discoverer) GetNode(nodeID string) (*NodeInfo, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()

	node, exists := d.nodes[nodeID]
	if !exists {
		return nil, fmt.Errorf("node %s not found", nodeID)
	}

	c := *node
	return &c, nil
}

// Heartbeat 更新节点心跳
func (d *Discoverer) Heartbeat(nodeID string, lastSeen time.Time) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	node, exists := d.nodes[nodeID]
	if !exists {
		return fmt.Errorf("node %s not found", nodeID)
	}

	node.LastSeen = lastSeen
	return nil
}

// IsNodeAlive 检查节点是否存活
func (d *Discoverer) IsNodeAlive(nodeID string, timeout time.Duration) bool {
	d.mu.RLock()
	defer d.mu.RUnlock()

	node, exists := d.nodes[nodeID]
	if !exists {
		return false
	}

	return time.Since(node.LastSeen) < timeout
}

// GetAliveNodes 获取存活节点
func (d *Discoverer) GetAliveNodes(timeout time.Duration) []*NodeInfo {
	d.mu.RLock()
	defer d.mu.RUnlock()

	alive := make([]*NodeInfo, 0)
	for _, node := range d.nodes {
		if time.Since(node.LastSeen) < timeout {
			c := *node
			alive = append(alive, &c)
		}
	}
	return alive
}

// DiscoverByBroadcast 通过广播发现节点 (局域网)
func (d *Discoverer) DiscoverByBroadcast() (*DiscoveryResult, error) {
	start := time.Now()

	// TODO: 实现广播发现
	// 1. 创建 UDP 广播 socket
	// 2. 发送发现请求
	// 3. 等待响应
	// 4. 解析响应并注册节点

	fmt.Println("[Discoverer] Broadcast discovery not yet implemented")

	return &DiscoveryResult{
		Nodes:      make([]*NodeInfo, 0),
		TotalFound: 0,
		SearchTime: time.Since(start),
		Method:     "broadcast",
	}, nil
}

// DiscoverByMulticast 通过多播发现节点 (跨子网)
func (d *Discoverer) DiscoverByMulticast() (*DiscoveryResult, error) {
	start := time.Now()

	// TODO: 实现多播发现
	// 1. 创建 UDP 多播 socket
	// 2. 设置多播地址和端口
	// 3. 发送发现请求
	// 4. 等待响应

	fmt.Println("[Discoverer] Multicast discovery not yet implemented")

	return &DiscoveryResult{
		Nodes:      make([]*NodeInfo, 0),
		TotalFound: 0,
		SearchTime: time.Since(start),
		Method:     "multicast",
	}, nil
}

// DiscoverByManual 从已知节点列表发现
func (d *Discoverer) DiscoverByManual() *DiscoveryResult {
	start := time.Now()
	d.mu.RLock()
	defer d.mu.RUnlock()

	nodes := make([]*NodeInfo, 0, len(d.manualNodes))
	for _, node := range d.manualNodes {
		c := *node
		nodes = append(nodes, &c)
	}

	return &DiscoveryResult{
		Nodes:      nodes,
		TotalFound: len(nodes),
		SearchTime: time.Since(start),
		Method:     "manual",
	}
}

// GetStats 获取发现器统计
func (d *Discoverer) GetStats() map[string]interface{} {
	d.mu.RLock()
	defer d.mu.RUnlock()

	return map[string]interface{}{
		"total_nodes":       len(d.nodes),
		"manual_nodes":      len(d.manualNodes),
		"broadcast_enabled": d.broadcast,
		"multicast_enabled": d.multicast,
	}
}

// ====== 网络发现辅助函数 ======

// GetLocalIP 获取本地 IP 地址
func GetLocalIP() (string, error) {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "", err
	}

	for _, addr := range addrs {
		if ipNet, ok := addr.(*net.IPNet); ok && !ipNet.IP.IsLoopback() {
			if ipNet.IP.To4() != nil {
				return ipNet.IP.String(), nil
			}
		}
	}

	return "", fmt.Errorf("no local IP found")
}

// GetLocalPorts 获取可用端口
func GetLocalPorts(start, count int) ([]int, error) {
	ports := make([]int, 0, count)

	for port := start; port < start+count; port++ {
		conn, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
		if err == nil {
			conn.Close()
			ports = append(ports, port)
		}
	}

	return ports, nil
}
