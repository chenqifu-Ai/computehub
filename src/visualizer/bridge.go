package visualizer

import (
	"fmt"
	"time"

	"github.com/computehub/opc/src/kernel"
)

// BridgeKernel 注入 kernel 引用，让 Visualizer 能从真实节点获取数据。
func (vg *VisualizerGateway) BridgeKernel(k *kernel.ExtendedKernel) {
	vg.bridgedKernel = k
}

// SyncFromKernel 从 kernel 同步真实节点数据到 GlobalPowerMap。
// 每调用一次用真实节点覆盖模拟数据。
func (vg *VisualizerGateway) SyncFromKernel() {
	if vg.bridgedKernel == nil {
		return
	}

	nm := vg.bridgedKernel.NodeMgr
	if nm == nil {
		return
	}

	realNodes := nm.ListNodes()

	vg.kernelMu.Lock()
	defer vg.kernelMu.Unlock()

	// Step 1: 收集 kernel 中存在的 nodeID
	activeIDs := make(map[string]bool, len(realNodes))
	for _, state := range realNodes {
		activeIDs[state.Register.NodeID] = true
	}

	// Step 2: 清理 visualizer 中已被 kernel 删除的节点
	vg.gpm.RemoveStaleNodes(activeIDs)

	// Step 3: 同步/更新 kernel 中存在的节点
	for _, state := range realNodes {
		node := NodeVisual{
			ID:           state.Register.NodeID,
			Region:       state.Register.Region,
			Country:      state.Register.Region,
			IPAddress:    state.Register.IPAddress,
			Status:       state.Register.Status,
			GPUType:      state.Register.GPUType,
			NodeType:     state.Register.NodeType,
			Platform:     state.Register.Platform,
			CPUCores:     state.Register.CPUCores,
			MemoryGB:     state.Register.GPUMemoryGB,
			Load:         state.Metrics.CPUUtilization,
			NetworkLatMS: int64(state.Metrics.NetworkLatency),
			ActiveTasks:  state.Metrics.ActiveTasks,
			MaxTasks:     state.Metrics.MaxTasks,
			SuccessRate:  state.Metrics.SuccessRate,
			HealthStatus: state.Register.Status,
			RegisteredAt: state.Register.RegisteredAt.Format(time.RFC3339),
			Version:      state.Register.Version,
		}

		for i, gm := range state.Metrics.GPU {
			gpu := GPUInfo{
				ID:          fmt.Sprintf("gpu_%d", i+1),
				Model:       state.Register.GPUType,
				Utilization: gm.Utilization,
				Temperature: gm.Temperature,
				MemoryUsed:  gm.MemoryUsedGB,
				MemoryTotal: gm.MemoryTotalGB,
				PowerWatts:  gm.PowerWatts,
				Status:      "busy",
			}
			if gm.Utilization < 5 {
				gpu.Status = "idle"
			}
			node.GPUs = append(node.GPUs, gpu)
		}

		vg.gpm.RegisterNodeFromKernel(&node)
	}
}
