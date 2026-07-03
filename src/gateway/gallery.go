package gateway

import (
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// GalleryConfig 作品广场配置
type GalleryConfig struct {
	RootDir string `json:"root_dir"` // 作品存储根目录
}

// GalleryItem 代表一个作品项
type GalleryItem struct {
	Name      string `json:"name"`
	Path      string `json:"path"`
	Size      int64  `json:"size"`
	SizeHuman string `json:"size_human"`
	ModTime   string `json:"mod_time"`
	IsVideo   bool   `json:"is_video"`
	IsAudio   bool   `json:"is_audio"`
	IsImage   bool   `json:"is_image"`
	MimeType  string `json:"mime_type"`
	URL       string `json:"url"`
}

// UploadedFileInfo 上传文件的识别信息
type UploadedFileInfo struct {
	Name     string `json:"name"`
	Size     int64  `json:"size"`
	FileType string `json:"file_type"` // document / audio / image / video / binary
	Role     string `json:"role"`      // 内容源 / 配音 / 素材 / ...
	Ext      string `json:"ext"`
}

// TaskProgress 任务进度
type TaskProgress struct {
	TaskID    string `json:"task_id"`
	Title     string `json:"title"`
	Stage     string `json:"stage"`     // uploading / parsing / tts / rendering / completed / failed
	Percent   int    `json:"percent"`
	Message   string `json:"message"`
	OutputURL string `json:"output_url,omitempty"`
	Updated   string `json:"updated"`
}

// GalleryHandler 作品广场 HTTP 处理器
type GalleryHandler struct {
	mu          sync.RWMutex
	rootDir     string
	items       []GalleryItem
	lastScan    time.Time
	tasks       map[string]*TaskProgress
	tasksMu     sync.RWMutex
}

// NewGalleryHandler 创建作品广场处理器
func NewGalleryHandler(config *GalleryConfig) *GalleryHandler {
	rootDir := "/home/computehub/gallery"
	if config != nil && config.RootDir != "" {
		rootDir = config.RootDir
	}
	os.MkdirAll(rootDir, 0755)

	h := &GalleryHandler{
		rootDir: rootDir,
		tasks:   make(map[string]*TaskProgress),
	}
	h.scan()
	return h
}

// ── 作品列表 ──

func (h *GalleryHandler) scan() {
	h.mu.Lock()
	defer h.mu.Unlock()

	h.items = nil
	entries, err := os.ReadDir(h.rootDir)
	if err != nil {
		return
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err != nil {
			continue
		}
		name := entry.Name()
		ext := strings.ToLower(filepath.Ext(name))
		mimeType := detectMime(ext)

		item := GalleryItem{
			Name:      name,
			Path:      filepath.Join(h.rootDir, name),
			Size:      info.Size(),
			SizeHuman: formatSize(info.Size()),
			ModTime:   info.ModTime().Format(time.RFC3339),
			IsVideo:   strings.HasPrefix(mimeType, "video/"),
			IsAudio:   strings.HasPrefix(mimeType, "audio/"),
			IsImage:   strings.HasPrefix(mimeType, "image/"),
			MimeType:  mimeType,
			URL:       fmt.Sprintf("/api/v1/files/%s", name),
		}
		h.items = append(h.items, item)
	}

	sort.Slice(h.items, func(i, j int) bool {
		return h.items[i].ModTime > h.items[j].ModTime
	})
	h.lastScan = time.Now()
}

func (h *GalleryHandler) refresh() { h.scan() }

func (h *GalleryHandler) getItems() []GalleryItem {
	h.mu.RLock()
	defer h.mu.RUnlock()

	if time.Since(h.lastScan) > 10*time.Second {
		h.mu.RUnlock()
		h.refresh()
		h.mu.RLock()
	}

	items := make([]GalleryItem, len(h.items))
	copy(items, h.items)
	return items
}

// ── 文件类型识别 ──

// classifyFile 识别文件类型和角色
func classifyFile(name string) (fileType string, role string) {
	ext := strings.ToLower(filepath.Ext(name))

	documentExts := map[string]bool{".pdf": true, ".pptx": true, ".ppt": true, ".docx": true, ".doc": true, ".txt": true}
	audioExts := map[string]bool{".mp3": true, ".wav": true, ".aac": true, ".m4a": true, ".flac": true, ".ogg": true, ".wma": true}
	imageExts := map[string]bool{".jpg": true, ".jpeg": true, ".png": true, ".gif": true, ".webp": true, ".bmp": true, ".svg": true}
	videoExts := map[string]bool{".mp4": true, ".webm": true, ".avi": true, ".mov": true, ".mkv": true, ".flv": true, ".wmv": true, ".m4v": true}

	if documentExts[ext] {
		return "document", "文档内容"
	}
	if audioExts[ext] {
		return "audio", "语音配音"
	}
	if imageExts[ext] {
		return "image", "图片素材"
	}
	if videoExts[ext] {
		return "video", "视频素材"
	}
	return "binary", "文件"
}

// ── 任务进度管理 ──

func (h *GalleryHandler) updateTask(taskID, title, stage string, percent int, message string) {
	h.tasksMu.Lock()
	defer h.tasksMu.Unlock()
	h.tasks[taskID] = &TaskProgress{
		TaskID:  taskID,
		Title:   title,
		Stage:   stage,
		Percent: percent,
		Message: message,
		Updated: time.Now().Format(time.RFC3339),
	}
}

func (h *GalleryHandler) getTasks() []*TaskProgress {
	h.tasksMu.RLock()

	// 先从内存 task 列表读取
	result := make([]*TaskProgress, 0, len(h.tasks))
	for _, t := range h.tasks {
		if t.Stage == "completed" || t.Stage == "failed" {
			updated, err := time.Parse(time.RFC3339, t.Updated)
			if err == nil && time.Since(updated) > 5*time.Minute {
				continue
			}
		}
		result = append(result, t)
	}
	h.tasksMu.RUnlock()

	// 再从磁盘进度目录读取（兼容旧 API 提交的任务）
	progressDir := "/tmp/computehub-video/progress"
	if entries, err := os.ReadDir(progressDir); err == nil {
		seen := make(map[string]bool)
		for _, t := range result {
			seen[t.TaskID] = true
		}
		for _, entry := range entries {
			name := entry.Name()
			if !strings.HasSuffix(name, ".json") || strings.HasSuffix(name, "_gw.log.json") || strings.HasSuffix(name, "_worker.log.json") {
				continue
			}
			taskID := strings.TrimSuffix(name, ".json")
			if seen[taskID] {
				continue
			}
			data, readErr := os.ReadFile(filepath.Join(progressDir, name))
			if readErr != nil {
				continue
			}
			var prog map[string]interface{}
			if json.Unmarshal(data, &prog) != nil {
				continue
			}
			title := ""
			if t, ok := prog["title"]; ok {
				title, _ = t.(string)
			}
			stage := ""
			if s, ok := prog["stage"]; ok {
				stage, _ = s.(string)
			}
			pct := 0
			if p, ok := prog["percent"]; ok {
				if pf, ok := p.(float64); ok {
					pct = int(pf)
				}
			}
			msg := ""
			if m, ok := prog["message"]; ok {
				msg, _ = m.(string)
			}
			// 只显示非 completed/failed 的任务
			// 或者 5 分钟内完成的
			if stage == "completed" || stage == "failed" {
				continue
			}
			result = append(result, &TaskProgress{
				TaskID:  taskID,
				Title:   title,
				Stage:   stage,
				Percent: pct,
				Message: msg,
				Updated: time.Now().Format(time.RFC3339),
			})
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].Updated > result[j].Updated
	})
	return result
}

// ── HTTP Handlers ──

func (h *GalleryHandler) HandleGallery(w http.ResponseWriter, r *http.Request) {
	accept := r.Header.Get("Accept")
	if strings.Contains(accept, "application/json") || r.URL.Query().Get("format") == "json" {
		h.handleGalleryJSON(w, r)
		return
	}
	h.handleGalleryHTML(w, r)
}

func (h *GalleryHandler) handleGalleryJSON(w http.ResponseWriter, r *http.Request) {
	items := h.getItems()
	tasks := h.getTasks()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    items,
		"total":   len(items),
		"tasks":   tasks,
	})
}

func (h *GalleryHandler) handleGalleryHTML(w http.ResponseWriter, r *http.Request) {
	items := h.getItems()
	tmpl := template.Must(template.New("gallery").Parse(galleryHTML))
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	tmpl.Execute(w, map[string]interface{}{
		"Items":      items,
		"Total":      len(items),
		"ServerTime": time.Now().Format("2006-01-02 15:04:05"),
	})
}

// HandleGenerateFromGallery 从已经上传到 Gallery 的文件生成视频
// 接收 JSON: {"filenames": ["xxx.pdf", "voice.wav", "cover.jpg"]}
func (h *GalleryHandler) HandleGenerateFromGallery(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, map[string]interface{}{"success": false, "error": "Only POST allowed"})
		return
	}

	body, _ := io.ReadAll(r.Body)
	defer r.Body.Close()

	var req struct {
		Filenames []string `json:"filenames"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		writeJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if len(req.Filenames) == 0 {
		writeJSON(w, map[string]interface{}{"success": false, "error": "filenames is required"})
		return
	}

	// 从 gallery 目录中找这些文件
	var docPath string
	var docTitle string
	var selected []UploadedFileInfo

	for _, name := range req.Filenames {
		name = filepath.Base(name)
		if name == "." || name == "/" || strings.Contains(name, "..") {
			continue
		}
		fullPath := filepath.Join(h.rootDir, name)
		info, err := os.Stat(fullPath)
		if err != nil {
			continue
		}
		fileType, role := classifyFile(name)
		selected = append(selected, UploadedFileInfo{
			Name:     name,
			Size:     info.Size(),
			FileType: fileType,
			Role:     role,
			Ext:      strings.ToLower(filepath.Ext(name)),
		})
		if fileType == "document" && docPath == "" {
			docPath = fullPath
			docTitle = strings.TrimSuffix(name, filepath.Ext(name))
		}
	}

	if docPath == "" && len(selected) > 0 {
		docPath = filepath.Join(h.rootDir, selected[0].Name)
		docTitle = strings.TrimSuffix(selected[0].Name, selected[0].Ext)
	}

	if docPath == "" {
		writeJSON(w, map[string]interface{}{"success": false, "error": "No valid files found in gallery"})
		return
	}

	taskID := fmt.Sprintf("video_%d", time.Now().UnixNano()/1000000)
	h.updateTask(taskID, docTitle, "pending", 0, "任务已提交，等待处理...")
	go h.runVideoPipeline(taskID, docPath, docTitle)

	writeJSON(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"task_id":    taskID,
			"title":      docTitle,
		},
	})
}

func (h *GalleryHandler) HandleGenerateFromText(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, map[string]interface{}{"success": false, "error": "Only POST allowed"})
		return
	}
	body, _ := io.ReadAll(r.Body)
	defer r.Body.Close()
	var req struct {
		Text     string `json:"text"`
		Duration int    `json:"duration"`
		Bg       string `json:"bg"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		writeJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}
	if req.Text == "" {
		writeJSON(w, map[string]interface{}{"success": false, "error": "text is required"})
		return
	}
	if req.Duration <= 0 {
		req.Duration = 5
	}
	if req.Bg == "" {
		req.Bg = "#302b63"
	}
	taskID := fmt.Sprintf("text_%d", time.Now().UnixNano()/1000000)
	title := req.Text
	runes := []rune(title)
	if len(runes) > 30 {
		title = string(runes[:30]) + "..."
	}
	title = strings.TrimSpace(strings.ReplaceAll(title, "\n", " "))

	tmpDir := "/tmp/computehub-video/text"
	os.MkdirAll(tmpDir, 0755)
	tmpFile := filepath.Join(tmpDir, taskID+".txt")
	os.WriteFile(tmpFile, []byte(req.Text), 0644)

	h.updateTask(taskID, title, "pending", 0, "文字已提交，正在生成...")
	go h.runTextPipeline(taskID, tmpFile, title, req.Duration, req.Bg)

	writeJSON(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"task_id": taskID,
			"title":   title,
			"message": "文字已提交，正在生成视频...",
		},
	})
}

// runTextPipeline 后台运行文字转视频（ffmpeg drawtext + edge-tts 语音合成）
func (h *GalleryHandler) runTextPipeline(taskID, textFile, title string, duration int, bg string) {
	defer func() {
		if r := recover(); r != nil {
			errMsg := fmt.Sprintf("❌ 任务崩溃: %v", r)
			logWithTimestamp("❌ 任务崩溃: %v", r)
			h.updateTask(taskID, title, "failed", 0, errMsg)
		}
	}()
	h.updateTask(taskID, title, "tts", 20, "正在合成语音...")

	// 读文字内容
	data, err := os.ReadFile(textFile)
	if err != nil {
		h.updateTask(taskID, title, "failed", 0, fmt.Sprintf("❌ 读取文字失败: %v", err))
		return
	}
	rawText := strings.TrimSpace(string(data))

	logFile := fmt.Sprintf("/tmp/computehub-video/progress/%s_gw.log", taskID)
	os.MkdirAll("/tmp/computehub-video/progress", 0755)
	logF, _ := os.Create(logFile)

	logWithTimestamp("📝 Text video task: task_id=%s text=%q duration=%d bg=%s", taskID, rawText[:min(len(rawText), 50)], duration, bg)

	if logF != nil {
		fmt.Fprintf(logF, "📝 Text video task: task_id=%s\ntext: %s\nduration: %d\nbg: %s\n", taskID, rawText, duration, bg)
	}

	// ── 1. 语音合成（edge-tts） ──
	ttsAudio := fmt.Sprintf("/tmp/computehub-video/text/%s_tts.mp3", taskID)
	os.MkdirAll("/tmp/computehub-video/text", 0755)

	ttsVoice := "zh-CN-XiaoxiaoNeural"
	// 检测是否包含英文/数字较多，可切换混合语音，暂时固定用 Xiaoxiao
	ttsCmd := exec.Command("python3", "-m", "edge_tts",
		"--text", rawText,
		"--voice", ttsVoice,
		"--write-media", ttsAudio,
	)
	if logF != nil {
		ttsCmd.Stdout = logF
		ttsCmd.Stderr = logF
	}

	logWithTimestamp("🎤 TTS: voice=%s", ttsVoice)
	if logF != nil {
		fmt.Fprintf(logF, "🎤 TTS: voice=%s\n", ttsVoice)
	}

	if err := ttsCmd.Run(); err != nil {
		h.updateTask(taskID, title, "failed", 0, fmt.Sprintf("❌ 语音合成失败: %v", err))
		return
	}

	// ── 2. 获取音频时长 ──
	audioDuration := float64(duration)
	if stat, err := os.Stat(ttsAudio); err == nil && stat.Size() > 0 {
		// 用 ffprobe 获取时长
		probe := exec.Command("ffprobe", "-v", "error", "-show_entries", "format=duration",
			"-of", "default=noprint_wrappers=1:nokey=1", ttsAudio)
		out, err := probe.Output()
		if err == nil {
			durStr := strings.TrimSpace(string(out))
			if d, parseErr := strconv.ParseFloat(durStr, 64); parseErr == nil && d > 1 {
				audioDuration = d
			}
		}
	}
	// 视频时长 = 音频时长（至少 3 秒）
	videoDuration := int(audioDuration) + 1
	if videoDuration < 3 {
		videoDuration = 3
	}

	h.updateTask(taskID, title, "rendering", 50, fmt.Sprintf("正在渲染视频（%.0f秒）...", audioDuration))

	// 构建输出路径 — 保留中文/字母/数字，其他特殊字符替换为 _
	outputName := fmt.Sprintf("%s_%s.mp4", title, taskID)
	ext := ".mp4"
	safeBase := strings.TrimSuffix(outputName, ext)
	safeBase = strings.Map(func(r rune) rune {
		if r >= 0x4e00 && r <= 0x9fff {
			return r
		}
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') {
			return r
		}
		if r == '-' || r == '_' {
			return r
		}
		return '_'
	}, safeBase)
	for strings.Contains(safeBase, "__") {
		safeBase = strings.ReplaceAll(safeBase, "__", "_")
	}
	safeBase = strings.Trim(safeBase, "._")
	if safeBase == "" {
		safeBase = taskID
	}
	outputName = safeBase + ext
	outputPath := filepath.Join(h.rootDir, outputName)
	outputPath = strings.ReplaceAll(outputPath, "//", "/")

	// ── 3. 渲染视频（带动画背景 + 居中文字 + 配音） ──
	fontFile := "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
	if _, err := os.Stat(fontFile); err != nil {
		fontFile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
	}

	lines := breakLines(rawText, 36, 42)
	if len(lines) == 0 {
		lines = []string{" "}
	}

	totalLines := len(lines)
	lineHeight := 52
	totalTextHeight := totalLines * lineHeight
	startY := (1080 - totalTextHeight) / 2

	// 构建 drawtext 滤镜链
	drawtextFilters := make([]string, 0, totalLines)
	for i, line := range lines {
		yPos := startY + i*lineHeight
		if yPos < 0 {
			yPos = 0
		}
		if yPos > 1040 {
			yPos = 1040
		}
		escaped := strings.ReplaceAll(line, "\\", "\\\\\\\\")
		escaped = strings.ReplaceAll(escaped, ":", "\\\\:")
		escaped = strings.ReplaceAll(escaped, "'", "\\\\'")
		filter := fmt.Sprintf(
			"drawtext=text='%s':fontfile=%s:fontsize=36:fontcolor=white:x=(w-text_w)/2:y=%d",
			escaped, fontFile, yPos,
		)
		drawtextFilters = append(drawtextFilters, filter)
	}

	// 先渲染无声音视频
	rawVideo := fmt.Sprintf("/tmp/computehub-video/text/%s_nosound.mp4", taskID)
	ffmpegArgs := []string{
		"-y",
		"-f", "lavfi",
		"-i", fmt.Sprintf("color=c=%s:s=1920x1080:d=%d:r=30", bg, videoDuration),
		"-vf", strings.Join(drawtextFilters, ","),
		"-c:v", "libx264",
		"-preset", "ultrafast",
		"-pix_fmt", "yuv420p",
		rawVideo,
	}

	if logF != nil {
		fmt.Fprintf(logF, "🎬 ffmpeg video: %s\n", strings.Join(ffmpegArgs, " "))
	}

	cmd := exec.Command("ffmpeg", ffmpegArgs...)
	if logF != nil {
		cmd.Stdout = logF
		cmd.Stderr = logF
	}
	if err := cmd.Run(); err != nil {
		h.updateTask(taskID, title, "failed", 0, fmt.Sprintf("❌ 视频渲染失败: %v", err))
		return
	}

	// ── 4. 混合配音 ──
	h.updateTask(taskID, title, "rendering", 80, "正在合成配音...")

	muxArgs := []string{
		"-y",
		"-i", rawVideo,
		"-i", ttsAudio,
		"-c:v", "copy",
		"-c:a", "aac",
		"-b:a", "128k",
		"-map", "0:v:0",
		"-map", "1:a:0",
		"-shortest",
		outputPath,
	}

	if logF != nil {
		fmt.Fprintf(logF, "🎬 ffmpeg mux: %s\n", strings.Join(muxArgs, " "))
	}

	muxCmd := exec.Command("ffmpeg", muxArgs...)
	if logF != nil {
		muxCmd.Stdout = logF
		muxCmd.Stderr = logF
	}
	if err := muxCmd.Run(); err != nil {
		h.updateTask(taskID, title, "failed", 0, fmt.Sprintf("❌ 配音合成失败: %v", err))
		return
	}

	// ── 5. 清理临时文件 ──
	os.Remove(ttsAudio)
	os.Remove(rawVideo)
	if logF != nil {
		logF.Close()
	}

	// 检查输出
	if stat, statErr := os.Stat(outputPath); statErr == nil && stat.Size() > 0 {
		h.recordToPipelineRepo(taskID, title, textFile, outputName)
		h.updateTask(taskID, title, "completed", 100, fmt.Sprintf("✅ 配音视频已生成: %s", outputName))
		h.refresh()
		os.Remove(textFile)
		return
	}

	h.refresh()
	h.updateTask(taskID, title, "completed", 100, "✅ 处理完成，请刷新作品列表")
	h.refresh()
	os.Remove(textFile)
}

// breakLines 简单换行算法：按中英文混合拆分
func breakLines(text string, charsPerLine int, maxLines int) []string {
	lines := []string{}
	paragraphs := strings.Split(text, "\n")

	for _, para := range paragraphs {
		para = strings.TrimSpace(para)
		if para == "" {
			continue
		}

		runes := []rune(para)
		for len(runes) > 0 {
			if len(lines) >= maxLines {
				if len(runes) > 3 {
					lines = append(lines, string(runes[:min(len(runes), charsPerLine-3)])+"...")
				}
				return lines
			}

			if len(runes) <= charsPerLine {
				lines = append(lines, string(runes))
				runes = nil
			} else {
				lines = append(lines, string(runes[:charsPerLine]))
				runes = runes[charsPerLine:]
			}
		}
	}
	return lines
}

// HandleTaskStatus 获取任务状态列表
func (h *GalleryHandler) HandleTaskStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"success":false,"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	tasks := h.getTasks()
	writeJSON(w, map[string]interface{}{
		"success": true,
		"data":    tasks,
		"total":   len(tasks),
	})
}

// runVideoPipeline 后台运行视频管线
func (h *GalleryHandler) runVideoPipeline(taskID, docPath, title string) {
	defer func() {
		if r := recover(); r != nil {
			errMsg := fmt.Sprintf("❌ 任务崩溃: %v", r)
			logWithTimestamp("❌ 任务崩溃: %v", r)
			h.updateTask(taskID, title, "failed", 0, errMsg)
		}
	}()
	h.updateTask(taskID, title, "parsing", 10, "正在解析文档...")

	// 找到 worker 脚本
	workerScript := findVideoWorkerScript()
	if workerScript == "" {
		h.updateTask(taskID, title, "failed", 0, "❌ video_worker.py 未找到")
		return
	}

	// 构建参数
	params := map[string]interface{}{
		"task_id":  taskID,
		"doc_path": docPath,
		"title":    title,
	}
	paramsJSON, _ := json.Marshal(params)

	// 进度目录
	os.MkdirAll("/tmp/computehub-video/progress", 0755)

	// 进度文件 —— worker 写入
	progressFile := fmt.Sprintf("/tmp/computehub-video/progress/%s.json", taskID)

	// 启动 worker
	h.updateTask(taskID, title, "tts", 40, "正在生成语音...")
	// 临时写一个占位进度，让 worker 覆盖
	os.WriteFile(progressFile, []byte(fmt.Sprintf(`{"task_id":"%s","stage":"tts","percent":40,"message":"语音合成中..."}`, taskID)), 0644)

	cmd := exec.Command("nohup", "python3", workerScript, string(paramsJSON))
	logFile := fmt.Sprintf("/tmp/computehub-video/progress/%s_gw.log", taskID)
	logF, err := os.Create(logFile)
	if err == nil {
		cmd.Stdout = logF
		cmd.Stderr = logF
	}

	h.updateTask(taskID, title, "rendering", 70, "正在合成视频...")

	if err := cmd.Start(); err != nil {
		h.updateTask(taskID, title, "failed", 0, fmt.Sprintf("❌ 启动失败: %v", err))
		return
	}

	logWithTimestamp("🎬 Gallery video task: task_id=%s doc=%s pid=%d", taskID, docPath, cmd.Process.Pid)

	// 等待完成
	go func() {
		err := cmd.Wait()
		if logF != nil {
			logF.Close()
		}

		if err != nil {
			h.updateTask(taskID, title, "failed", 0, fmt.Sprintf("❌ 处理失败: %v", err))
			return
		}

		// 检查进度文件里的最终结果
		if data, readErr := os.ReadFile(progressFile); readErr == nil {
			var prog map[string]interface{}
			if json.Unmarshal(data, &prog) == nil {
				if output, ok := prog["output"]; ok {
					// 写入 git pipeline repo
					h.recordToPipelineRepo(taskID, title, docPath, fmt.Sprintf("%v", output))
					h.updateTask(taskID, title, "completed", 100, fmt.Sprintf("✅ 视频已生成: %v", output))
					h.refresh()
					return
				}
			}
		}

		// fallback: 去 gallery 目录找最新的 mp4
		h.refresh()
		items := h.getItems()
		if len(items) > 0 {
			latest := items[0]
			if latest.IsVideo {
				h.recordToPipelineRepo(taskID, title, docPath, latest.Name)
				h.updateTask(taskID, title, "completed", 100, fmt.Sprintf("✅ 视频已生成: %s", latest.Name))
				return
			}
		}

		h.updateTask(taskID, title, "completed", 100, "✅ 处理完成，请刷新作品列表")
		h.refresh()
	}()
}

// recordToPipelineRepo 记录任务到 pipeline-repo
func (h *GalleryHandler) recordToPipelineRepo(taskID, title, docPath, outputName string) {
	runDir := fmt.Sprintf("/home/computehub/pipeline-repo/runs/%s_%s", time.Now().Format("2006-01-02"), taskID)
	os.MkdirAll(runDir+"/input", 0755)
	os.MkdirAll(runDir+"/output", 0755)
	os.MkdirAll(runDir+"/logs", 0755)

	manifest := map[string]interface{}{
		"id":          taskID,
		"title":       title,
		"created":     time.Now().Format(time.RFC3339),
		"status":      "completed",
		"source_file": docPath,
		"output_file": outputName,
	}

	data, _ := json.MarshalIndent(manifest, "", "  ")
	os.WriteFile(runDir+"/manifest.json", data, 0644)

	// 尝试 git commit
	gitCmds := []string{
		fmt.Sprintf("cd /home/computehub/pipeline-repo && git add runs/ && git commit -m 'task: %s - %s'", title, taskID),
	}
	for _, cmd := range gitCmds {
		exec.Command("bash", "-c", cmd).Run()
	}
}

// ── 文件下载 ──

func (h *GalleryHandler) HandleFile(w http.ResponseWriter, r *http.Request) {
	filename := strings.TrimPrefix(r.URL.Path, "/api/v1/files/")
	if filename == "" || strings.HasPrefix(filename, ".") || strings.Contains(filename, "../") || strings.Contains(filename, "..\\") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	filePath := filepath.Join(h.rootDir, filepath.Clean(filename))
	absRoot, _ := filepath.Abs(h.rootDir)
	absFile, _ := filepath.Abs(filePath)
	if !strings.HasPrefix(absFile, absRoot) {
		http.Error(w, "Access denied", http.StatusForbidden)
		return
	}

	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		http.Error(w, "File not found", http.StatusNotFound)
		return
	}

	ext := strings.ToLower(filepath.Ext(filename))
	mimeType := detectMime(ext)

	w.Header().Set("Content-Type", mimeType)
	w.Header().Set("Content-Disposition", fmt.Sprintf(`inline; filename="%s"`, filename))
	w.Header().Set("Accept-Ranges", "bytes")
	http.ServeFile(w, r, filePath)
}

// ── 上传（向后兼容） ──

func (h *GalleryHandler) HandleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// 最大 500MB 上传限制
	r.Body = http.MaxBytesReader(w, r.Body, 500<<20)

	if err := r.ParseMultipartForm(500 << 20); err != nil {
		http.Error(w, fmt.Sprintf("Parse error: %v", err), http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, fmt.Sprintf("File error: %v", err), http.StatusBadRequest)
		return
	}
	defer file.Close()

	filename := filepath.Base(header.Filename)
	if filename == "." || filename == "/" || strings.Contains(filename, "..") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	destPath := filepath.Join(h.rootDir, filename)
	if _, err := os.Stat(destPath); err == nil {
		// Known binary names: overwrite directly (no timestamp suffix)
		// This allows repeated gallery-upload.sh runs to overwrite the same binary
		binaryPrefixes := []string{
			"computehub-", "computehub-worker-", "computehub-gateway-",
			"computehub-tui-", "compute-worker-", "compute-gateway-",
			"compute-tui-", "compute-",
		}
		isBinary := false
		for _, prefix := range binaryPrefixes {
			if strings.HasPrefix(filename, prefix) {
				isBinary = true
				break
			}
		}
		if !isBinary {
			// Non-binary: add timestamp to avoid collision
			ext := filepath.Ext(filename)
			base := strings.TrimSuffix(filename, ext)
			filename = fmt.Sprintf("%s_%d%s", base, time.Now().Unix(), ext)
			destPath = filepath.Join(h.rootDir, filename)
		}
		// isBinary == true → use original filename (overwrite in place)
	}

	dst, err := os.Create(destPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("Create error: %v", err), http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	written, err := io.Copy(dst, file)
	if err != nil {
		os.Remove(destPath)
		http.Error(w, fmt.Sprintf("Write error: %v", err), http.StatusInternalServerError)
		return
	}

	h.refresh()

	fileType, role := classifyFile(filename)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"name":      filename,
			"size":      written,
			"size_str":  formatSize(written),
			"url":       fmt.Sprintf("/api/v1/files/%s", filename),
			"file_type": fileType,
			"role":      role,
		},
	})
}

// ── 删除 ──

func (h *GalleryHandler) HandleDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var filename string
	body, _ := io.ReadAll(r.Body)
	defer r.Body.Close()
	if len(body) > 0 {
		var req struct {
			Name string `json:"name"`
		}
		if json.Unmarshal(body, &req) == nil && req.Name != "" {
			filename = req.Name
		}
	}
	if filename == "" {
		filename = r.URL.Query().Get("name")
	}

	if filename == "" || strings.HasPrefix(filename, ".") || strings.Contains(filename, "../") || strings.Contains(filename, "..\\") {
		writeJSON(w, map[string]interface{}{"success": false, "error": "Invalid filename"})
		return
	}

	filePath := filepath.Join(h.rootDir, filepath.Clean(filename))
	absRoot, _ := filepath.Abs(h.rootDir)
	absFile, _ := filepath.Abs(filePath)
	if !strings.HasPrefix(absFile, absRoot) {
		writeJSON(w, map[string]interface{}{"success": false, "error": "Access denied"})
		return
	}

	if err := os.Remove(filePath); err != nil {
		writeJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}

	h.refresh()
	writeJSON(w, map[string]interface{}{"success": true, "data": map[string]string{"name": filename}})
}

// ── 辅助函数 ──

func detectMime(ext string) string {
	mimeMap := map[string]string{
		".mp4": "video/mp4", ".webm": "video/webm", ".avi": "video/x-msvideo",
		".mov": "video/quicktime", ".mkv": "video/x-matroska", ".flv": "video/x-flv",
		".wmv": "video/x-ms-wmv", ".m4v": "video/x-m4v", ".3gp": "video/3gpp",
		".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
		".aac": "audio/aac", ".flac": "audio/flac", ".m4a": "audio/mp4", ".wma": "audio/x-ms-wma",
		".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
		".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp", ".svg": "image/svg+xml",
		".pdf": "application/pdf", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
		".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		".txt": "text/plain", ".json": "application/json", ".html": "text/html", ".htm": "text/html",
		".zip": "application/zip", ".tar": "application/x-tar", ".gz": "application/gzip",
	}
	if mime, ok := mimeMap[ext]; ok {
		return mime
	}
	return "application/octet-stream"
}

func formatSize(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

func writeJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

// ── 注册路由 ──

func RegisterGallery(config *GalleryConfig) {
	h := NewGalleryHandler(config)

	http.HandleFunc("/gallery", h.HandleGallery)
	http.HandleFunc("/api/v1/gallery", h.HandleGallery)
	http.HandleFunc("/api/v1/gallery/upload", h.HandleUpload)
	http.HandleFunc("/api/v1/gallery/delete", h.HandleDelete)
	http.HandleFunc("/api/v1/gallery/generate", h.HandleGenerateFromGallery)
	http.HandleFunc("/api/v1/gallery/generate-text", h.HandleGenerateFromText)
	http.HandleFunc("/api/v1/gallery/tasks", h.HandleTaskStatus)
	http.HandleFunc("/api/v1/files/", h.HandleFile)

	logWithTimestamp("🎬 Gallery v2 registered:")
	logWithTimestamp("   - /                          → Gallery v2 首页")
	logWithTimestamp("   - /gallery                   → 作品广场")
	logWithTimestamp("   - /api/v1/gallery            → JSON 接口")
	logWithTimestamp("   - /api/v1/gallery/upload     → 文件上传")
	logWithTimestamp("   - /api/v1/gallery/delete     → 文件删除")
	logWithTimestamp("   - /api/v1/gallery/generate   → 上传+生成视频")
	logWithTimestamp("   - /api/v1/gallery/generate-text → 文字直出视频")
	logWithTimestamp("   - /api/v1/gallery/tasks      → 任务进度查询")
	logWithTimestamp("   - /api/v1/files/*            → 文件下载/预览")
	logWithTimestamp("📂 Gallery root: %s", h.rootDir)
}

// ════════════════════════════════════════════════════════════════════
// HTML 模板
// ════════════════════════════════════════════════════════════════════

const galleryHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎬 小智影业 · 作品广场</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
        }

        /* ── Header ── */
        .header {
            padding: 24px 32px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .header h1 {
            font-size: 26px;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .subtitle { color: #888; margin-top: 4px; font-size: 13px; }
        .header .stats {
            display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: #aaa;
        }
        .header .stats strong, .header .stats em { color: #f7971e; font-style: normal; }

        /* ── 上传区 ── */

        .upload-section {
            margin: 16px 32px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 20px;
        }
        .upload-zone {
            padding: 28px;
            border: 2px dashed rgba(255,255,255,0.12);
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: #f7971e;
            background: rgba(247,151,30,0.06);
        }
        .upload-zone .icon { font-size: 32px; }
        .upload-zone p { color: #888; font-size: 13px; margin-top: 4px; }
        .upload-zone input[type=file] { display: none; }

        /* ── 文件列表 ── */
        .file-list { margin-top: 12px; }
        .file-list.hidden { display: none; }
        .file-item {
            display: flex; align-items: center;
            padding: 8px 12px; margin-top: 4px;
            background: rgba(255,255,255,0.04);
            border-radius: 8px;
            gap: 10px;
        }
        .file-item .icon { font-size: 18px; width: 28px; text-align: center; }
        .file-item .name { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .file-item .size { font-size: 11px; color: #888; min-width: 60px; text-align: right; }
        .file-item .badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-weight: 600;
        }
        .badge-document { background: rgba(33,150,243,0.18); color: #42a5f5; }
        .badge-audio { background: rgba(76,175,80,0.18); color: #66bb6a; }
        .badge-image { background: rgba(255,152,0,0.18); color: #ffa726; }
        .badge-video { background: rgba(247,151,30,0.18); color: #f7971e; }
        .badge-binary { background: rgba(156,39,176,0.18); color: #ce93d8; }
        .badge-success { background: rgba(76,175,80,0.18); color: #66bb6a; font-size: 11px; }

        .file-actions {
            display: flex; gap: 8px; margin-top: 12px; align-items: center;
        }
        .file-actions .file-count { font-size: 13px; color: #888; }
        .btn {
            padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
            font-size: 13px; font-weight: 600; transition: all 0.2s;
        }
        .btn-generate {
            background: linear-gradient(90deg, #f7971e, #ffd200);
            color: #1a1a2e;
        }
        .btn-generate:hover { opacity: 0.9; transform: scale(1.02); }
        .btn-generate:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
        .btn-clear {
            background: rgba(255,255,255,0.08); color: #ccc;
        }
        .btn-clear:hover { background: rgba(255,255,255,0.15); }

        /* ── 进度面板 ── */
        .task-section { margin: 0 32px 16px; }
        .task-section.hidden { display: none; }
        .task-section h3 { font-size: 14px; color: #aaa; margin-bottom: 8px; }
        .task-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px; padding: 14px 16px; margin-bottom: 8px;
        }
        .task-card .task-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
        }
        .task-card .task-title { font-size: 14px; font-weight: 600; }
        .task-card .task-status {
            font-size: 12px; padding: 2px 10px; border-radius: 10px;
        }
        .task-status.pending { background: rgba(255,152,0,0.15); color: #ffa726; }
        .task-status.running { background: rgba(33,150,243,0.15); color: #42a5f5; }
        .task-status.completed { background: rgba(76,175,80,0.15); color: #66bb6a; }
        .task-status.failed { background: rgba(244,67,54,0.15); color: #ef5350; }
        .task-progress-bar {
            height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden;
        }
        .task-progress-fill {
            height: 100%; background: linear-gradient(90deg, #f7971e, #ffd200);
            transition: width 0.5s ease;
        }
        .task-card .task-message { font-size: 12px; color: #888; margin-top: 6px; }

        /* ── 搜索/筛选工具栏 ── */
        .toolbar {
            display: flex; gap: 10px; padding: 12px 32px; flex-wrap: wrap;
            align-items: center;
        }
        .search-box {
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px; padding: 8px 14px; color: #e0e0e0;
            font-size: 13px; min-width: 200px; outline: none;
        }
        .search-box:focus { border-color: #f7971e; }

        /* ── AI 助手搜索栏 ── */
        .ai-bar {
            margin: 12px 32px; padding: 10px 16px;
            background: rgba(124,58,237,0.06);
            border: 1px solid rgba(124,58,237,0.15);
            border-radius: 12px;
        }
        .ai-search { display: flex; gap: 8px; align-items: center; }
        .ai-icon { font-size: 20px; }
        .ai-search input {
            flex: 1; padding: 10px 14px; border-radius: 8px;
            border: 1px solid rgba(124,58,237,0.3);
            background: rgba(255,255,255,0.05); color: #e0e0e0;
            font-size: 14px; outline: none;
        }
        .ai-search input:focus { border-color: #7c3aed; }
        .ai-btn {
            padding: 10px 20px; border-radius: 8px; border: none;
            background: #7c3aed; color: #fff; cursor: pointer;
            font-size: 14px; font-weight: 600; white-space: nowrap;
        }
        .ai-btn:hover { background: #6d28d9; }
        .ai-reply {
            margin-top: 10px; padding: 10px 14px;
            background: rgba(255,255,255,0.04); border-radius: 8px;
            font-size: 14px; line-height: 1.6; display: none;
            color: #ccc; max-height: 300px; overflow-y: auto;
        }

        .filter-btns { display: flex; gap: 6px; flex-wrap: wrap; }
        .filter-btn, .sort-btn {
            background: rgba(255,255,255,0.06); border: none; border-radius: 6px;
            padding: 6px 12px; color: #999; font-size: 12px; cursor: pointer; transition: all 0.2s;
        }
        .filter-btn:hover, .sort-btn:hover { background: rgba(255,255,255,0.12); }
        .filter-btn.active { background: rgba(247,151,30,0.2); color: #f7971e; }

        /* ── 作品网格 ── */
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 14px; padding: 8px 32px 24px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 10px; overflow: hidden;
            border: 1px solid rgba(255,255,255,0.06);
            transition: all 0.25s ease;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(247,151,30,0.25);
            box-shadow: 0 6px 24px rgba(247,151,30,0.08);
        }
        .card-preview {
            position: relative; background: #1a1a2e;
            aspect-ratio: 16/9; display: flex;
            align-items: center; justify-content: center; overflow: hidden;
        }
        .card-preview video, .card-preview img {
            width: 100%; height: 100%; object-fit: cover;
        }
        .card-preview .icon { font-size: 40px; opacity: 0.4; }
        .card-info { padding: 10px 12px; }
        .card-info .name {
            font-size: 13px; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .card-info .meta {
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 4px; font-size: 11px; color: #888;
        }
        .card-info .actions {
            display: flex; gap: 4px; margin-top: 8px;
        }
        .card-info .actions a, .card-info .actions button {
            flex: 1; text-align: center; padding: 6px 8px; border-radius: 6px;
            font-size: 12px; text-decoration: none; border: none; cursor: pointer;
            transition: all 0.2s;
        }
        .btn-play {
            background: linear-gradient(90deg, #f7971e, #ffd200);
            color: #1a1a2e !important; font-weight: 600;
        }
        .btn-play:hover { opacity: 0.9; }
        .btn-download { background: rgba(255,255,255,0.08); color: #bbb !important; }
        .btn-download:hover { background: rgba(255,255,255,0.15); }
        .btn-delete {
            background: rgba(244,67,54,0.12); color: #ef5350 !important;
            flex: 0 0 auto !important; padding: 6px 10px !important;
        }
        .btn-delete:hover { background: rgba(244,67,54,0.25); }

        .empty {
            grid-column: 1 / -1; text-align: center;
            padding: 60px 32px; color: #666;
        }
        .empty .big-icon { font-size: 56px; margin-bottom: 16px; }

        .footer { text-align: center; padding: 16px; color: #444; font-size: 12px; }

        /* ── 模态框 ── */
        .modal {
            display: none; position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.92); z-index: 1000;
            align-items: center; justify-content: center; padding: 32px;
        }
        .modal.active { display: flex; }
        .modal video { max-width: 100%; max-height: 85vh; border-radius: 8px; }
        .modal .close {
            position: absolute; top: 16px; right: 24px;
            font-size: 28px; color: #fff; cursor: pointer; opacity: 0.6;
        }
        .modal .close:hover { opacity: 1; }

        /* ── 删除确认 ── */
        .confirm-dialog {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 2000;
            display: none; align-items: center; justify-content: center;
        }
        .confirm-dialog.active { display: flex; }
        .confirm-box {
            background: #1e1e3a; border-radius: 12px;
            padding: 24px; max-width: 400px; width: 90%;
            border: 1px solid rgba(244,67,54,0.3);
        }
        .confirm-box h3 { font-size: 16px; margin-bottom: 8px; }
        .confirm-box p { font-size: 13px; color: #888; margin-bottom: 12px; }
        .confirm-box .name-display { font-size: 14px; color: #ef5350; margin-bottom: 16px; word-break: break-all; }
        .confirm-box .btns { display: flex; gap: 8px; }
        .confirm-box .btns button {
            flex: 1; padding: 10px; border-radius: 8px; border: none;
            font-size: 13px; cursor: pointer; transition: all 0.2s;
        }
        .btn-confirm-delete { background: #ef5350; color: #fff; }
        .btn-confirm-delete:hover { background: #e53935; }
        .btn-cancel-delete { background: rgba(255,255,255,0.08); color: #ccc; }
        .btn-cancel-delete:hover { background: rgba(255,255,255,0.15); }

        /* ── Toast ── */
        .toast {
            position: fixed; bottom: 24px; right: 24px;
            background: rgba(0,0,0,0.85); color: #e0e0e0;
            padding: 12px 20px; border-radius: 8px; font-size: 13px;
            z-index: 3000; opacity: 0; transition: opacity 0.3s;
            pointer-events: none;
        }
        .toast.show { opacity: 1; }

        @media (max-width: 768px) {
            .header { padding: 16px 20px; }
    
        .text-input-section {
            margin: 16px 32px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 18px 20px;
        }
        .text-input-header {
            display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
        }
        .text-input-icon { font-size: 20px; }
        .text-input-title { font-size: 15px; font-weight: 600; color: #e0e0e0; }
        .text-input-subtitle { font-size: 12px; color: #666; margin-left: 8px; }
        .text-input-area textarea {
            width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px; color: #e0e0e0; font-size: 14px; padding: 12px;
            resize: vertical; min-height: 80px; max-height: 300px;
            font-family: inherit; outline: none; transition: border-color 0.2s;
            box-sizing: border-box;
        }
        .text-input-area textarea:focus { border-color: #f7971e; }
        .text-input-area textarea::placeholder { color: #555; }
        .text-input-controls {
            display: flex; align-items: center; gap: 14px; margin-top: 12px; flex-wrap: wrap;
        }
        .control-group {
            display: flex; align-items: center; gap: 6px;
        }
        .control-group label { font-size: 13px; color: #999; }
        .control-input {
            width: 56px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px; color: #e0e0e0; font-size: 13px; padding: 5px 8px;
            text-align: center; outline: none;
        }
        .control-input:focus { border-color: #f7971e; }
        .control-unit { font-size: 12px; color: #666; }
        .control-color {
            width: 32px; height: 32px; border: 2px solid rgba(255,255,255,0.15);
            border-radius: 6px; cursor: pointer; padding: 0; background: none;
        }
        .control-color::-webkit-color-swatch-wrapper { padding: 0; }
        .control-color::-webkit-color-swatch { border: none; border-radius: 4px; }

        @media (max-width: 768px) {
            .text-input-section { margin: 12px 16px; padding: 14px; }
            .text-input-controls { gap: 10px; }
        }
        .upload-section { margin: 12px 16px; padding: 14px; }
            .toolbar { padding: 10px 20px; }
            .gallery { padding: 8px 16px; grid-template-columns: 1fr; }
            .modal { padding: 8px; }
            .file-actions { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top">
            <h1>🎬 小智影业 · 作品广场</h1>
        </div>
        <p class="subtitle">ComputeHub 集群 · 自动视频生产</p>
        <div class="stats">
            <span>📦 共 <strong id="totalCount">{{.Total}}</strong> 件</span>
            <span>🎬 <em id="videoCount">0</em> 视频</span>
            <span>🖼 <em id="imageCount">0</em> 图片</span>
            <span>🎵 <em id="audioCount">0</em> 音频</span>
        </div>
    </div>

    <!-- ════ AI 助手搜索栏 ════ -->
    <div class="ai-bar">
        <div class="ai-search" id="aiSearchWrap">
            <span class="ai-icon">🤖</span>
            <input id="ai-search" type="text" placeholder="问小智：集群状态、查作品、下发任务..." autocomplete="off">
            <button class="ai-btn" onclick="askAI()">提问</button>
        </div>
        <div id="ai-reply" class="ai-reply"></div>
    </div>

    <!-- ════ 上传 + 生成区 ════ -->
    <div class="upload-section">
        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
            <div class="icon">📤</div>
            <p>点击上传或拖拽文件到此处</p>
            <p style="font-size:12px;color:#555;margin-top:2px;">
                支持 PDF / PPT / 音频 / 图片（最大 500MB）
            </p>
            <input type="file" id="fileInput" multiple
                   accept=".pdf,.pptx,.ppt,.docx,.doc,.txt,.mp3,.wav,.aac,.m4a,.flac,.ogg,.jpg,.jpeg,.png,.gif,.webp,.mp4,.mov"
                   onchange="handleFileSelect(this.files)">
        </div>

        <div class="file-list hidden" id="fileList">
            <div id="fileItems"></div>
        </div>
        <div class="file-actions" style="margin-top:12px;">
            <span class="file-count" id="fileCount">已选 0 个文件</span>
            <button class="btn btn-generate" id="btnGenerate" disabled onclick="generateVideo()">
                🎬 生成视频
            </button>
            <button class="btn btn-clear" onclick="clearFiles()">🗑 清空</button>
        </div>
    </div>

    <!-- ════ 文字直出 ════ -->
    <div class="text-input-section">
        <div class="text-input-header">
            <span class="text-input-icon">📝</span>
            <span class="text-input-title">文字直出视频</span>
            <span class="text-input-subtitle">输入文字，每行一个字幕画面，自动转视频</span>
        </div>
        <div class="text-input-area">
            <textarea id="textInput" placeholder="输入你的内容...&#10;&#10;例如：&#10;欢迎来到小智影业&#10;这里是一个全新的世界&#10;用 AI 创造无限可能" rows="5"></textarea>
        </div>
        <div class="text-input-controls">
            <div class="control-group">
                <label>⏱ 每段</label>
                <input type="number" id="durationInput" value="5" min="3" max="20" class="control-input">
                <span class="control-unit">秒</span>
            </div>
            <div class="control-group">
                <label>🎨 背景</label>
                <input type="color" id="bgColor" value="#302b63" class="control-color">
            </div>
            <button class="btn btn-generate" id="btnGenerateText" disabled onclick="generateFromText()">
                🎬 生成视频
            </button>
        </div>
    </div>

    <!-- ════ 任务进度 ════ -->
    <div class="task-section hidden" id="taskSection">
        <h3>📊 任务进度</h3>
        <div id="taskList"></div>
    </div>

    <!-- ════ 工具栏 ════ -->
    <div class="toolbar">
        <input class="search-box" id="searchBox" type="text" placeholder="🔍 搜索文件名..." oninput="filterGallery()">
        <div class="filter-btns">
            <button class="filter-btn active" data-filter="all" onclick="setFilter(this,'all')">全部</button>
            <button class="filter-btn" data-filter="video" onclick="setFilter(this,'video')">🎬 视频</button>
            <button class="filter-btn" data-filter="image" onclick="setFilter(this,'image')">🖼 图片</button>
            <button class="filter-btn" data-filter="audio" onclick="setFilter(this,'audio')">🎵 音频</button>
        </div>
        <button class="sort-btn" id="sortBtn" onclick="toggleSort()">📅 最新</button>
    </div>

    <!-- ════ 作品网格 ════ -->
    <div class="gallery" id="gallery">
        {{if eq .Total 0}}
        <div class="empty">
            <div class="big-icon">🎥</div>
            <p>还没有作品</p>
            <p style="margin-top:6px;font-size:13px;color:#555;">上传 PDF 或文档，点击「生成视频」自动出片</p>
        </div>
        {{end}}
    </div>

    <!-- ════ 模态框 ════ -->
    <div class="modal" id="playerModal" onclick="this.classList.remove('active')">
        <span class="close" onclick="document.getElementById('playerModal').classList.remove('active')">&times;</span>
        <video id="playerVideo" controls autoplay></video>
    </div>

    <div class="confirm-dialog" id="confirmDialog">
        <div class="confirm-box">
            <h3>确认删除</h3>
            <p>确定要删除这个文件吗？此操作不可撤销。</p>
            <div class="name-display" id="deleteFileName"></div>
            <div class="btns">
                <button class="btn-cancel-delete" onclick="closeConfirm()">取消</button>
                <button class="btn-confirm-delete" id="confirmDeleteBtn">删除</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <div class="footer">ComputeHub Gallery v2 · 小智影业</div>

    <script>
    // ══════════════════════════════════════════
    // 数据
    // ══════════════════════════════════════════
    let items = [];
    let currentFilter = 'all';
    let currentSort = 'date-desc';
    let currentSearch = '';
    let deleteTarget = null;

    // 已上传到 Gallery 的文件列表（前端缓存）
    var uploadedFiles = [];

    // 文件类型识别
    const FILE_TYPES = {
        document: ['.pdf', '.pptx', '.ppt', '.docx', '.doc', '.txt'],
        audio: ['.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.wma'],
        image: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'],
        video: ['.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v']
    };

    function classifyFile(name) {
        const ext = '.' + name.split('.').pop().toLowerCase();
        if (FILE_TYPES.document.includes(ext)) return { type: 'document', label: '📄 文档内容', badge: 'badge-document' };
        if (FILE_TYPES.audio.includes(ext)) return { type: 'audio', label: '🎤 语音配音', badge: 'badge-audio' };
        if (FILE_TYPES.image.includes(ext)) return { type: 'image', label: '🖼 图片素材', badge: 'badge-image' };
        if (FILE_TYPES.video.includes(ext)) return { type: 'video', label: '🎬 视频素材', badge: 'badge-video' };
        return { type: 'binary', label: '📦 文件', badge: 'badge-binary' };
    }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes/1024).toFixed(1) + ' KB';
        return (bytes/1048576).toFixed(1) + ' MB';
    }

    function formatDate(ts) {
        const d = new Date(ts);
        const pad = n => n.toString().padStart(2,'0');
        return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+' '+pad(d.getHours())+':'+pad(d.getMinutes());
    }

    // ══════════════════════════════════════════
    // 上传（拖入→立刻上传到Gallery）
    // ══════════════════════════════════════════
    uploadedFiles = [];
    const uploadZone = document.getElementById('uploadZone');
    uploadZone.addEventListener('dragover', function(e) {
        e.preventDefault(); this.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', function(e) {
        e.preventDefault(); this.classList.remove('dragover');
    });
    uploadZone.addEventListener('drop', function(e) {
        e.preventDefault(); this.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files);
    });

    function handleFileSelect(files) {
        for (let f of files) {
            uploadToGallery(f);
        }
    }

    async function uploadToGallery(file) {
        const fd = new FormData();
        fd.append('file', file);
        try {
            const r = await fetch('/api/v1/gallery/upload', { method: 'POST', body: fd });
            const d = await r.json();
            if (d.success) {
                const info = d.data;
                uploadedFiles.push({
                    name: info.name,
                    size: info.size,
                    size_str: info.size_str,
                    file_type: info.file_type,
                    role: info.role,
                    checked: true
                });
                renderFileList();
                refreshData();
            } else {
                showToast('❌ ' + file.name + ' 上传失败');
            }
        } catch(e) {
            showToast('❌ ' + file.name + ' 网络错误');
        }
    }

    function toggleFile(index) {
        uploadedFiles[index].checked = !uploadedFiles[index].checked;
        renderFileList();
    }

    function removeFile(index) {
        uploadedFiles.splice(index, 1);
        renderFileList();
    }

    function clearFiles() {
        uploadedFiles = [];
        renderFileList();
    }

    function renderFileList() {
        const itemsDiv = document.getElementById('fileItems');
        const countSpan = document.getElementById('fileCount');
        const btn = document.getElementById('btnGenerate');

        if (uploadedFiles.length === 0) {
            itemsDiv.innerHTML = '';
            btn.disabled = true;
            countSpan.textContent = '已选 0 个文件';
            return;
        }
        const checked = uploadedFiles.filter(f => f.checked).length;
        btn.disabled = checked === 0;
        countSpan.textContent = '已上传 ' + uploadedFiles.length + ' 个，勾选 ' + checked + ' 个';

        let html = '';
        uploadedFiles.forEach((f, i) => {
            const info = classifyFile(f.name);
            html += '<div class="file-item">' +
                '<input type="checkbox" ' + (f.checked ? 'checked' : '') +
                ' onchange="toggleFile('+i+')" style="width:16px;height:16px;accent-color:#f7971e;cursor:pointer;">' +
                '<span class="icon">' + info.label.charAt(0) + '</span>' +
                '<span class="name" title="'+f.name+'">' + escapeHtml(f.name) + '</span>' +
                '<span class="size">' + f.size_str + '</span>' +
                '<span class="badge ' + info.badge + '">' + info.label + '</span>' +
                '<span class="badge badge-success">✅</span>' +
                '<button onclick="removeFile('+i+')" style="background:none;border:none;color:#ef5350;cursor:pointer;font-size:14px;">✕</button>' +
                '</div>';
        });
        itemsDiv.innerHTML = html;
    }

    // ══════════════════════════════════════════
    // 生成视频
    // ══════════════════════════════════════════
    // 📝 文字直出 -> 生成视频
    async function generateFromText() {
        const text = document.getElementById('textInput').value.trim();
        if (!text) return;
        const btn = document.getElementById('btnGenerateText');
        btn.disabled = true;
        btn.textContent = '⏳ 提交中...';
        try {
            const r = await fetch('/api/v1/gallery/generate-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    duration: parseInt(document.getElementById('durationInput').value) || 5,
                    bg: document.getElementById('bgColor').value
                })
            });
            const d = await r.json();
            if (d.success) {
                showToast('✅ ' + d.data.message);
                document.getElementById('textInput').value = '';
                btn.disabled = true;
                refreshTasks();
                refreshData();
            } else {
                showToast('❌ ' + (d.error || '生成失败'));
            }
        } catch(e) {
            showToast('❌ 网络错误');
        }
        btn.disabled = false;
        btn.textContent = '🎬 生成视频';
        checkTextInput();
    }

    // 监听文字输入，启用/禁用按钮
    function checkTextInput() {
        const text = document.getElementById('textInput').value.trim();
        document.getElementById('btnGenerateText').disabled = !text;
    }
    document.addEventListener('DOMContentLoaded', function() {
        const ta = document.getElementById('textInput');
        if (ta) {
            ta.addEventListener('input', checkTextInput);
            checkTextInput();
        }
    });

    async function generateVideo() {
        const checked = uploadedFiles.filter(f => f.checked);
        if (checked.length === 0) return;

        const btn = document.getElementById('btnGenerate');
        btn.disabled = true;
        btn.textContent = '⏳ 提交中...';

        try {
            const r = await fetch('/api/v1/gallery/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filenames: checked.map(f => f.name) })
            });
            const d = await r.json();

            if (d.success) {
                showToast('✅ ' + d.data.message);
                uploadedFiles = [];
                renderFileList();
                refreshTasks();
                refreshData();
            } else {
                showToast('❌ ' + (d.error || '生成失败'));
            }
        } catch(e) {
            showToast('❌ 网络错误');
        }

        btn.disabled = false;
        btn.textContent = '🎬 生成视频';
    }

    // ══════════════════════════════════════════
    // 任务进度
    // ══════════════════════════════════════════
    async function refreshTasks() {
        try {
            const r = await fetch('/api/v1/gallery/tasks');
            const d = await r.json();
            const tasks = d.data || [];

            const section = document.getElementById('taskSection');
            const list = document.getElementById('taskList');

            if (tasks.length === 0) {
                section.classList.add('hidden');
                return;
            }

            section.classList.remove('hidden');
            list.innerHTML = tasks.map(t => {
                const statusClass = t.stage === 'completed' ? 'completed' :
                    (t.stage === 'failed' ? 'failed' : 'running');
                const stageLabel = {
                    'pending': '排队中', 'parsing': '解析文档', 'tts': '语音合成',
                    'rendering': '合成视频', 'completed': '✅ 完成', 'failed': '❌ 失败'
                }[t.stage] || t.stage;

                return '<div class="task-card">' +
                    '<div class="task-header">' +
                        '<span class="task-title">' + escapeHtml(t.title) + '</span>' +
                        '<span class="task-status ' + statusClass + '">' + stageLabel + '</span>' +
                    '</div>' +
                    '<div class="task-progress-bar">' +
                        '<div class="task-progress-fill" style="width:' + t.percent + '%"></div>' +
                    '</div>' +
                    '<div style="display:flex;justify-content:space-between;margin-top:4px;">' +
                        (t.message ? '<span class="task-message" style="margin:0;">' + escapeHtml(t.message) + '</span>' : '<span></span>') +
                        '<span style="font-size:12px;color:#f7971e;font-weight:600;">' + t.percent + '%</span>' +
                    '</div>' +
                    '</div>';
            }).join('');
        } catch(e) {}
    }

    // ══════════════════════════════════════════
    // 作品展示
    // ══════════════════════════════════════════
    async function refreshData() {
        try {
            const r = await fetch('/api/v1/gallery?format=json');
            const d = await r.json();
            items = d.data || [];
            render();
        } catch(e) {}
    }

    function getType(item) {
        if (item.is_video) return 'video';
        if (item.is_audio) return 'audio';
        if (item.is_image) return 'image';
        return 'binary';
    }

    function getBadgeHtml(type) {
        if (type==='video') return '<span class="badge badge-video">🎬 视频</span>';
        if (type==='audio') return '<span class="badge badge-audio">🎵 音频</span>';
        if (type==='image') return '<span class="badge badge-image">🖼 图片</span>';
        return '<span class="badge badge-binary">📦 文件</span>';
    }

    function render() {
        let filtered = items.filter(item => {
            if (currentFilter !== 'all' && getType(item) !== currentFilter) return false;
            if (currentSearch && !item.name.toLowerCase().includes(currentSearch.toLowerCase())) return false;
            return true;
        });

        filtered.sort((a,b) => {
            if (currentSort === 'date-desc') return b.mod_time.localeCompare(a.mod_time);
            if (currentSort === 'date-asc') return a.mod_time.localeCompare(b.mod_time);
            if (currentSort === 'name') return a.name.localeCompare(b.name);
            if (currentSort === 'size-desc') return b.size - a.size;
            if (currentSort === 'size-asc') return a.size - b.size;
            return 0;
        });

        const vc = items.filter(i=>i.is_video).length;
        const ic = items.filter(i=>i.is_image).length;
        const ac = items.filter(i=>i.is_audio).length;
        document.getElementById('totalCount').textContent = items.length;
        document.getElementById('videoCount').textContent = vc;
        document.getElementById('imageCount').textContent = ic;
        document.getElementById('audioCount').textContent = ac;

        const container = document.getElementById('gallery');

        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty"><div class="big-icon">🔍</div><p>没有匹配的作品</p></div>';
            return;
        }

        container.innerHTML = filtered.map(item => {
            const type = getType(item);
            const badgeHtml = getBadgeHtml(type);

            let previewHtml = '';
            if (type === 'video') {
                previewHtml = '<video muted preload="metadata" src="'+item.url+'#t=0.5" ' +
                    'onmouseover="this.play()" onmouseout="this.pause();this.currentTime=0;"></video>';
            } else if (type === 'image') {
                previewHtml = '<img src="'+item.url+'" loading="lazy">';
            } else if (type === 'audio') {
                previewHtml = '<div class="icon">🎵</div>';
            } else {
                previewHtml = '<div class="icon">📦</div>';
            }

            let actionsHtml = '';
            if (type === 'video' || type === 'audio') {
                actionsHtml += '<a href="#" class="btn-play" onclick="playMedia(\''+item.url+'\');return false;">▶ 播放</a>';
            }
            actionsHtml += '<a href="'+item.url+'" download class="btn-download">⬇ 下载</a>';
            actionsHtml += '<button class="btn-delete" onclick="confirmDelete(\''+encodeURIComponent(item.name)+'\')">🗑</button>';

            return '<div class="card">' +
                '<div class="card-preview">'+previewHtml+'</div>' +
                '<div class="card-info">' +
                    '<div class="name" title="'+escapeHtml(item.name)+'">'+escapeHtml(item.name)+'</div>' +
                    '<div class="meta"><span>'+badgeHtml+'</span><span>'+item.size_human+'</span></div>' +
                    '<div class="meta" style="margin-top:1px;font-size:11px;color:#555;">'+formatDate(item.mod_time)+'</div>' +
                    '<div class="actions">'+actionsHtml+'</div>' +
                '</div></div>';
        }).join('');
    }

    function escapeHtml(s) {
        return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function playMedia(url) {
        const modal = document.getElementById('playerModal');
        const video = document.getElementById('playerVideo');
        modal.classList.add('active');
        video.src = url;
        video.play();
    }

    // ══════════════════════════════════════════
    // 筛选 / 排序
    // ══════════════════════════════════════════
    function setFilter(btn, filter) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = filter;
        render();
    }

    function filterGallery() {
        currentSearch = document.getElementById('searchBox').value;
        render();
    }

    function toggleSort() {
        const modes = ['date-desc','date-asc','name','size-desc','size-asc'];
        const labels = ['📅 最新','📅 最旧','📝 名称','📈 最大','📉 最小'];
        const idx = modes.indexOf(currentSort);
        currentSort = modes[(idx+1) % modes.length];
        document.getElementById('sortBtn').textContent = labels[(idx+1) % modes.length];
        render();
    }

    // ══════════════════════════════════════════
    // 删除
    // ══════════════════════════════════════════
    function confirmDelete(name) {
        deleteTarget = decodeURIComponent(name);
        document.getElementById("deleteFileName").textContent = decodeURIComponent(name);
        document.getElementById('confirmDialog').classList.add('active');
        document.getElementById('confirmDeleteBtn').onclick = doDelete;
    }

    function closeConfirm() {
        document.getElementById('confirmDialog').classList.remove('active');
        deleteTarget = null;
    }

    async function doDelete() {
        if (!deleteTarget) return;
        try {
            const r = await fetch('/api/v1/gallery/delete?name='+encodeURIComponent(deleteTarget), {method:'POST'});
            const d = await r.json();
            if (d.success) {
                showToast('✅ 已删除: '+deleteTarget);
                closeConfirm();
                await refreshData();
            } else {
                showToast('❌ '+(d.error||'删除失败'));
            }
        } catch(e) {
            showToast('❌ 网络错误');
        }
    }

    // ══════════════════════════════════════════
    // Toast
    // ══════════════════════════════════════════
    function showToast(msg) {
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 3000);
    }

    // ══════════════════════════════════════════
    // AI 助手 (搜索框模式)
    // ══════════════════════════════════════════
    let aiSessionId = 'ai-' + Date.now();

    let aiResult = "";

    async function askAI() {
        const input = document.getElementById('ai-search');
        const msg = input.value.trim();
        if (!msg) return;

        const replyBox = document.getElementById('ai-reply');
        replyBox.innerHTML = '<span style="color:#888;">⏳ 连接中...</span>';
        replyBox.style.display = 'block';
        input.disabled = true;
        aiResult = "";

        try {
            const resp = await fetch('/api/v1/agent/stream', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task: msg, session_id: aiSessionId})
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let inEvent = false;
            let evType = "";

            replyBox.innerHTML = '<span style="color:#888;">⏳ 接收中...</span>';

            while (true) {
                const {done, value} = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("event: ")) {
                        evType = line.slice(7).trim();
                        inEvent = true;
                    } else if (line.startsWith("data: ") && inEvent) {
                        const data = line.slice(6).trim();
                        inEvent = false;

                        if (evType === "result" || evType === "thought") {
                            aiResult += data;
                            replyBox.innerHTML = aiResult.replace(/\n/g, '<br>');
                        } else if (evType === "status") {
                            replyBox.innerHTML = '<span style="color:#888;">' + data + '</span>';
                        } else if (evType === "done") {
                            replyBox.innerHTML = aiResult.replace(/\n/g, '<br>');
                        }
                    }
                }
            }
        } catch(e) {
            replyBox.innerHTML = '<span style="color:#f66;">⚠️ 网络错误: ' + e.message + '</span>';
        }
        input.disabled = false;
        input.focus();
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && document.activeElement === document.getElementById('ai-search')) {
            askAI();
        }
    });

    function escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    // ══════════════════════════════════════════
    // 初始化
    // ══════════════════════════════════════════
    refreshData();
    refreshTasks();
    setInterval(refreshData, 15000);
    setInterval(refreshTasks, 3000);
    </script>
</body>
</html>`
