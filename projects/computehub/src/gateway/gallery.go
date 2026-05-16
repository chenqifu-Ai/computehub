package gateway

import (
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
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

// GalleryHandler 作品广场 HTTP 处理器
type GalleryHandler struct {
	mu       sync.RWMutex
	rootDir  string
	items    []GalleryItem
	lastScan time.Time
}

// NewGalleryHandler 创建作品广场处理器
func NewGalleryHandler(config *GalleryConfig) *GalleryHandler {
	rootDir := "/var/computehub/gallery"
	if config != nil && config.RootDir != "" {
		rootDir = config.RootDir
	}
	// 确保目录存在
	os.MkdirAll(rootDir, 0755)

	h := &GalleryHandler{
		rootDir: rootDir,
	}
	h.scan()
	return h
}

// scan 扫描作品目录
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

	// 按修改时间倒序（最新的在前）
	sort.Slice(h.items, func(i, j int) bool {
		return h.items[i].ModTime > h.items[j].ModTime
	})

	h.lastScan = time.Now()
}

// refresh 强制刷新扫描
func (h *GalleryHandler) refresh() {
	h.scan()
}

// getItems 获取作品列表
func (h *GalleryHandler) getItems() []GalleryItem {
	h.mu.RLock()
	defer h.mu.RUnlock()

	// 自动刷新：如果距离上次扫描超过 10 秒
	if time.Since(h.lastScan) > 10*time.Second {
		h.mu.RUnlock()
		h.refresh()
		h.mu.RLock()
	}

	items := make([]GalleryItem, len(h.items))
	copy(items, h.items)
	return items
}

// HandleGallery 处理作品广场页面请求
func (h *GalleryHandler) HandleGallery(w http.ResponseWriter, r *http.Request) {
	// 支持 JSON 和 HTML 两种格式
	accept := r.Header.Get("Accept")
	if strings.Contains(accept, "application/json") || r.URL.Query().Get("format") == "json" {
		h.handleGalleryJSON(w, r)
		return
	}
	h.handleGalleryHTML(w, r)
}

// handleGalleryJSON 返回 JSON 格式的作品列表
func (h *GalleryHandler) handleGalleryJSON(w http.ResponseWriter, r *http.Request) {
	items := h.getItems()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    items,
		"total":   len(items),
	})
}

// handleGalleryHTML 返回 HTML 格式的作品广场页面
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

// HandleFile 处理文件下载/预览请求
func (h *GalleryHandler) HandleFile(w http.ResponseWriter, r *http.Request) {
	filename := strings.TrimPrefix(r.URL.Path, "/api/v1/files/")
	if filename == "" || strings.Contains(filename, "..") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	filePath := filepath.Join(h.rootDir, filepath.Clean(filename))

	// 安全检查：确保文件在 rootDir 下
	absRoot, _ := filepath.Abs(h.rootDir)
	absFile, _ := filepath.Abs(filePath)
	if !strings.HasPrefix(absFile, absRoot) {
		http.Error(w, "Access denied", http.StatusForbidden)
		return
	}

	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		http.Error(w, "File not found", http.StatusNotFound)
		return
	}

	// 检测 MIME 类型并设置正确的 Content-Type
	ext := strings.ToLower(filepath.Ext(filename))
	mimeType := detectMime(ext)

	w.Header().Set("Content-Type", mimeType)
	w.Header().Set("Content-Disposition", fmt.Sprintf(`inline; filename="%s"`, filename))
	w.Header().Set("Accept-Ranges", "bytes")

	// 支持 Range 请求（视频拖动进度条）
	http.ServeFile(w, r, filePath)
}

// detectMime 根据扩展名检测 MIME 类型
func detectMime(ext string) string {
	mimeMap := map[string]string{
		// 视频
		".mp4":  "video/mp4",
		".webm": "video/webm",
		".avi":  "video/x-msvideo",
		".mov":  "video/quicktime",
		".mkv":  "video/x-matroska",
		".flv":  "video/x-flv",
		".wmv":  "video/x-ms-wmv",
		".m4v":  "video/x-m4v",
		".3gp":  "video/3gpp",
		// 音频
		".mp3":  "audio/mpeg",
		".wav":  "audio/wav",
		".ogg":  "audio/ogg",
		".aac":  "audio/aac",
		".flac": "audio/flac",
		".m4a":  "audio/mp4",
		".wma":  "audio/x-ms-wma",
		// 图片
		".jpg":  "image/jpeg",
		".jpeg": "image/jpeg",
		".png":  "image/png",
		".gif":  "image/gif",
		".webp": "image/webp",
		".bmp":  "image/bmp",
		".svg":  "image/svg+xml",
		// 文档
		".txt":  "text/plain",
		".json": "application/json",
		".html": "text/html",
		".htm":  "text/html",
		".pdf":  "application/pdf",
		".zip":  "application/zip",
		".tar":  "application/x-tar",
		".gz":   "application/gzip",
	}
	if mime, ok := mimeMap[ext]; ok {
		return mime
	}
	return "application/octet-stream"
}

// formatSize 格式化文件大小
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

// ==================== HTML 模板 ====================

const galleryHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎬 小智影业 - 作品广场</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            padding: 24px 32px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .header-top {
            display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
        }
        .header h1 {
            font-size: 26px;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .subtitle {
            color: #666; font-size: 13px; margin-top: 2px;
        }
        .header .stats {
            display: flex; gap: 24px; margin-top: 8px; font-size: 13px;
        }
        .header .stats span { color: #888; }
        .header .stats strong { color: #f7971e; }
        .header .stats em { color: #4caf50; font-style: normal; }

        /* 工具栏 */
        .toolbar {
            padding: 16px 32px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
        }
        .toolbar .search-box {
            flex: 1; min-width: 200px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px; padding: 10px 14px;
            color: #e0e0e0; font-size: 14px; outline: none;
            transition: border-color 0.2s;
        }
        .toolbar .search-box:focus {
            border-color: #f7971e;
        }
        .toolbar .search-box::placeholder { color: #555; }
        .filter-btns {
            display: flex; gap: 6px; flex-wrap: wrap;
        }
        .filter-btn {
            padding: 8px 14px; border-radius: 8px; font-size: 13px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: #888; cursor: pointer; transition: all 0.2s;
        }
        .filter-btn:hover { background: rgba(255,255,255,0.1); color: #ccc; }
        .filter-btn.active {
            background: rgba(247,151,30,0.15);
            border-color: #f7971e; color: #f7971e;
        }
        .sort-btn {
            padding: 8px 12px; border-radius: 8px; font-size: 13px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            color: #888; cursor: pointer; transition: all 0.2s;
        }
        .sort-btn:hover { background: rgba(255,255,255,0.1); color: #ccc; }

        /* 上传区域 */
        .upload-zone-wrap {
            padding: 0 32px; margin-top: 16px;
        }
        .upload-zone {
            padding: 24px;
            border: 2px dashed rgba(255,255,255,0.12);
            border-radius: 12px; text-align: center; cursor: pointer;
            transition: all 0.3s ease;
            background: rgba(255,255,255,0.02);
        }
        .upload-zone:hover, .upload-zone.dragover {
            border-color: #f7971e;
            background: rgba(247,151,30,0.06);
        }
        .upload-zone .icon { font-size: 28px; }
        .upload-zone p { color: #888; font-size: 13px; margin-top: 4px; }
        .upload-zone input[type=file] { display: none; }
        .upload-progress {
            padding: 0 32px; display: none;
        }
        .upload-progress .bar {
            height: 3px; background: rgba(255,255,255,0.08);
            border-radius: 2px; overflow: hidden;
        }
        .upload-progress .bar-fill {
            height: 100%; background: linear-gradient(90deg, #f7971e, #ffd200);
            width: 0%; transition: width 0.3s;
        }
        .upload-progress .status {
            font-size: 12px; color: #888; margin-top: 4px;
        }

        /* 作品网格 */
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px; padding: 20px 32px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 10px; overflow: hidden;
            border: 1px solid rgba(255,255,255,0.06);
            transition: all 0.25s ease; position: relative;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(247,151,30,0.25);
            box-shadow: 0 6px 24px rgba(247,151,30,0.08);
        }
        .card-preview {
            position: relative;
            background: #1a1a2e;
            aspect-ratio: 16/9;
            display: flex; align-items: center; justify-content: center;
            overflow: hidden;
        }
        .card-preview video, .card-preview img {
            width: 100%; height: 100%; object-fit: cover;
        }
        .card-preview .icon {
            font-size: 40px; opacity: 0.4;
        }
        .card-preview .duration-badge {
            position: absolute; bottom: 8px; right: 8px;
            background: rgba(0,0,0,0.7); padding: 2px 8px;
            border-radius: 4px; font-size: 11px; color: #fff;
        }
        .card-info {
            padding: 12px 14px;
        }
        .card-info .name {
            font-size: 14px; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .card-info .meta {
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 6px; font-size: 12px; color: #888;
        }
        .badge {
            display: inline-block; padding: 2px 7px; border-radius: 4px;
            font-size: 11px; font-weight: 600;
        }
        .badge-video { background: rgba(247,151,30,0.18); color: #f7971e; }
        .badge-audio { background: rgba(76,175,80,0.18); color: #4caf50; }
        .badge-image { background: rgba(33,150,243,0.18); color: #2196f3; }
        .badge-binary { background: rgba(156,39,176,0.18); color: #ce93d8; }
        .card-info .actions {
            display: flex; gap: 6px; margin-top: 10px;
        }
        .card-info .actions a, .card-info .actions button {
            flex: 1; text-align: center; padding: 7px 10px; border-radius: 6px;
            font-size: 12px; text-decoration: none; border: none; cursor: pointer;
            transition: all 0.2s;
        }
        .btn-play {
            background: linear-gradient(90deg, #f7971e, #ffd200);
            color: #1a1a2e !important; font-weight: 600;
        }
        .btn-play:hover { opacity: 0.9; }
        .btn-download {
            background: rgba(255,255,255,0.08); color: #bbb !important;
        }
        .btn-download:hover { background: rgba(255,255,255,0.15); }
        .btn-delete {
            background: rgba(244,67,54,0.12); color: #ef5350 !important;
            flex: 0 0 auto !important; padding: 7px 10px !important;
        }
        .btn-delete:hover { background: rgba(244,67,54,0.25); }

        .empty {
            grid-column: 1 / -1; text-align: center;
            padding: 60px 32px; color: #666;
        }
        .empty .big-icon { font-size: 56px; margin-bottom: 16px; }

        .footer { text-align: center; padding: 16px; color: #444; font-size: 12px; }

        /* 模态框 */
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
            font-size: 28px; color: #fff; cursor: pointer;
            opacity: 0.6; transition: opacity 0.2s;
        }
        .modal .close:hover { opacity: 1; }

        /* 删除确认弹窗 */
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
        .confirm-box p { font-size: 13px; color: #888; margin-bottom: 16px; }
        .confirm-box .name-display {
            font-size: 14px; color: #ef5350; margin-bottom: 16px;
            word-break: break-all;
        }
        .confirm-box .btns { display: flex; gap: 8px; }
        .confirm-box .btns button {
            flex: 1; padding: 10px; border-radius: 8px; border: none;
            font-size: 13px; cursor: pointer; transition: all 0.2s;
        }
        .btn-confirm-delete {
            background: #ef5350; color: #fff;
        }
        .btn-confirm-delete:hover { background: #e53935; }
        .btn-cancel-delete {
            background: rgba(255,255,255,0.08); color: #ccc;
        }
        .btn-cancel-delete:hover { background: rgba(255,255,255,0.15); }

        /* Toast通知 */
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
            .toolbar { padding: 12px 20px; }
            .upload-zone-wrap { padding: 0 20px; }
            .gallery { padding: 12px 20px; grid-template-columns: 1fr; }
            .modal { padding: 8px; }
            .toolbar .search-box { min-width: 140px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top">
            <h1>🎬 小智影业 · 作品广场</h1>
        </div>
        <p class="subtitle">ComputeHub 集群自动生产的视频 / 音频 / 图片 / 二进制作品</p>
        <div class="stats">
            <span>📦 共 <strong id="totalCount">{{.Total}}</strong> 件</span>
            <span>🎬 <em id="videoCount">0</em> 视频</span>
            <span>🖼 <em id="imageCount">0</em> 图片</span>
            <span>🎵 <em id="audioCount">0</em> 音频</span>
            <span>🕐 <span id="refreshTime">{{.ServerTime}}</span></span>
        </div>
    </div>

    <div class="toolbar">
        <input class="search-box" id="searchBox" type="text" placeholder="🔍 搜索文件名..." oninput="filterGallery()">
        <div class="filter-btns">
            <button class="filter-btn active" data-filter="all" onclick="setFilter(this,'all')">全部</button>
            <button class="filter-btn" data-filter="video" onclick="setFilter(this,'video')">🎬 视频</button>
            <button class="filter-btn" data-filter="image" onclick="setFilter(this,'image')">🖼 图片</button>
            <button class="filter-btn" data-filter="audio" onclick="setFilter(this,'audio')">🎵 音频</button>
            <button class="filter-btn" data-filter="binary" onclick="setFilter(this,'binary')">📦 二进制</button>
        </div>
        <button class="sort-btn" id="sortBtn" onclick="toggleSort()">📅 最新</button>
    </div>

    <div class="upload-zone-wrap">
        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
            <div class="icon">📤</div>
            <p>点击或拖拽文件到这里上传（最大 500MB）</p>
            <input type="file" id="fileInput" accept="image/*,video/*,audio/*" multiple onchange="uploadFiles(this.files)">
        </div>
    </div>

    <div class="upload-progress" id="uploadProgress">
        <div class="bar"><div class="bar-fill" id="progressFill"></div></div>
        <div class="status" id="uploadStatus">准备中...</div>
    </div>

    <div class="gallery" id="gallery"></div>

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

    <div class="footer">ComputeHub Gallery · 作品自动展示</div>

    <script>
        // ── 数据 ──
        let items = [];
        let currentFilter = 'all';
        let currentSort = 'date-desc';
        let currentSearch = '';
        let deleteTarget = null;

        // ── 获取数据 ──
        async function refreshData() {
            try {
                const r = await fetch('/api/v1/gallery?format=json');
                const d = await r.json();
                items = d.data || [];
                render();
            } catch(e) { console.log('refresh error'); }
        }

        // ── 分类辅助 ──
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
            return '<span class="badge badge-binary">📦 二进制</span>';
        }
        function formatDate(ts) {
            const d = new Date(ts);
            const pad = n => n.toString().padStart(2,'0');
            return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+' '+pad(d.getHours())+':'+pad(d.getMinutes());
        }

        // ── 渲染 ──
        function render() {
            let filtered = items.filter(item => {
                if (currentFilter !== 'all' && getType(item) !== currentFilter) return false;
                if (currentSearch && !item.name.toLowerCase().includes(currentSearch.toLowerCase())) return false;
                return true;
            });

            // 排序
            filtered.sort((a,b) => {
                if (currentSort === 'date-desc') return b.mod_time.localeCompare(a.mod_time);
                if (currentSort === 'date-asc') return a.mod_time.localeCompare(b.mod_time);
                if (currentSort === 'name') return a.name.localeCompare(b.name);
                if (currentSort === 'size-desc') return b.size - a.size;
                if (currentSort === 'size-asc') return a.size - b.size;
                return 0;
            });

            // 统计
            const vc = items.filter(i=>i.is_video).length;
            const ic = items.filter(i=>i.is_image).length;
            const ac = items.filter(i=>i.is_audio).length;
            document.getElementById('totalCount').textContent = items.length;
            document.getElementById('videoCount').textContent = vc;
            document.getElementById('imageCount').textContent = ic;
            document.getElementById('audioCount').textContent = ac;
            document.getElementById('refreshTime').textContent = new Date().toLocaleString('zh-CN');

            const container = document.getElementById('gallery');

            if (filtered.length === 0) {
                container.innerHTML = '<div class="empty"><div class="big-icon">🔍</div><p>没有匹配的作品</p></div>';
                return;
            }

            container.innerHTML = filtered.map(item => {
                const type = getType(item);
                const badgeHtml = getBadgeHtml(type);
                const previewHtml = getPreviewHtml(item, type);
                const actionsHtml = getActionsHtml(item, type);

                return '<div class="card" data-type="'+type+'">' +
                    '<div class="card-preview">'+previewHtml+'</div>' +
                    '<div class="card-info">' +
                        '<div class="name" title="'+escapeHtml(item.name)+'">'+escapeHtml(item.name)+'</div>' +
                        '<div class="meta"><span>'+badgeHtml+'</span><span>'+item.size_human+'</span></div>' +
                        '<div class="meta" style="margin-top:2px;font-size:11px;color:#555;">'+formatDate(item.mod_time)+'</div>' +
                        '<div class="actions">'+actionsHtml+'</div>' +
                    '</div></div>';
            }).join('');
        }

        function escapeHtml(s) {
            return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function getPreviewHtml(item, type) {
            if (type === 'video') {
                return '<video muted preload="metadata" src="'+item.url+'#t=0.5" ' +
                       'onmouseover="this.play()" onmouseout="this.pause();this.currentTime=0;"></video>';
            }
            if (type === 'image') {
                return '<img src="'+item.url+'" loading="lazy">';
            }
            if (type === 'audio') {
                return '<div class="icon">🎵</div>';
            }
            return '<div class="icon">📦</div>';
        }

        function getActionsHtml(item, type) {
            let html = '';
            if (type === 'video' || type === 'audio') {
                html += '<a href="#" class="btn-play" onclick="playMedia(\''+item.url+'\',\''+item.mime_type+'\');return false;">▶ 播放</a>';
            }
            html += '<a href="'+item.url+'" download class="btn-download">⬇ 下载</a>';
            html += '<button class="btn-delete" onclick="confirmDelete(\''+escapeHtml(item.name)+'\')">🗑</button>';
            return html;
        }

        // ── 播放 ──
        function playMedia(url, mimeType) {
            const modal = document.getElementById('playerModal');
            const video = document.getElementById('playerVideo');
            modal.classList.add('active');
            video.src = url;
            video.play();
        }

        // ── 筛选 ──
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

        // ── 排序 ──
        function toggleSort() {
            const modes = ['date-desc','date-asc','name','size-desc','size-asc'];
            const labels = ['📅 最新','📅 最旧','📝 名称','📈 最大','📉 最小'];
            const idx = modes.indexOf(currentSort);
            currentSort = modes[(idx+1) % modes.length];
            document.getElementById('sortBtn').textContent = labels[(idx+1) % modes.length];
            render();
        }

        // ── 删除 ──
        function confirmDelete(name) {
            deleteTarget = name;
            document.getElementById('deleteFileName').textContent = name;
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
                    showToast('❌ 删除失败: '+(d.error||'unknown'));
                }
            } catch(e) {
                showToast('❌ 网络错误');
            }
        }

        // ── Toast ──
        function showToast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3000);
        }

        // ── 上传 ──
        const uploadZone = document.getElementById('uploadZone');
        const progressBar = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const uploadStatus = document.getElementById('uploadStatus');

        uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault(); this.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', function(e) {
            e.preventDefault(); this.classList.remove('dragover');
        });
        uploadZone.addEventListener('drop', function(e) {
            e.preventDefault(); this.classList.remove('dragover');
            if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
        });

        function uploadFiles(files) {
            for (let i = 0; i < files.length; i++) uploadFile(files[i]);
        }
        function uploadFile(file) {
            const fd = new FormData();
            fd.append('file', file);
            progressBar.style.display = 'block';

            const xhr = new XMLHttpRequest();
            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    progressFill.style.width = Math.round((e.loaded/e.total)*100)+'%';
                    uploadStatus.textContent = '上传中 '+file.name;
                }
            };
            xhr.onload = function() {
                if (xhr.status === 200) {
                    uploadStatus.textContent = '✅ '+file.name+' 完成';
                    setTimeout(()=>{progressBar.style.display='none';progressFill.style.width='0%';},2000);
                    refreshData();
                } else {
                    uploadStatus.textContent = '❌ '+file.name+' 失败';
                }
            };
            xhr.onerror = () => uploadStatus.textContent = '❌ '+file.name+' 网络错误';
            xhr.open('POST', '/api/v1/gallery/upload', true);
            xhr.send(fd);
        }

        // ── 初始化 ──
        refreshData();
        setInterval(refreshData, 15000);
    </script>
</body>
</html>`

// HandleUpload 处理文件上传（来自 Worker 自动回传或手动上传）
func (h *GalleryHandler) HandleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// 限制上传大小：500MB
	r.Body = http.MaxBytesReader(w, r.Body, 500<<20)

	if err := r.ParseMultipartForm(32 << 20); err != nil {
		http.Error(w, fmt.Sprintf("Parse error: %v", err), http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, fmt.Sprintf("File error: %v", err), http.StatusBadRequest)
		return
	}
	defer file.Close()

	filename := header.Filename
	// 清理文件名
	filename = filepath.Base(filename)
	if filename == "." || filename == "/" {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	// 安全检查
	if strings.Contains(filename, "..") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	destPath := filepath.Join(h.rootDir, filename)

	// 如果同名文件已存在，加时间戳后缀
	if _, err := os.Stat(destPath); err == nil {
		ext := filepath.Ext(filename)
		base := strings.TrimSuffix(filename, ext)
		filename = fmt.Sprintf("%s_%d%s", base, time.Now().Unix(), ext)
		destPath = filepath.Join(h.rootDir, filename)
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

	// 触发刷新
	h.refresh()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"name":     filename,
			"size":     written,
			"size_str": formatSize(written),
			"url":      fmt.Sprintf("/api/v1/files/%s", filename),
		},
	})
}


// HandleDelete 处理文件删除
// 支持 URL query (?name=xxx) 和 JSON body 两种方式
func (h *GalleryHandler) HandleDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	// 优先从 JSON body 读取
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
	// fallback 到 query string
	if filename == "" {
		filename = r.URL.Query().Get("name")
	}

	if filename == "" || strings.Contains(filename, "..") {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "Invalid filename",
		})
		return
	}

	filePath := filepath.Join(h.rootDir, filepath.Clean(filename))
	absRoot, _ := filepath.Abs(h.rootDir)
	absFile, _ := filepath.Abs(filePath)
	if !strings.HasPrefix(absFile, absRoot) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "Access denied",
		})
		return
	}

	if err := os.Remove(filePath); err != nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		})
		return
	}

	h.refresh()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    map[string]string{"name": filename},
	})
}

// RegisterGallery 在默认 ServeMux 上注册作品广场路由
func RegisterGallery(config *GalleryConfig) {
	h := NewGalleryHandler(config)

	http.HandleFunc("/api/v1/gallery", h.HandleGallery)
	http.HandleFunc("/api/v1/gallery/upload", h.HandleUpload)
	http.HandleFunc("/api/v1/gallery/delete", h.HandleDelete)
	http.HandleFunc("/gallery", h.HandleGallery)
	http.HandleFunc("/api/v1/files/", h.HandleFile)
	// Note: "/" route registered in gateway.go to avoid conflict

	logWithTimestamp("🎬 Gallery registered:")
	formatTime := time.Now().Format("2006-01-02 15:04:05")
	logWithTimestamp("   - /api/v1/gallery            → 作品广场页面 (HTML/JSON) [%s]", formatTime)
	logWithTimestamp("   - /api/v1/gallery?format=json → JSON 接口")
	logWithTimestamp("   - /api/v1/gallery/upload      → 文件上传 (multipart/form-data)")
	logWithTimestamp("   - /api/v1/gallery/delete      → 文件删除")
	logWithTimestamp("   - /gallery                    → 简洁页面入口")
	logWithTimestamp("   - /                         → 默认页面入口")
	logWithTimestamp("   - /api/v1/files/*             → 作品文件下载/预览")
	logWithTimestamp("📂 Gallery root: %s", h.rootDir)
}
