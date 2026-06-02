# 📸 Gallery 作品广场项目全景回顾

> **项目周期**: 2026-05-15 ~ 2026-05-20  
> **涉及版本**: v0.7.7 → v0.7.12  
> **代码量**: 后端 ~1900行 Go + 前端 ~500行嵌入HTML + 前端补丁 248行  
> **总代码变更**: 约2300行（不含测试文件）

---

## 一、需求缘起

### 1.1 背景痛点

ComputeHub 作为算力调度平台，Worker 节点能跑任务、产视频，但产出的内容无处展示。老大需要一个**集中式的作品展示系统**：

- 上传文档/图片/音频 → 自动识别类型 → 生成视频 → 进度可见 → 作品广场展示
- 支持相机拍照直接上传（移动端友好）
- 支持文本生成视频（无需外部文档）
- 任务进度实时追踪
- 支持删除、下载

### 1.2 需求总结

```
上传文件（文档/图片/音频/视频/文本）
    ↓
自动识别文件类型（document/audio/image/video/binary）
    ↓
分配角色（内容源/配音/素材）
    ↓
触发视频生成管线
    ↓
进度实时追踪（uploading → parsing → tts → rendering → completed/failed）
    ↓
作品展示（广场页面，按时间倒序）
    ↓
支持：查看/下载/删除
```

---

## 二、架构设计

### 2.1 核心组件

```
GalleryHandler
├── scan()           → 扫描 gallery/ 目录，构建作品列表
├── getItems()       → 返回作品列表（10s 自动刷新）
├── classifyFile()   → 文件类型识别（基于扩展名）
├── updateTask()     → 更新任务进度
├── getTasks()       → 查询任务进度（5分钟自动清理）
│
├── HandleGallery()      → HTML 前端页面 + 列表
├── HandleUpload()       → 文件上传 → 类型识别 → 存盘
├── HandleDelete()       → 删除文件
├── HandleFile()         → 文件下载/预览
├── HandleGenerateFromGallery() → 从已上传文件生成视频
├── HandleGenerateFromText()    → 从文本直接生成视频
├── HandleTaskStatus()       → 查询任务进度
└── register()           → 注册所有 HTTP 路由
```

### 2.2 数据模型

```go
// 作品项
type GalleryItem struct {
    Name, Path, SizeHuman, ModTime string
    IsVideo, IsAudio, IsImage      bool
    MimeType, URL                  string
}

// 任务进度
type TaskProgress struct {
    TaskID, Title, Stage string
    Percent int
    Message, OutputURL, Updated string
}
// Stage: uploading / parsing / tts / rendering / completed / failed
```

### 2.3 文件类型识别体系

| 扩展名 | 类型 | 角色 |
|--------|------|------|
| .pdf, .pptx, .ppt, .docx, .doc, .txt | document | 文档内容 |
| .mp3, .wav, .aac, .m4a, .flac, .ogg, .wma | audio | 语音配音 |
| .jpg, .jpeg, .png, .gif, .webp, .bmp, .svg | image | 图片素材 |
| .mp4, .webm, .avi, .mov, .mkv, .flv, .wmv, .m4v | video | 视频素材 |

---

## 三、功能演进（5个迭代）

### 迭代1: v0.7.7 — Gallery 作品广场 + Worker自动回传（5/15）

**核心功能：**
- ✅ `gallery.go` 首次写入，~1000行，核心骨架
- ✅ 文件上传、列表展示、类型识别
- ✅ Worker 自动回传作品到 Gallery 目录
- ✅ 后端 API 全部实现
- ❌ 前端 HTML 内嵌在 Go 中，功能有限

**HTTP 端点：**
```
GET  /api/v1/gallery          → 作品列表（JSON）
GET  /api/v1/gallery/         → 前端页面（HTML）
POST /api/v1/gallery/upload   → 上传文件
GET  /api/v1/files/:name      → 文件下载
```

### 迭代2: v0.7.7→v0.7.8 — Gallery v2 全功能改版（5/16 凌晨）

**核心变更：**
- ✅ `gallery.go` 从 ~1000行 → **~1900行**（+974行）
- ✅ 前端 HTML 重写，完整的 SPA 体验
- ✅ 文件上传拖拽支持
- ✅ `gallery/root_dir` 配置可自定义（config.json）
- ✅ 相机拍照直接上传按钮（移动端）
- ✅ 文本生成视频（`HandleGenerateFromText`）
- ✅ 任务进度实时更新（轮询 API）

**新增 API：**
```
POST /api/v1/gallery/generate       → 从已上传文件生成视频
POST /api/v1/gallery/generate-text  → 从文本生成视频
GET  /api/v1/gallery/tasks          → 查询所有任务进度
POST /api/v1/gallery/delete         → 删除文件
```

### 迭代3: v0.7.9 — Gallery 配置标准化（5/16 下午）

**核心变更：**
- ✅ STD-CONFIG-001 规范落地
- ✅ Gallery 配置纳入 `config.json`
- ✅ 构建脚本规范化
- ✅ 文档补充

### 迭代4: v0.7.10 — Gallery 集成到 Pipeline Repo（5/19）

**核心变更：**
- ✅ `recordToPipelineRepo()` 任务记录到 Git 仓库
- ✅ 每次视频生成自动生成 commit（作者 + 时间戳 + 描述）
- ✅ 完整追溯：哪个任务 → 用了什么文件 → 产出什么
- ✅ 支持分支创建

**Git 追溯逻辑：**
```go
func recordToPipelineRepo(taskID, title, docPath, outputName string) {
    // 1. cd ~/pipeline-repo
    // 2. 创建任务目录
    // 3. 添加文档、配置、输出视频
    // 4. git add + git commit
    //    author: 小智 <19525456@qq.com>
    //    message: task: {taskID} - {title}
    // 5. 自动创建分支（按任务ID）
}
```

### 迭代5: v0.7.12 — Gallery 删除修复 + 全平台二进制更新（5/20）

**核心变更：**
- ✅ 删除功能修复（修复了文件锁/路径问题）
- ✅ `patch_gallery_js.py` — 前端补丁脚本 248行
- ✅ 全平台二进制重新编译
- ✅ 部署脚本更新

---

## 四、完整功能链路

### 4.1 上传 → 识别 → 生成 → 展示（全链路）

```
用户操作                          Gateway 内部流程
─────────                         ────────────────
上传文件                        HandleUpload()
  ├─ multipart/form-data         ├─ 解析 multipart
  ├─ 限制大小                      ├─ 校验文件大小
  ├─ 校验扩展名                    ├─ 校验扩展名
  └─ 保存到 gallery/              └─ 返回上传结果
                                      ↓
                                  classifyFile()
                                  ├─ .pptx → document → 内容源
                                  ├─ .mp3 → audio → 语音配音
                                  └─ .png → image → 图片素材
                                      ↓
                                  HandleGenerateFromGallery()
                                  ├─ 分配 taskID (uuid)
                                  ├─ 创建任务记录
                                  ├─ 启动后台 goroutine
                                  │   └─ runVideoPipeline()
                                  └─ 立即返回 taskID
                                      ↓
                              runVideoPipeline() (后台)
                              ├─ stage: uploading (100%)
                              ├─ stage: parsing
                              │   └─ doc_parser.go 解析文档
                              ├─ stage: tts
                              │   └─ tts_engine.go 生成语音
                              ├─ stage: rendering
                              │   └─ ffmpeg 合成视频
                              └─ stage: completed
                                  ├─ 输出视频存到 gallery/
                                  └─ recordToPipelineRepo()

前端轮询                      HandleTaskStatus()
  ├─ GET /api/v1/gallery/tasks   ├─ 查询任务进度
  ├─ 每 2s 刷新一次              ├─ 返回 JSON
  └─ 显示进度条                  └─ completed 时显示下载按钮
```

### 4.2 文本 → 生成 → 展示（短链路）

```
用户输入文字                    Gateway 内部流程
─────────                       ────────────────
POST /api/v1/gallery/           HandleGenerateFromText()
  generate-text                 ├─ 创建临时文件
{                               ├─ 分配 taskID
  "text": "你好...",            ├─ 后台 goroutine
  "duration": 60,              │   └─ runTextPipeline()
  "bg": "default"              │       ├─ 写入临时 .txt
}                              │       ├─ edge-tts 语音合成
                               │       ├─ ffmpeg 合成视频
                               │       └─ 输出到 gallery/
                               └─ 立即返回 taskID
```

---

## 五、核心技术实现

### 5.1 并发安全设计

```go
// 作品列表：读写锁保护
type GalleryHandler struct {
    mu      sync.RWMutex  // 保护 items 列表
    tasksMu sync.RWMutex  // 保护 tasks 字典
}

// 10秒自动刷新：避免每次都扫磁盘
func (h *GalleryHandler) getItems() []GalleryItem {
    h.mu.RLock()
    if time.Since(h.lastScan) > 10*time.Second {
        h.mu.RUnlock()
        h.refresh()  // 重扫
        h.mu.RLock()
    }
    // ... 返回副本
}
```

### 5.2 任务进度管理

```go
// 任务清理：5分钟后自动清理 completed/failed 的任务
func (h *GalleryHandler) getTasks() []*TaskProgress {
    // 过滤掉已完成超5分钟的任务
    for _, t := range h.tasks {
        if t.Stage == "completed" || t.Stage == "failed" {
            if time.Since(updated) > 5*time.Minute {
                continue  // 跳过
            }
        }
    }
}
```

### 5.3 视频生成管线

```go
// runVideoPipeline() 核心流程：
1. doc_parser.Parse()     → 提取文档内容、图片、章节
2. tts_engine.Synthesize() → 每段文字 → edge-tts → .mp3
3. ffmpeg 合成：
   - 图片幻灯片（drawtext + pan）
   - 语音轨道叠加
   - BGM 可选
   - 输出 .mp4
```

### 5.4 Git 自动追溯

```
每次生成任务 → ~/pipeline-repo/{taskID}/
├── document/        # 原始文档
├── config.json      # 任务配置
├── pipeline.log     # 管线日志
├── output.mp4       # 产出视频
└── README.md        # 任务说明

git commit -m "task: {taskID} - {title}"
    author: 小智 <19525456@qq.com>
    自动创建分支: {taskID}
```

---

## 六、前端设计（内嵌HTML SPA）

前端直接嵌入 Go binary（不依赖外部静态文件），包括：

- **作品网格展示**：卡片式布局，按类型显示图标
- **拖拽上传区域**：支持文件拖入上传
- **进度条**：实时显示各阶段进度
- **类型过滤**：文档/图片/音频/视频 标签切换
- **相机上传**：移动端直接调用摄像头
- **删除确认**：二次确认弹窗
- **响应式设计**：PC + 移动端自适应

---

## 七、统计总览

| 指标 | 数值 |
|------|------|
| 总代码行数 | ~1900 Go + ~500 HTML/JS + ~250 Python补丁 |
| HTTP API 端点数 | 8个 |
| 支持的文件类型 | 6种 |
| 任务阶段数 | 6个（uploading/parsing/tts/rendering/completed/failed） |
| 迭代次数 | 5个版本迭代 |
| 涉及提交 | 4个主提交（dfa2c85, 702a402, ec1d042, cdcd0d8） |

---

## 八、当前状态与待优化

### ✅ 已完成
- 文件上传 + 自动类型识别
- 视频生成管线集成
- 任务进度实时追踪
- 作品广场展示
- Git 自动追溯
- 文本生成视频
- 相机上传按钮
- 删除功能

### ⏳ 已知问题
- **Gallery 路径问题**：联农丢失根因待排查（当前在 HEARTBEAT.md 待办中）
- 批量上传性能（大量文件时 scan 阻塞）
- 图片预览优化（大图缩略图）
- 搜索功能（按名称/类型搜索）

### 🔄 待开发
- 作品合集/分类管理
- 作品分享链接
- 权限控制（查看/上传/删除）
- 作品统计面板（播放量/下载次数）

---

> **总结**: Gallery 项目从 5/15 需求提出到 5/20 功能基本稳定，5天时间完成了从 0 到 1 的全功能产品。核心链路「上传→识别→生成→进度→展示」全部跑通，累计 ~2600 行代码，支撑了 48 件作品的展示和管理。
