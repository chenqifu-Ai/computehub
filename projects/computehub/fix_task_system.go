// ComputeHub 任务系统修复
// 直接修改源文件: actions.go, kernel.go, gateway.go, main.go (tui), worker/main.go
//
// 用法: go run fix_task_system.go
// 或直接编辑，补丁内容见下方
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

var ROOT string

func main() {
	ROOT = "/root/.openclaw/workspace/projects/computehub"
	fmt.Println("🔧 ComputeHub 任务系统修复")

	// === 1. KERNEL: actions.go — TaskSubmit 添加 NodeID 字段 ===
	editFile(filepath.Join(ROOT, "src/kernel/actions.go"), []patch{
		{
			desc: "TaskSubmit struct 添加 NodeID 字段",
			old: `// TaskSubmit 任务提交信息
type TaskSubmit struct {
	TaskID       string    ` + "`json:\"task_id\"`" + `
	SourceType   string    ` + "`json:\"source_type\"`" + ` // "direct" | "scheduled" | "auto"
	Priority     int       ` + "`json:\"priority\"`" + `    // 1-10, 10 highest
	RegionAffinity string  ` + "`json:\"region_affinity\"`" + ` // preferred region
	Timeout      int       ` + "`json:\"timeout\"`" + `     // seconds
	Command      string    ` + "`json:\"command\"`" + `     // command to execute
	EnvVars      map[string]string ` + "`json:\"env_vars,omitempty\"`" + `
	MaxRetries   int       ` + "`json:\"max_retries\"`" + `
	SubmittedAt  time.Time ` + "`json:\"submitted_at\"`" + `
}`,
			new: `// TaskSubmit 任务提交信息
type TaskSubmit struct {
	TaskID       string    ` + "`json:\"task_id\"`" + `
	NodeID       string    ` + "`json:\"node_id\"`" + `    // 目标节点 (空=自动分配)
	SourceType   string    ` + "`json:\"source_type\"`" + ` // "direct" | "scheduled" | "auto"
	Priority     int       ` + "`json:\"priority\"`" + `    // 1-10, 10 highest
	RegionAffinity string  ` + "`json:\"region_affinity\"`" + ` // preferred region
	Timeout      int       ` + "`json:\"timeout\"`" + `     // seconds
	Command      string    ` + "`json:\"command\"`" + `     // command to execute
	EnvVars      map[string]string ` + "`json:\"env_vars,omitempty\"`" + `
	MaxRetries   int       ` + "`json:\"max_retries\"`" + `
	SubmittedAt  time.Time ` + "`json:\"submitted_at\"`" + `
}`,
		},
	})

	// === 2. KERNEL: actions.go — TaskState 添加 Source 字段 ===
	editFile(filepath.Join(ROOT, "src/kernel/actions.go"), []patch{
		{
			desc: "TaskState struct 添加 Source 字段",
			old: `type TaskState struct {
	Task     *TaskSubmit
	Status   string // "pending" | "running" | "completed" | "failed" | "cancelled"
	Assigned string // node_id
	Result   *TaskResult
	Retries  int
	Created  time.Time
}`,
			new: `type TaskState struct {
	Task     *TaskSubmit
	Status   string // "pending" | "running" | "completed" | "failed" | "cancelled"
	Assigned string // node_id
	Result   *TaskResult
	Retries  int
	Created  time.Time
	Source   string // source_type display name
}`,
		},
	})

	// === 3. KERNEL: actions.go — SubmitTask 支持 NodeID 定向 ===
	editFile(filepath.Join(ROOT, "src/kernel/actions.go"), []patch{
		{
			desc: "SubmitTask 支持 node_id 定向分配",
			old: `	// 0. 没有任何节点注册
	if len(nm.nodes) == 0 {
		return fmt.Errorf("no nodes registered")
	}

	// 1. Convert priority from 1-10 scale to scheduler priority
	schedPriority := scheduler.TaskPriority(task.Priority)
	if schedPriority < 1 {
		schedPriority = scheduler.PriorityMedium
	}

	// 2. Check if any node has capacity
	hasCapacity := false`,
			new: `	// 0. 没有任何节点注册
	if len(nm.nodes) == 0 {
		return fmt.Errorf("no nodes registered")
	}

	// 1. Convert priority from 1-10 scale to scheduler priority
	schedPriority := scheduler.TaskPriority(task.Priority)
	if schedPriority < 1 {
		schedPriority = scheduler.PriorityMedium
	}

	// 2. 如果指定了 NodeID，直接分配给该节点
	if task.NodeID != "" {
		if state, exists := nm.nodes[task.NodeID]; exists {
			if state.Register.Status == "online" {
				state.Tasks[task.TaskID] = &TaskState{
					Task:     task,
					Status:   "pending",
					Assigned: task.NodeID,
					Created:  time.Now(),
					Source:   task.SourceType,
				}
				logWithTimestamp("[NodeMgr] Assigned task %s -> node %s (by request)", task.TaskID, task.NodeID)
				return nil
			}
		}
		return fmt.Errorf("node %s not found or not online", task.NodeID)
	}

	// 3. Check if any node has capacity
	hasCapacity := false`,
		},
	})

	// === 4. KERNEL: actions.go — 所有 TaskState 创建加 Source ===
	editFile(filepath.Join(ROOT, "src/kernel/actions.go"), []patch{
		{
			desc: "SubmitTask 自动分配的 TaskState 加 Source",
			old: `		state.Tasks[task.TaskID] = &TaskState{
			Task:     task,
			Status:   "running",
			Assigned: bestNodeID,
			Created:  time.Now(),
		}`,
			new: `		state.Tasks[task.TaskID] = &TaskState{
			Task:     task,
			Status:   "running",
			Assigned: bestNodeID,
			Created:  time.Now(),
			Source:   task.SourceType,
		}`,
		},
		{
			desc: "dispatchFromQueue 的 TaskState 加 Source",
			old: `		nodeState.Tasks[nextTask.TaskID] = &TaskState{
			Task:     taskPayload,
			Status:   "running",
			Assigned: bestNodeID,
			Created:  time.Now(),
		}`,
			new: `		nodeState.Tasks[nextTask.TaskID] = &TaskState{
			Task:     taskPayload,
			Status:   "running",
			Assigned: bestNodeID,
			Created:  time.Now(),
			Source:   taskPayload.SourceType,
		}`,
		},
	})

	// === 5. GATEWAY: gateway.go — 添加 /api/v1/tasks/detail ===
	editFile(filepath.Join(ROOT, "src/gateway/gateway.go"), []patch{
		{
			desc: "Serve() 注册 /api/v1/tasks/detail",
			old: `	http.HandleFunc("/api/v1/tasks/cancel", g.handleTaskCancel)`,
			new: `	http.HandleFunc("/api/v1/tasks/detail", g.handleTaskDetail)
	http.HandleFunc("/api/v1/tasks/cancel", g.handleTaskCancel)`,
		},
		{
			desc: "ServeHTTP 添加 detail 路由",
			old: `	case "/api/v1/tasks/cancel":
		g.handleTaskCancel(w, r)`,
			new: `	case "/api/v1/tasks/detail":
		g.handleTaskDetail(w, r)
	case "/api/v1/tasks/cancel":
		g.handleTaskCancel(w, r)`,
		},
		{
			desc: "TaskSubmit 解析 node_id",
			old: `	var task kernel.TaskSubmit
	if err := json.Unmarshal(body, &task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	task.SubmittedAt = time.Now()
	if task.Priority == 0 {
		task.Priority = 5
	}
	if task.SourceType == "" {
		task.SourceType = "api"
	}
	if task.MaxRetries == 0 {
		task.MaxRetries = 3
	}`,
			new: `	var task kernel.TaskSubmit
	if err := json.Unmarshal(body, &task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	task.SubmittedAt = time.Now()
	if task.Priority == 0 {
		task.Priority = 5
	}
	if task.SourceType == "" {
		task.SourceType = "api"
	}
	if task.MaxRetries == 0 {
		task.MaxRetries = 3
	}
	// 兼容 TUI 提交的 node_id (可能在嵌套或平级)
	if task.NodeID == "" {
		if nodeID, ok := rawMap["node_id"].(string); ok {
			task.NodeID = nodeID
		}
	}`,
		},
	})

	// 解析 rawMap
	editFile(filepath.Join(ROOT, "src/gateway/gateway.go"), []patch{
		{
			desc: "解析 body 为 rawMap 供 node_id 回退使用",
			old: `	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var task kernel.TaskSubmit
	if err := json.Unmarshal(body, &task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}`,
			new: `	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	// First pass: parse full body to get rawMap for compatibility
	var rawMap map[string]interface{}
	json.Unmarshal(body, &rawMap)

	var task kernel.TaskSubmit
	if err := json.Unmarshal(body, &task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}`,
		},
	})

	// === 6. GATEWAY: gateway.go — handleTaskDetail 实现 ===
	editFile(filepath.Join(ROOT, "src/gateway/gateway.go"), []patch{
		{
			desc: "handleTaskList 添加 source 字段",
			old: `			tasks[node.Register.NodeID] = append(tasks[node.Register.NodeID], map[string]interface{}{
				"task_id":    taskID,
				"status":     ts.Status,
				"command":    ts.Task.Command,
				"source_type": ts.Task.SourceType,
				"priority":   ts.Task.Priority,
			})`,
			new: `			tasks[node.Register.NodeID] = append(tasks[node.Register.NodeID], map[string]interface{}{
				"task_id":     taskID,
				"source":      ts.Task.SourceType,
				"status":      ts.Status,
				"command":     ts.Task.Command,
				"source_type": ts.Task.SourceType,
				"priority":    ts.Task.Priority,
			})`,
		},
		{
			desc: "添加 handleTaskDetail 方法",
			old: `func (g *OpcGateway) handleTaskCancel(w http.ResponseWriter, r *http.Request) {`,
			new: `func (g *OpcGateway) handleTaskDetail(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		g.sendResponse(w, Response{Success: false, Error: "Only GET allowed"})
		return
	}

	taskID := r.URL.Query().Get("task_id")
	nodeID := r.URL.Query().Get("node_id")
	if taskID == "" {
		g.sendResponse(w, Response{Success: false, Error: "task_id is required"})
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	for _, state := range nodes {
		if nodeID != "" && state.Register.NodeID != nodeID {
			continue
		}
		if ts, exists := state.Tasks[taskID]; exists {
			g.sendResponse(w, Response{
				Success: true,
				Data: map[string]interface{}{
					"task_id":     taskID,
					"node_id":     state.Register.NodeID,
					"command":     ts.Task.Command,
					"priority":    ts.Task.Priority,
					"timeout":     ts.Task.Timeout,
					"source_type": ts.Task.SourceType,
					"status":      ts.Status,
				},
			})
			return
		}
	}

	g.sendResponse(w, Response{
		Success: false,
		Error:   fmt.Sprintf("task %s not found", taskID),
	})
}

func (g *OpcGateway) handleTaskCancel(w http.ResponseWriter, r *http.Request) {`,
		},
	})

	// === 7. TUI: cmd/tui/main.go — submit 添加 node_id ===
	editFile(filepath.Join(ROOT, "cmd/tui/main.go"), []patch{
		{
			desc: "TUI submit 发送 node_id + 更好的 task_id",
			old: `		case strings.HasPrefix(cmd, "submit "):
			// submit <node_id> <cmd>
			parts := strings.Fields(input)
			if len(parts) < 3 {
				fmt.Printf("\n %s用法: submit <node_id> <command>%s\n", Yellow, Reset)
				continue
			}
			nodeID := parts[1]
			command := strings.Join(parts[2:], " ")
			// Build POST request to /api/v1/tasks/submit
			payload := map[string]interface{}{
				"task_id":    fmt.Sprintf("tui-%s", strings.ReplaceAll(command, " ", "-")[:min(20, len(command))]),
				"source_type": "tui",
				"priority":   5,
				"command":    command,
				"max_retries": 3,
			}`,
			new: `		case strings.HasPrefix(cmd, "submit "):
			// submit <node_id> <cmd>
			parts := strings.Fields(input)
			if len(parts) < 3 {
				fmt.Printf("\n %s用法: submit <node_id> <command>%s\n", Yellow, Reset)
				continue
			}
			nodeID := parts[1]
			command := strings.Join(parts[2:], " ")
			// Build POST request to /api/v1/tasks/submit
			shortCmd := command
			if len(shortCmd) > 16 { shortCmd = shortCmd[:16] }
			taskID := fmt.Sprintf("tui-%s-%d", strings.ReplaceAll(shortCmd, " ", "_"), time.Now().Unix()%100000)
			payload := map[string]interface{}{
				"task_id":    taskID,
				"node_id":    nodeID,
				"source_type": "tui",
				"priority":   5,
				"command":    command,
				"max_retries": 3,
			}`,
		},
	})

	// === 8. WORKER: cmd/worker/main.go — 接受 pending + running ===
	editFile(filepath.Join(ROOT, "cmd/worker/main.go"), []patch{
		{
			desc: "Worker 接受 pending + running 状态任务",
			old: `		// Look for pending tasks assigned to us
		for _, task := range tasks {
			if task.Status == "pending" {`,
			new: `		// Look for tasks assigned to us
		for _, task := range tasks {
			if task.Status == "pending" || task.Status == "running" {`,
		},
	})

	// === 编译验证 ===
	fmt.Println()
	fmt.Println("🛠️  编译验证...")
	cmds := [][]string{
		{"go", "build", "./src/kernel/"},
		{"go", "build", "./src/gateway/"},
		{"go", "build", "./cmd/tui/"},
		{"go", "build", "./cmd/worker/"},
		{"go", "build", "./..."},
	}
	allOK := true
	for _, cmdArgs := range cmds {
		c := exec.Command(cmdArgs[0], cmdArgs[1:]...)
		c.Dir = ROOT
		out, err := c.CombinedOutput()
		if err != nil {
			fmt.Printf("  ❌ %s: %v\n", strings.Join(cmdArgs, " "), string(out))
			allOK = false
		} else {
			fmt.Printf("  ✅ %s\n", strings.Join(cmdArgs, " "))
		}
	}

	if allOK {
		fmt.Println()
		fmt.Println("🎉 全部修复完成！")
		fmt.Println()
		fmt.Println("使用方法:")
		fmt.Println("  1. submit cn-east-01 'echo hello'  — 提交任务到指定节点")
		fmt.Println("  2. cancel <task_id>                — 取消任务")
		fmt.Println("  3. list                            — 刷新任务列表")
	}
}

type patch struct {
	desc string
	old  string
	new  string
}

func editFile(path string, patches []patch) {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Printf("  ❌ 读取失败 %s: %v\n", path, err)
		return
	}

	content := string(data)
	modified := false

	for _, p := range patches {
		if strings.Contains(content, p.old) {
			content = strings.Replace(content, p.old, p.new, 1)
			fmt.Printf("  ✅ %s — %s\n", filepath.Base(path), p.desc)
			modified = true
		} else {
			fmt.Printf("  ⚠️  %s — %s: 未找到匹配文本\n", filepath.Base(path), p.desc)
		}
	}

	if modified {
		if err := os.WriteFile(path, []byte(content), 0644); err != nil {
			fmt.Printf("  ❌ 写入失败 %s: %v\n", path, err)
		}
	}
}
