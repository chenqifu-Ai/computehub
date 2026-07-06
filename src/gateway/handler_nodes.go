package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/computehub/opc/src/kernel"
)

// ==================== Node Handlers ====================

func (g *OpcGateway) handleNodeRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var reg kernel.NodeRegister
	if err := json.Unmarshal(body, &reg); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	reg.IPAddress = extractClientIP(r)
	reg.RegisteredAt = time.Now()
	if reg.Status == "" {
		reg.Status = "online"
	}
	if reg.Region == "" {
		reg.Region = "unknown"
	}

	if len(reg.NodeID) > 15 {
		logWithTimestamp("⚠️ Node ID too long (%d chars): %q — may be truncated on Windows. Use --node-id with ≤15 chars",
			len(reg.NodeID), reg.NodeID)
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeRegister, &reg)
	resp := <-respChan

	if resp.Success {
		regCopy := reg
		go g.BroadcastNodeEvent(EventTypeNodeJoin, &regCopy)
	}

	g.auditLog(reg.NodeID, AuditNodeRegister, "node", reg.NodeID,
		fmt.Sprintf("region=%s gpu=%s", reg.Region, reg.GPUType), resp.Success)

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeUnregister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		NodeID string `json:"node_id"`
	}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.NodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeUnregister, req.NodeID)
	resp := <-respChan

	if g.unregisterSimFallback != nil {
		if fbErr := g.unregisterSimFallback(req.NodeID); fbErr == nil {
			logWithTimestamp("[Gateway] 🗑️ Visualizer data cleaned for node %s", req.NodeID)
		}
	}

	errStr := ""
	if resp.Error != nil {
		errStr = resp.Error.Error()
	}

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    errStr,
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeHeartbeat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var heartbeat map[string]interface{}
	if err := json.Unmarshal(body, &heartbeat); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	nodeID, _ := heartbeat["node_id"].(string)
	if nodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required for heartbeat"})
		return
	}

	heartbeat["ip_address"] = extractClientIP(r)

	kernelRespChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeHeartbeat, heartbeat)
	kernelResp := <-kernelRespChan

	if g.Scheduler != nil {
		g.Scheduler.UpdateNodeHeartbeat(nodeID, 15, 45.0, 62.0, 24.0)
	}

	g.sendResponse(w, Response{
		Success:  kernelResp.Success,
		Data:     kernelResp.Data,
		Error:    fmt.Sprintf("%v", kernelResp.Error),
		Duration: kernelResp.Duration,
	})
}

func (g *OpcGateway) handleNodeList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	nodeData := make([]map[string]interface{}, 0, len(nodes))

	for _, node := range nodes {
		ipAddr := ""
		if node.Register.IPAddress != "" {
			ipAddr = node.Register.IPAddress
		}
		nodeData = append(nodeData, map[string]interface{}{
			"node_id":         node.Register.NodeID,
			"node_type":       node.Register.NodeType,
			"platform":        node.Register.Platform,
			"region":          node.Register.Region,
			"gpu_type":        node.Register.GPUType,
			"status":          node.Register.Status,
			"version":         node.Register.Version,
			"ip_address":      ipAddr,
			"registered_at":   node.Register.RegisteredAt.Format(time.RFC3339),
			"active_tasks":    node.Metrics.ActiveTasks,
			"cpu_utilization": node.Metrics.CPUUtilization,
			"gpu_utilization": node.Metrics.GPUUtilization,
			"temperature":     node.Metrics.Temperature,
			"memory_used_gb":  node.Metrics.MemoryUsedGB,
		})
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    nodeData,
	})
}

func (g *OpcGateway) handleNodeMetrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	metrics, err := g.Kernel.NodeMgr.GetNodeMetrics(nodeID)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("%v", err)})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    metrics,
	})
}

func (g *OpcGateway) handleNodesStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()

	onlineCount := 0
	offlineCount := 0
	byRegion := make(map[string]int)
	byType := make(map[string]int)
	byVersion := make(map[string]int)
	totalTasks := 0
	activeTasks := 0
	totalCPU := 0.0
	totalMem := 0.0

	nodeList := make([]map[string]interface{}, 0, len(nodes))

	for _, node := range nodes {
		nodeData := map[string]interface{}{
			"node_id":        node.Register.NodeID,
			"status":         node.Register.Status,
			"version":        node.Register.Version,
			"platform":       node.Register.Platform,
			"region":         node.Register.Region,
			"gpu_type":       node.Register.GPUType,
			"ip_address":     node.Register.IPAddress,
			"registered_at":  node.Register.RegisteredAt,
			"active_tasks":   node.Metrics.ActiveTasks,
			"total_tasks":    node.Metrics.TotalTasks,
			"cpu_utilization": node.Metrics.CPUUtilization,
			"memory_used_gb": node.Metrics.MemoryUsedGB,
		}
		nodeList = append(nodeList, nodeData)

		if node.Register.Status == "online" {
			onlineCount++
		} else {
			offlineCount++
		}

		region := node.Register.Region
		if region == "" {
			region = "unknown"
		}
		byRegion[region]++

		nodeType := "cpu"
		if node.Register.GPUType != "" {
			nodeType = "gpu"
		}
		byType[nodeType]++

		ver := node.Register.Version
		if ver == "" {
			ver = "unknown"
		}
		byVersion[ver]++

		totalTasks += node.Metrics.TotalTasks
		activeTasks += node.Metrics.ActiveTasks
		totalCPU += node.Metrics.CPUUtilization
		totalMem += node.Metrics.MemoryUsedGB
	}

	stats := map[string]interface{}{
		"total_nodes":   len(nodes),
		"online_nodes":  onlineCount,
		"offline_nodes": offlineCount,
		"total_tasks":   totalTasks,
		"active_tasks":  activeTasks,
		"avg_cpu_util":  totalCPU / float64(max(len(nodes), 1)),
		"avg_mem_used":  totalMem / float64(max(len(nodes), 1)),
		"by_region":     byRegion,
		"by_type":       byType,
		"by_version":    byVersion,
		"nodes":         nodeList,
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    stats,
	})
}
