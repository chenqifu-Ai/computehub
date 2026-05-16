# 🎬 "一键生成视频" 实施计划

**制定日期**: 2026-05-16  
**目标**: 修复视频管线现有问题，确保代码可靠  
**核心原则**: 不瞎编，每个问题必须代码验证

---

## 📊 当前状态评估

| 模块 | 状态 | 可信度 |
|------|------|--------|
| Gateway (Go) | ✅ 运行中 | 高 |
| Worker (Go) | ✅ 运行中 | 高 |
| Gallery (Go) | ✅ 运行中 | 高 |
| Scheduler | ⚠️ 代码存在，功能未充分验证 | 中 |
| video_pipeline.py | ⚠️ 代码存在，有大量待确认问题 | 低 |
| 文档与代码一致性 | ❌ 多处不一致 | 低 |

---

## 🔴 P0: 必须立即修复（代码级 Bug）

### 1. video_pipeline.py — ffmpeg 命令注入漏洞
**文件**: `scripts/video_pipeline.py`  
**问题**: 场景模板直接用 `format(**kwargs)` 拼接 ffmpeg 命令，`text` 参数中的特殊字符（引号、分号、管道符）可以注入任意命令。

```python
# 当前代码（危险）:
cmd = tmpl.format(**kwargs)  # text 中有 ' 或 ; | 等会被执行
```

**修复**: 用 `shlex.quote()` 包裹所有用户输入参数。

---

### 2. video_pipeline.py — 文字场景的 ffmpeg 命令有 bug
**文件**: `scripts/video_pipeline.py`  
**问题**: `title` 和 `subtitle` 模板使用 `-f lavfi -i color=... -d={duration}`，ffmpeg 的 `-d` 是 demuxer 级别的 duration 参数，对于 `color` 输入应该用 `-t`。

```python
# 当前代码:
"color=c={bg_color}:s={width}x{height}:d={duration}:r=30"
# color 滤镜的 d 参数是 duration 但 lavfi 需要 -t 控制输出时长
```

**修复**: 在 ffmpeg 命令中加 `-t {duration}` 参数。

---

### 3. video_pipeline.py — 字幕文字含特殊字符会崩溃
**文件**: `scripts/video_pipeline.py`  
**问题**: `drawtext` 滤镜中 text 参数如果包含 `:` `|` `'` 等字符，ffmpeg 会报错。需要用 `:` 转义。

```python
# 修复: 在 render 方法中对 text 做转义
text = kwargs['text'].replace(':', '\\:').replace('|', '\\|').replace("'", "\\'")
```

---

### 4. Worker main.go — `ctx` 变量声明未使用
**文件**: `cmd/worker/main.go`  
**问题**:
```go
ctx := s.client   // ← 声明了但没用
_ = ctx           // ← 用 _ 静默忽略，这是 bug 残留
```

**修复**: 删除这两行。

---

### 5. Worker main.go — 任务轮询使用旧的 API 端点
**文件**: `cmd/worker/main.go`  
**问题**: Worker 调用 `/api/v1/tasks/list` 拿任务，但 Gateway 的 `handleTaskList` 返回的数据格式是 `map[nodeID][]TaskInfo`。Worker 用 `tasks := listResp.Data[s.nodeID]` 拿自己的任务列表，这个逻辑是对的。

但 Worker 的 `taskPollLoop` 里拿到任务后调 `fetchTaskDetail(task.TaskID)`，而 Gateway 的 `handleTaskDetail` 需要 `task_id` 和 `node_id` 参数。**这个端点实际上已经实现了**（在 `gateway_worker.go`），所以这部分没问题。

**结论**: 任务轮询链路正确 ✅

---

### 6. Worker main.go — 超时后没有清理资源
**文件**: `cmd/worker/main.go`  
**问题**: `time.AfterFunc` 超时后发送 SIGTERM，如果进程不响应，3秒后 Kill。但 `delete(s.runningTasks, taskID)` 在超时定时器结束后才执行（defer），如果 Kill 成功，这部分没问题。但缺少 `exec.Cmd` 的 `SysProcAttr` 设置（无子进程泄漏）。

**修复**: 给 cmd 设置 `SysProcAttr.Setsid = true`，超时 kill 时用 `cmd.Process.Signal(syscall.SIGKILL)`。

---

## 🟡 P1: 需要改进（不致命但影响可靠性）

### 7. Worker main.go — nvidia-smi fallback 硬编码
**文件**: `cmd/worker/main.go`  
**问题**: `collectGPUStats` 中，如果 nvidia-smi 不可用，`MemoryTotalGB` 硬编码为 `80GB`。

```go
stats.MemoryTotalGB = float64(stats.Count) * 80 // rough estimate for H100
```

**修复**: 从 `/proc/meminfo` 读取总内存，或返回 0 表示未知。

---

### 8. video_pipeline.py — 字体搜索路径不完整
**文件**: `scripts/video_pipeline.py`  
**问题**: Android (Termux) 上字体路径可能在 `/data/data/com.termux/files/usr/share/fonts/` 或其他位置。当前只检查了 3 个常见路径。

**修复**: 增加 Termux 路径，或允许环境变量 `COMPUTEHUB_FONT` 指定字体。

---

### 9. Gateway — Gallery 硬编码根目录
**文件**: `src/gatewaycmd/cmd.go`  
**问题**: `RegisterGallery` 硬编码 `/var/computehub/gallery`。

**修复**: 从 config.json 的 `gallery.root_dir` 读取，或允许环境变量覆盖。

---

### 10. Scheduler — getCandidates 在遍历时修改 Status
**文件**: `src/scheduler/scheduler.go`  
**问题**: `getCandidates` 在遍历 `s.nodeIndex` 时检查超时，如果超时直接 `node.Status = "offline"`。但在 `ScheduleTask` 里又调了一次 `getCandidates`，同一个函数会被调用两次。

**修复**: 健康检查应该独立于调度。将超时检查移到单独的 `HealthCheck()` 方法。

---

### 11. Gateway — ServeHTTP 路由重复注册问题
**文件**: `src/gateway/gateway.go`  
**问题**: `ServeHTTP` 中 `/api/v1/download` 后面没有 handler 调用（只有 `case "/api/v1/download":` 然后 fallthrough），然后下一条直接调了 `g.handleFileDownload(w, r)`。这意味着 `ServeHTTP` 里 download 请求会直接调用 handler，但 `ServeWithServer` 里是通过 `http.HandleFunc` 注册的。两条路径功能一致但实现不同。

**修复**: 统一为 `ServeWithServer` 的路由方式（`http.HandleFunc`），删除 `ServeHTTP` 中的重复逻辑或确保两者完全一致。

---

### 12. video_pipeline.py — concat 拼接缺少音频
**文件**: `scripts/video_pipeline.py`  
**问题**: 拼接命令使用 `-c copy`，但如果各场景没有音频轨道，concat 会报 "concat demuxer: non-monotonous DTS" 错误。

**修复**: 在 concat 前先检测是否都有相同编解码器，如果没有音频，用 `-an` 或重新编码拼接。

---

## 🟢 P2: 优化建议（有时间再做）

### 13. 增加 video_pipeline.py 单元测试
覆盖 `find_font()`, `safe_filename()`, `run_cmd()` 等工具函数。

### 14. Worker 日志结构化
当前用 printf + ANSI 颜色，不方便 grep 和日志系统。改 JSON 日志。

### 15. 添加优雅停机
Gateway 收到 SIGTERM 后：停止接受新任务 → 等待现有任务完成（最多 60s） → 退出。

---

## 📅 执行顺序

```
1. 修复 P0 问题 (1-6) — 验证代码可编译
2. 运行测试: go test ./...
3. 视频管线功能测试 — 实际生成一个视频
4. 修复 P1 问题 (7-12)
5. 最终验证
```

---

## ⚠️ 关键发现（认真读代码后）

1. **video_pipeline.py 的 title 和 subtitle 模板有根本性 bug** — ffmpeg lavfi color 滤镜的 `-d` 参数不是输出时长，需要用 `-t` 控制。实际生成的视频可能是 0 秒或几秒。

2. **Worker 超时后进程可能残留** — `cmd.Process.Kill()` 在 defer 之前执行，但 `delete(s.runningTasks, ...)` 在 defer 中，如果 Kill 后程序 panic，字典不会清理。

3. **Gateway 路由注册方式不统一** — `Serve()` 用 `http.HandleFunc`，`ServeHTTP` 用 switch case，`ServeWithServer` 用 `http.HandleFunc` 但 `ServeHTTP` 里 `/api/v1/download` 的处理有 bug。

4. **视频管线没有任何转义** — 用户输入的 `text` 直接拼进 shell 命令，是命令注入漏洞。

5. **Scheduler 的 getCandidates 在调度中直接修改 node.Status** — 这违反了"只读检查"原则，应该在 HealthCheck 中做。
