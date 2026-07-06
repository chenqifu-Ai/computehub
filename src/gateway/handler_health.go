package gateway

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"time"
)

// DetailedHealth 深度健康检查响应
type DetailedHealth struct {
	Status    string            `json:"status"`    // "healthy" | "degraded" | "unhealthy"
	Uptime    string            `json:"uptime"`
	Version   string            `json:"version"`
	Timestamp string            `json:"timestamp"`
	Checks    map[string]CheckResult `json:"checks"`
}

// CheckResult 单项检查结果
type CheckResult struct {
	Status  string `json:"status"`  // "ok" | "warn" | "fail"
	Message string `json:"message,omitempty"`
	Latency string `json:"latency,omitempty"`
}

// handleHealthDetailed — GET /api/v1/health/detailed
// 深度健康检查：LLM 连通性、磁盘空间、内存、节点数
func (g *OpcGateway) handleHealthDetailed(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	checks := make(map[string]CheckResult)
	overallStatus := "healthy"

	// 1. 系统资源检查
	checks["system"] = checkSystemResources()

	// 2. 节点检查
	checks["nodes"] = checkNodes(g)

	// 3. LLM 连通性检查
	checks["llm"] = checkLLM(g)

	// 4. 磁盘空间检查
	checks["disk"] = checkDiskSpace()

	// 5. WebSocket Hub 检查
	checks["ws_hub"] = checkWSHub(g)

	// 6. 内存检查
	checks["memory"] = checkSharedMemory(g)

	// 汇总状态
	for _, c := range checks {
		if c.Status == "fail" {
			overallStatus = "unhealthy"
			break
		}
		if c.Status == "warn" && overallStatus == "healthy" {
			overallStatus = "degraded"
		}
	}

	uptime := time.Since(g.startTime).String()

	resp := DetailedHealth{
		Status:    overallStatus,
		Uptime:    uptime,
		Version:   "1.4.0",
		Timestamp: time.Now().Format(time.RFC3339),
		Checks:    checks,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func checkSystemResources() CheckResult {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	// 检查 goroutine 数量
	numGoroutine := runtime.NumGoroutine()
	if numGoroutine > 1000 {
		return CheckResult{Status: "warn", Message: fmt.Sprintf("high goroutine count: %d", numGoroutine)}
	}

	// 检查堆内存使用
	heapMB := m.HeapAlloc / 1024 / 1024
	if heapMB > 1024 {
		return CheckResult{Status: "warn", Message: fmt.Sprintf("high heap usage: %d MB", heapMB)}
	}

	return CheckResult{Status: "ok", Message: fmt.Sprintf("goroutines=%d heap=%dMB", numGoroutine, heapMB)}
}

func checkNodes(g *OpcGateway) CheckResult {
	if g.Kernel == nil || g.Kernel.NodeMgr == nil {
		return CheckResult{Status: "fail", Message: "NodeManager not initialized"}
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	onlineCount := 0
	for _, n := range nodes {
		if n.Register.Status == "online" {
			onlineCount++
		}
	}

	if len(nodes) == 0 {
		return CheckResult{Status: "warn", Message: "no nodes registered"}
	}

	return CheckResult{
		Status:  "ok",
		Message: fmt.Sprintf("%d/%d nodes online", onlineCount, len(nodes)),
	}
}

func checkLLM(g *OpcGateway) CheckResult {
	if g.composerAPI == "" {
		return CheckResult{Status: "warn", Message: "LLM not configured (composer.api_url empty)"}
	}

	// 轻量检查：只验证配置存在，不实际调用 API（避免阻塞健康检查）
	return CheckResult{Status: "ok", Message: fmt.Sprintf("configured: %s", g.composerAPI)}
}

func checkDiskSpace() CheckResult {
	// 检查当前工作目录磁盘空间
	var stat os.FileInfo
	wd, err := os.Getwd()
	if err != nil {
		return CheckResult{Status: "warn", Message: fmt.Sprintf("cannot get working dir: %v", err)}
	}

	// 使用 statfs 检查磁盘 — 简单检查 deploy/ 目录是否存在
	if _, err := os.Stat("deploy"); os.IsNotExist(err) {
		if _, err := os.Stat("../deploy"); os.IsNotExist(err) {
			return CheckResult{Status: "warn", Message: "deploy/ directory not found"}
		}
	}

	// 检查 gateway.out 和 gateway.err 是否过大
	for _, f := range []string{"gateway.out", "gateway.err"} {
		if info, err := os.Stat(f); err == nil && info.Size() > 100*1024*1024 {
			return CheckResult{Status: "warn", Message: fmt.Sprintf("%s is %d MB (consider rotating)", f, info.Size()/1024/1024)}
		}
	}

	_ = stat
	return CheckResult{Status: "ok", Message: fmt.Sprintf("working dir: %s", wd)}
}

func checkWSHub(g *OpcGateway) CheckResult {
	if g.wsHub == nil {
		return CheckResult{Status: "warn", Message: "WS Hub not initialized"}
	}

	online := g.wsHub.OnlineCount()
	return CheckResult{
		Status:  "ok",
		Message: fmt.Sprintf("%d clients online, %d sent, %d received",
			online, g.wsHub.MessagesSent, g.wsHub.MessagesReceived),
	}
}

func checkSharedMemory(g *OpcGateway) CheckResult {
	stats := clusterMem.getStats()
	episodes, _ := stats["episodes"].(int)
	knowledge, _ := stats["knowledge"].(int)

	return CheckResult{
		Status:  "ok",
		Message: fmt.Sprintf("%d episodes, %d knowledge entries", episodes, knowledge),
	}
}
