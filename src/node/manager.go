// Package node - NodeManager manages the distributed compute node pool.
// Handles registration, heartbeat monitoring, health checks,
// circuit breaking, and node pool management.
package node

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"
)

// ─── 熔断状态 ───

const (
	CircuitClosed   = "closed"    // Normal operation
	CircuitOpen     = "open"      // Failing, reject requests
	CircuitHalfOpen = "half-open" // Testing recovery
)

// CircuitBreaker implements the circuit breaker pattern for node health.
type CircuitBreaker struct {
	mu             sync.Mutex
	state          string
	failureCount   int
	failureThreshold int
	successCount   int
	successThreshold int
	lastFailure    time.Time
	resetTimeout   time.Duration
}

// NewCircuitBreaker creates a circuit breaker with defaults.
func NewCircuitBreaker(failureThreshold, successThreshold int, resetTimeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		state:            CircuitClosed,
		failureThreshold: failureThreshold,
		successThreshold: successThreshold,
		resetTimeout:     resetTimeout,
	}
}

// Allow checks if a request should proceed.
func (cb *CircuitBreaker) Allow() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case CircuitClosed:
		return true
	case CircuitOpen:
		// Check if reset timeout has elapsed
		if time.Since(cb.lastFailure) > cb.resetTimeout {
			cb.state = CircuitHalfOpen
			return true
		}
		return false
	case CircuitHalfOpen:
		return true
	}
	return false
}

// RecordSuccess records a successful operation.
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case CircuitHalfOpen:
		cb.successCount++
		if cb.successCount >= cb.successThreshold {
			cb.state = CircuitClosed
			cb.failureCount = 0
			cb.successCount = 0
		}
	case CircuitClosed:
		cb.failureCount = 0
	}
}

// RecordFailure records a failed operation.
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failureCount++
	cb.lastFailure = time.Now()

	switch cb.state {
	case CircuitClosed:
		if cb.failureCount >= cb.failureThreshold {
			cb.state = CircuitOpen
		}
	case CircuitHalfOpen:
		cb.state = CircuitOpen
	}
}

// State returns the current circuit breaker state.
func (cb *CircuitBreaker) State() string {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	return cb.state
}

// ─── 节点管理器 ───

// NodeManager orchestrates the distributed node pool.
type NodeManager struct {
	mu         sync.RWMutex
	nodes      map[string]*Node      // ID -> Node
	localNode  *Node                 // Local node
	registry   chan *Node            // Registration channel
hbResults    chan hbResult         // Heartbeat results
	circuitBreakers map[string]*CircuitBreaker
	regionIndex map[string][]string    // region -> node IDs

	// Configuration
	heartbeatInterval time.Duration
	hbTimeout         time.Duration
	hbFailureLimit    int
	circuitFailLimit  int
	circuitReset      time.Duration
}

type hbResult struct {
	nodeID string
	OK     bool
}

// NewNodeManager creates a node manager with the local node.
func NewNodeManager(localNode *Node, opts ...NodeManagerOption) *NodeManager {
	nm := &NodeManager{
		nodes:             make(map[string]*Node),
		localNode:         localNode,
		registry:          make(chan *Node, 100),
		hbResults:         make(chan hbResult, 500),
		regionIndex:       make(map[string][]string),
		circuitBreakers:   make(map[string]*CircuitBreaker),
		heartbeatInterval: 10 * time.Second,
		hbTimeout:         30 * time.Second,
		hbFailureLimit:    3,
		circuitFailLimit:  5,
		circuitReset:      60 * time.Second,
	}

	for _, opt := range opts {
		opt(nm)
	}

	// Register local node
	nm.RegisterNode(localNode)

	// Start heartbeat monitor
	go nm.heartbeatMonitor()

	return nm
}

// NodeManagerOption configures the NodeManager.
type NodeManagerOption func(*NodeManager)

// WithHeartbeatInterval sets the heartbeat interval.
func WithHeartbeatInterval(d time.Duration) NodeManagerOption {
	return func(nm *NodeManager) {
		nm.heartbeatInterval = d
	}
}

// WithHBTimeout sets the heartbeat timeout.
func WithHBTimeout(d time.Duration) NodeManagerOption {
	return func(nm *NodeManager) {
		nm.hbTimeout = d
	}
}

// RegisterNode adds a node to the pool.
func (nm *NodeManager) RegisterNode(node *Node) {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	// Remove from old region index if any
	if oldRegion := nm.nodes[node.ID]; oldRegion != nil {
		nm.removeFromIndex(oldRegion.Region, node.ID)
	}

	node.Status = NodeStatusOnline
	node.Registered = time.Now()
	node.LastHB = time.Now()
	nm.nodes[node.ID] = node
	nm.circuitBreakers[node.ID] = NewCircuitBreaker(
		nm.circuitFailLimit, 2, nm.circuitReset,
	)
	nm.addToIndex(node.Region, node.ID)
}

// RemoveNode removes a node from the pool.
func (nm *NodeManager) RemoveNode(nodeID string) {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	if node, exists := nm.nodes[nodeID]; exists {
		nm.removeFromIndex(node.Region, nodeID)
		delete(nm.nodes, nodeID)
		delete(nm.circuitBreakers, nodeID)
	}
}

// GetNode retrieves a node by ID.
func (nm *NodeManager) GetNode(nodeID string) (*Node, bool) {
	nm.mu.RLock()
	defer nm.mu.RUnlock()
	node, ok := nm.nodes[nodeID]
	return node, ok
}

// GetAllNodes returns all nodes (safe copy).
func (nm *NodeManager) GetAllNodes() []*Node {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	result := make([]*Node, 0, len(nm.nodes))
	for _, node := range nm.nodes {
		// Copy essential fields for safe consumption
		cp := *node
		cp.Capability = node.GetCapability()
		result = append(result, &cp)
	}
	return result
}

// GetOnlineNodes returns only online/busy nodes.
func (nm *NodeManager) GetOnlineNodes() []*Node {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	result := make([]*Node, 0)
	for _, node := range nm.nodes {
		if node.Status == NodeStatusOnline || node.Status == NodeStatusBusy {
			cp := *node
			cp.Capability = node.GetCapability()
			result = append(result, &cp)
		}
	}
	return result
}

// GetNodesByRegion returns nodes in a specific region.
func (nm *NodeManager) GetNodesByRegion(region string) []*Node {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	ids, ok := nm.regionIndex[region]
	if !ok {
		return nil
	}

	result := make([]*Node, 0, len(ids))
	for _, id := range ids {
		if node, exists := nm.nodes[id]; exists {
			result = append(result, node)
		}
	}
	return result
}

// ─── 心跳监控 ───

// heartbeatMonitor periodically checks all node health.
func (nm *NodeManager) heartbeatMonitor() {
	ticker := time.NewTicker(nm.heartbeatInterval)
	defer ticker.Stop()

	for range ticker.C {
		nm.checkAllNodes()
	}
}

func (nm *NodeManager) checkAllNodes() {
	nm.mu.RLock()
	nodes := make([]*Node, 0, len(nm.nodes))
	for _, node := range nm.nodes {
		if node.ID != nm.localNode.ID {
			nodes = append(nodes, node)
		}
	}
	nm.mu.RUnlock()

	for _, node := range nodes {
		// Skip if circuit is open
		if cb := nm.circuitBreakers[node.ID]; cb != nil && !cb.Allow() {
			continue
		}

		// Send heartbeat
		ok := nm.sendHeartbeat(node)
		nm.hbResults <- hbResult{nodeID: node.ID, OK: ok}
	}
}

func (nm *NodeManager) sendHeartbeat(node *Node) bool {
	req := HeartbeatRequest{
		NodeID:    nm.localNode.ID,
		Capability: &nm.localNode.Capability,
	}
	data, _ := json.Marshal(req)

	addr := fmt.Sprintf("http://%s:%d/api/node/heartbeat", node.IP, node.Port)
	client := &http.Client{Timeout: 5 * time.Second}

	resp, err := client.Post(addr, "application/json", bytes.NewBuffer(data))
	if err != nil {
		nm.handleHBFailure(node)
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		nm.handleHBFailure(node)
		return false
	}

	// Parse response
	var hbr HeartbeatResponse
	if err := json.NewDecoder(resp.Body).Decode(&hbr); err == nil && hbr.Accepted {
		nm.handleHBSuccess(node)
		return true
	}

	nm.handleHBFailure(node)
	return false
}

func (nm *NodeManager) handleHBSuccess(node *Node) {
	nm.mu.Lock()
	node.MarkHeartbeat()
	nm.mu.Unlock()

	if cb, ok := nm.circuitBreakers[node.ID]; ok {
		cb.RecordSuccess()
	}
}

func (nm *NodeManager) handleHBFailure(node *Node) {
	nm.mu.Lock()
	failures := node.RecordHBFailure()
	nm.mu.Unlock()

	if cb, ok := nm.circuitBreakers[node.ID]; ok {
		cb.RecordFailure()
	}

	if failures >= nm.hbFailureLimit {
		// Evict severely unhealthy nodes after excessive failures
		fmt.Printf("[NodeManager] Node %s marked offline (%d failures)\n", node.ID, failures)
	}
}

// consumeHBResults processes heartbeat results in background.
func (nm *NodeManager) consumeHBResults() {
	for result := range nm.hbResults {
		if node, ok := nm.nodes[result.nodeID]; ok {
			if result.OK {
				node.MarkHeartbeat()
				if cb, exists := nm.circuitBreakers[node.ID]; exists {
					cb.RecordSuccess()
				}
			} else {
				failures := node.RecordHBFailure()
				if cb, exists := nm.circuitBreakers[node.ID]; exists {
					cb.RecordFailure()
				}
				if failures >= nm.hbFailureLimit {
					fmt.Printf("[NodeManager] Node %s marked offline (%d failures)\n", node.ID, failures)
				}
			}
		}
	}
}

// ─── 故障转移 ───

// FailoverTask retries a task on a different node.
func (nm *NodeManager) FailoverTask(taskID, failedNodeID string) (*Node, error) {
	// Find a healthy node that isn't the failed one
	online := nm.GetOnlineNodes()
	for _, node := range online {
		if node.ID != failedNodeID && node.CanAcceptTasks(0.9) {
			cb := nm.circuitBreakers[node.ID]
			if cb == nil || cb.Allow() {
				return node, nil
			}
		}
	}
	return nil, fmt.Errorf("no healthy node available for failover of %s", taskID)
}

// FailoverCount returns the number of healthy nodes available.
func (nm *NodeManager) FailoverCount() int {
	return len(nm.GetOnlineNodes())
}

// ─── 节点池统计 ───

// PoolStats returns aggregate node pool statistics.
func (nm *NodeManager) PoolStats() map[string]any {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	total, online, busy, offline := 0, 0, 0, 0
	totalGPUs := 0
	totalCPUs := 0
	totalMemMB := uint64(0)

	for _, node := range nm.nodes {
		total++
		switch node.Status {
		case NodeStatusOnline:
			online++
		case NodeStatusBusy:
			busy++
		case NodeStatusOffline:
			offline++
		}
		totalGPUs += len(node.Capability.GPUs)
		totalCPUs += node.Capability.CPUCores
		totalMemMB += node.Capability.MemTotalMB
	}

	// Circuit breaker states
	cbStates := map[string]int{
		CircuitClosed:   0,
		CircuitOpen:     0,
		CircuitHalfOpen: 0,
	}
	for _, cb := range nm.circuitBreakers {
		cbStates[cb.State()]++
	}

	return map[string]any{
		"total_nodes":  total,
		"online":       online,
		"busy":         busy,
		"offline":      offline,
		"total_gpus":   totalGPUs,
		"total_cpus":   totalCPUs,
		"total_mem_mb": totalMemMB,
		"circuit_breakers": cbStates,
		"regions":      func() map[string]int {
			counts := make(map[string]int)
			for _, node := range nm.nodes {
				counts[node.Region]++
			}
			return counts
		}(),
	}
}

// ─── 内部方法 ───

func (nm *NodeManager) addToIndex(region, nodeID string) {
	if _, exists := nm.regionIndex[region]; !exists {
		nm.regionIndex[region] = make([]string, 0)
	}
	nm.regionIndex[region] = append(nm.regionIndex[region], nodeID)
}

func (nm *NodeManager) removeFromIndex(region, nodeID string) {
	ids, exists := nm.regionIndex[region]
	if !exists {
		return
	}
	for i, id := range ids {
		if id == nodeID {
			nm.regionIndex[region] = append(ids[:i], ids[i+1:]...)
			break
		}
	}
}
