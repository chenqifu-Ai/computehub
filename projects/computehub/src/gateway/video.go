// ComputeHub Gateway Video API Handler
// 视频生成 API: /api/v1/video/generate, /api/v1/video/{task_id}/progress
//
// 设计原则：
//   1. Gateway 只做参数验证 + 提交后台进程（解决 #9: Gateway 30s 超时）
//   2. 脚本内置在 Worker，不通过 API 传输（解决 #8: \\n 转义）
//   3. 进度通过文件系统共享（Worker 写 -> Gateway 读）

package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// ── Video API 请求/响应结构 ──

type VideoGenerateRequest struct {
	DocPath      string  `json:"doc_path"`      // 文档路径
	Output       string  `json:"output"`        // 输出文件名（可选）
	TaskID       string  `json:"task_id"`        // 任务ID（可选，自动生成）
	Template     string  `json:"template"`       // 模板: business/clean/minimal
	Voice        string  `json:"voice"`          // 语音: yunxi/xiaoxiao/yunyang/xiaochen
	PageDuration float64 `json:"page_duration"`  // 每页时长（秒）
	NoTTS        bool    `json:"no_tts"`         // 禁用语音
}

type VideoGenerateResponse struct {
	Success bool   `json:"success"`
	TaskID  string `json:"task_id,omitempty"`
	Error   string `json:"error,omitempty"`
	Message string `json:"message,omitempty"`
}

// ── Video Handler ──

func (g *OpcGateway) handleVideoGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		g.sendResponse(w, Response{Success: false, Error: "Only POST allowed"})
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var req VideoGenerateRequest
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.DocPath == "" {
		g.sendResponse(w, Response{Success: false, Error: "doc_path is required"})
		return
	}

	// 生成 task_id
	taskID := req.TaskID
	if taskID == "" {
		taskID = fmt.Sprintf("video_%d", nowMs())
	}

	// 构建 Python 调用参数 JSON
	params := map[string]interface{}{
		"task_id":  taskID,
		"doc_path": req.DocPath,
	}
	if req.Output != "" {
		params["output"] = req.Output
	}
	if req.Template != "" {
		params["template"] = req.Template
	}
	if req.Voice != "" {
		params["voice"] = req.Voice
	}
	if req.PageDuration > 0 {
		params["page_duration"] = req.PageDuration
	}
	if req.NoTTS {
		params["no_tts"] = true
	}

	paramsJSON, _ := json.Marshal(params)

	// 找到 video_worker.py
	workerScript := findVideoWorkerScript()
	if workerScript == "" {
		g.sendResponse(w, Response{Success: false, Error: "video_worker.py not found"})
		return
	}

	// 确保进度目录存在
	os.MkdirAll("/tmp/computehub-video/progress", 0755)

	// 日志文件
	logFile := fmt.Sprintf("/tmp/computehub-video/progress/%s_gw.log", taskID)

	// 后台执行（解决 #9: 永不超时）
	cmd := exec.Command("nohup", "python3", workerScript, string(paramsJSON))
	cmd.Stdout = createLogFile(logFile)
	cmd.Stderr = cmd.Stdout

	if err := cmd.Start(); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Failed to start: %v", err)})
		return
	}

	logWithTimestamp("🎬 Video task submitted: task_id=%s doc=%s pid=%d", taskID, req.DocPath, cmd.Process.Pid)

	g.sendResponse(w, Response{
		Success: true,
		Data: VideoGenerateResponse{
			Success: true,
			TaskID:  taskID,
			Message: "任务已提交后台执行",
		},
	})
}

// handleVideoProgress — 查询视频生成进度
func (g *OpcGateway) handleVideoProgress(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		g.sendResponse(w, Response{Success: false, Error: "Only GET allowed"})
		return
	}

	taskID := r.URL.Query().Get("task_id")
	if taskID == "" {
		g.sendResponse(w, Response{Success: false, Error: "task_id is required"})
		return
	}

	// 读取进度文件
	progressFile := fmt.Sprintf("/tmp/computehub-video/progress/%s.json", taskID)
	data, err := os.ReadFile(progressFile)
	if err != nil {
		// 检查是否还在运行
		logFile := fmt.Sprintf("/tmp/computehub-video/progress/%s_gw.log", taskID)
		if _, err := os.Stat(logFile); err == nil {
			g.sendResponse(w, Response{
				Success: true,
				Data: map[string]interface{}{
					"task_id": taskID,
					"stage":   "running",
					"percent": -1,
					"message": "处理中...",
				},
			})
			return
		}

		g.sendResponse(w, Response{
			Success: true,
			Data: map[string]interface{}{
				"task_id": taskID,
				"stage":   "not_found",
				"percent": 0,
				"message": "任务未找到",
			},
		})
		return
	}

	var progress map[string]interface{}
	if err := json.Unmarshal(data, &progress); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Invalid progress data"})
		return
	}

	g.sendResponse(w, Response{Success: true, Data: progress})
}

// handleVideoList — 列出所有视频任务
func (g *OpcGateway) handleVideoList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		g.sendResponse(w, Response{Success: false, Error: "Only GET allowed"})
		return
	}

	progressDir := "/tmp/computehub-video/progress"
	entries, err := os.ReadDir(progressDir)
	if err != nil {
		g.sendResponse(w, Response{Success: true, Data: []interface{}{}})
		return
	}

	tasks := make([]map[string]interface{}, 0)
	seen := make(map[string]bool)

	for _, entry := range entries {
		name := entry.Name()
		// 只读 .json 文件，忽略 _gw.log 等
		if !strings.HasSuffix(name, ".json") || strings.HasSuffix(name, "_gw.log.json") {
			continue
		}

		taskID := strings.TrimSuffix(name, ".json")
		if seen[taskID] {
			continue
		}
		seen[taskID] = true

		data, err := os.ReadFile(filepath.Join(progressDir, name))
		if err != nil {
			continue
		}

		var progress map[string]interface{}
		if err := json.Unmarshal(data, &progress); err != nil {
			continue
		}

		tasks = append(tasks, progress)
	}

	g.sendResponse(w, Response{Success: true, Data: tasks})
}

// ── 辅助函数 ──

func findVideoWorkerScript() string {
	// 搜索路径（按优先级）
	candidates := []string{
		"/root/.openclaw/workspace/projects/computehub/scripts/video/video_worker.py",
		"/var/computehub/scripts/video/video_worker.py",
		"./scripts/video/video_worker.py",
		"scripts/video/video_worker.py",
	}

	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

func createLogFile(path string) *os.File {
	f, err := os.Create(path)
	if err != nil {
		return nil
	}
	return f
}

func nowMs() int64 {
	// simple timestamp for task ID generation
	return time.Now().UnixNano() / 1000000
}
