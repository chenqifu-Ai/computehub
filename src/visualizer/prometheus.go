package visualizer

import (
	"fmt"
	"strings"
	"time"

	"github.com/computehub/opc/src/kernel"
)

// ====== Prometheus Exporter ======

// 生成 Prometheus 格式指标
func GeneratePrometheusMetrics(k *kernel.ExtendedKernel) string {
	var b strings.Builder

	b.WriteString("# HELP computehub_online_nodes Number of online nodes\n")
	b.WriteString("# TYPE computehub_online_nodes gauge\n")
	b.WriteString(fmt.Sprintf("computehub_online_nodes %d\n", countOnline(k)))

	b.WriteString("# HELP computehub_total_nodes Total registered nodes\n")
	b.WriteString("# TYPE computehub_total_nodes gauge\n")
	b.WriteString(fmt.Sprintf("computehub_total_nodes %d\n", countTotal(k)))

	b.WriteString("# HELP computehub_active_tasks Currently running tasks\n")
	b.WriteString("# TYPE computehub_active_tasks gauge\n")
	b.WriteString(fmt.Sprintf("computehub_active_tasks %d\n", countActiveTasks(k)))

	b.WriteString("# HELP computehub_total_tasks All time tasks\n")
	b.WriteString("# TYPE computehub_total_tasks gauge\n")
	b.WriteString(fmt.Sprintf("computehub_total_tasks %d\n", countTotalTasks(k)))

	// 节点级指标
	nodes := k.NodeMgr.ListNodes()
	for _, n := range nodes {
		nodeID := sanitizeLabel(n.Register.NodeID)
		region := n.Register.Region

		// 节点状态 (0=offline, 1=online)
		statusVal := 0
		if n.Register.Status == "online" {
			statusVal = 1
		}
		b.WriteString(fmt.Sprintf("# HELP computehub_node_status Node status (0=offline, 1=online)\n"))
		b.WriteString(fmt.Sprintf("# TYPE computehub_node_status gauge\n"))
		b.WriteString(fmt.Sprintf("computehub_node_status{node=\"%s\",region=\"%s\",gpu_type=\"%s\"} %d\n",
			nodeID, region, n.Register.GPUType, statusVal))

		// 活跃任务数
		b.WriteString(fmt.Sprintf("# HELP computehub_node_active_tasks Active tasks per node\n"))
		b.WriteString(fmt.Sprintf("# TYPE computehub_node_active_tasks gauge\n"))
		b.WriteString(fmt.Sprintf("computehub_node_active_tasks{node=\"%s\"} %d\n", nodeID, n.Metrics.ActiveTasks))

		// GPU 指标
		for _, gpu := range n.Metrics.GPU {
			gpuID := sanitizeLabel(gpu.NodeID)
			b.WriteString(fmt.Sprintf("# HELP computehub_gpu_utilization GPU utilization (0-100)\n"))
			b.WriteString(fmt.Sprintf("# TYPE computehub_gpu_utilization gauge\n"))
			b.WriteString(fmt.Sprintf("computehub_gpu_utilization{node=\"%s\",gpu=\"%s\"} %.1f\n",
				nodeID, gpuID, gpu.Utilization))

			b.WriteString(fmt.Sprintf("# HELP computehub_gpu_temperature GPU temperature (Celsius)\n"))
			b.WriteString(fmt.Sprintf("# TYPE computehub_gpu_temperature gauge\n"))
			b.WriteString(fmt.Sprintf("computehub_gpu_temperature{node=\"%s\",gpu=\"%s\"} %.1f\n",
				nodeID, gpuID, gpu.Temperature))

			b.WriteString(fmt.Sprintf("# HELP computehub_gpu_memory_used_gb GPU memory used (GB)\n"))
			b.WriteString(fmt.Sprintf("# TYPE computehub_gpu_memory_used_gb gauge\n"))
			b.WriteString(fmt.Sprintf("computehub_gpu_memory_used_gb{node=\"%s\",gpu=\"%s\"} %.0f\n",
				nodeID, gpuID, gpu.MemoryUsedGB))

			b.WriteString(fmt.Sprintf("# HELP computehub_gpu_memory_total_gb GPU total memory (GB)\n"))
			b.WriteString(fmt.Sprintf("# TYPE computehub_gpu_memory_total_gb gauge\n"))
			b.WriteString(fmt.Sprintf("computehub_gpu_memory_total_gb{node=\"%s\",gpu=\"%s\"} %.0f\n",
				nodeID, gpuID, gpu.MemoryTotalGB))
		}

		// 网络
		b.WriteString(fmt.Sprintf("# HELP computehub_node_network_latency Network latency (ms)\n"))
		b.WriteString(fmt.Sprintf("# TYPE computehub_node_network_latency gauge\n"))
		b.WriteString(fmt.Sprintf("computehub_node_network_latency{node=\"%s\"} %.1f\n",
			nodeID, n.Metrics.NetworkLatency))

		// 最后心跳
		secondsSince := time.Since(n.Metrics.LastHeartbeat).Seconds()
		b.WriteString(fmt.Sprintf("# HELP computehub_node_last_heartbeat_seconds Seconds since last heartbeat\n"))
		b.WriteString(fmt.Sprintf("# TYPE computehub_node_last_heartbeat_seconds gauge\n"))
		b.WriteString(fmt.Sprintf("computehub_node_last_heartbeat_seconds{node=\"%s\"} %.0f\n",
			nodeID, secondsSince))
	}

	return b.String()
}

func sanitizeLabel(s string) string {
	s = strings.ReplaceAll(s, "\"", "\\\"")
	s = strings.ReplaceAll(s, " ", "_")
	return s
}

func countOnline(k *kernel.ExtendedKernel) int {
	count := 0
	for _, n := range k.NodeMgr.ListNodes() {
		if n.Register.Status == "online" {
			count++
		}
	}
	return count
}

func countTotal(k *kernel.ExtendedKernel) int {
	return len(k.NodeMgr.ListNodes())
}

func countActiveTasks(k *kernel.ExtendedKernel) int {
	count := 0
	for _, n := range k.NodeMgr.ListNodes() {
		count += n.Metrics.ActiveTasks
	}
	return count
}

func countTotalTasks(k *kernel.ExtendedKernel) int {
	count := 0
	for _, n := range k.NodeMgr.ListNodes() {
		count += len(n.Tasks)
	}
	return count
}
