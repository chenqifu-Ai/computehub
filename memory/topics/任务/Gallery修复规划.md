# 🎬 Gallery 修复规划 (2026-05-21)

## 📋 任务状态
- **状态**: ⏸ 已规划，待执行
- **优先级**: 低
- **来源**: Gallery 上传文件生成视频时3个任务失败

## 🔍 已确认的信息

### Gallery 架构
- Gallery HTML 是**内嵌在 Go 二进制**中的常量
- 文件位置: `src/gateway/gallery.go` → `const galleryHTML = `...``
- 编译后部署到 ECS: 36.250.122.43:8222

### 连接信息
- `ssh -p 8222 computehub@36.250.122.43`
- 密码: `c9fc9f,.`
- 当前版本: v0.7.12-amd64
- 源码目录: `/home/computehub/src/src/gateway/gallery.go`
- 部署目录: `/home/computehub/gallery/`

### 已修复的 HTML 文件
- 本地: `ai_agent/code/gallery_fixed.html`
- 修复内容: 文件名为纯英文避免乱码、docx MIME 类型修复等

## 🏗 修复方案

### 推荐方案：先诊断 → 再修复 → 编译部署

#### 步骤 1：日志诊断
```bash
# 查看 worker 日志
cat /home/computehub/worker.log | tail -100
# 查看任务进度
ls -la /tmp/computehub-video/progress/
cat /tmp/computehub-video/progress/<task_id>.json
```

#### 步骤 2：检查关键依赖
- `video_worker.py` 是否存在及路径
- ffmpeg 是否可用
- 字体文件是否存在（文字直出用）

#### 步骤 3：根据诊断修代码
- 如果 `video_worker.py` 找不到 → 修正路径或脚本
- 如果 ffmpeg 报错 → 修复 ffmpeg 参数
- 如果是文件名问题 → 修复 escape/编码
- 合并之前修复好的 HTML 优化

#### 步骤 4：编译部署
```bash
# 在服务器上编译
cd /home/computehub/src
go build -o ../computehub ./cmd/computehub/

# 重启 gateway
pkill -f "computehub.*gateway" || true
sleep 1
cd /home/computehub && ./computehub gateway &
```

### 备选方案 A：直接改 HTML + 服务器编译（最快）
修改 `gallery_fixed.html` → 注入到服务器 `gallery.go` → `go build` → 重启 gateway

### 备选方案 B：本地交叉编译后 scp
本地 linux/amd64 交叉编译 → scp 二进制 → 重启

## 📂 相关文件
| 文件 | 路径 |
|------|------|
| 修复后的 HTML | `ai_agent/code/gallery_fixed.html` |
| 源码（本地） | `projects/computehub/src/gateway/gallery.go` |
| 源码（服务器） | `/home/computehub/src/src/gateway/gallery.go` |
| 部署脚本 | `/home/computehub/scripts/build_all.sh` |
| worker 日志 | `/home/computehub/worker.log` |
| gateway 日志 | `/home/computehub/gateway.log` |
