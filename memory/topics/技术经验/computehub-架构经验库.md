# 🏗️ ComputeHub 架构经验库

## 一、源码目录结构

```
computehub/
├── cmd/              # 入口
│   ├── gateway/main.go    → Gateway 服务（API + 可视化）
│   ├── worker/main.go     → Worker Agent（执行任务）
│   ├── node/main.go       → 节点注册 CLI 工具
│   └── tui/main.go        → TUI 终端界面
├── src/              # 核心包
│   ├── gateway/           → API 路由、节点/任务管理、文件下载
│   ├── kernel/            → 任务调度、状态机、节点管理
│   ├── executor/          → 命令执行器（sh -c）
│   ├── composer/          → LLM 任务分解
│   ├── scheduler/         → 任务调度算法
│   ├── pure/              → 过滤管道（语法/语义/边界/上下文）
│   ├── gene/              → 基因存储器（学习优化）
│   ├── discover/          → 节点发现
│   ├── health/            → 健康检查
│   ├── monitor/           → 监控
│   ├── prometheus/        → 指标收集
│   ├── visualizer/        → 全球算力地图 + v2 API
│   └── version/           → 版本号管理
├── deploy/            # 部署文件（二进制 + 脚本）
│   ├── windows-worker/    → Windows Worker 部署包
│   └── version.txt        → 版本标识（用于 auto-upgrade 检测）
├── code/              # Dashboard 前端
├── scripts/           # 工具脚本
└── config.json        # Gateay 配置
```

## 二、Gateway（核心 API 服务）

### 启动流程
```go
main.go → loadConfig() → gateway.NewOpcGateway(port, config) → gw.Serve(port, dashboardDir)
```

### 内部组件
```
OpcGateway {
    Kernel        — 任务调度 + 节点管理 + 状态机
    Pipeline      — 请求过滤管道（语法/语义/边界过滤）
    Executor      — 本地命令执行器
    GeneStore     — 学习/优化记忆
    Composer      — LLM 任务分解器
    TaskDispatcher — 从 kernel 队列拿任务 → 本地 Runner 执行
    Metrics       — Prometheus 指标
    Scheduler     — 任务调度算法
}
```

### API 路由（全部 v1）
```
POST   /api/dispatch              — 遗留调度
GET    /api/health                — 健康检查
GET    /api/status                — 系统状态

POST   /api/v1/nodes/register     — 节点注册
POST   /api/v1/nodes/unregister   — 节点注销
POST   /api/v1/nodes/heartbeat    — 心跳上传
GET    /api/v1/nodes/list         — 节点列表
GET    /api/v1/nodes/metrics      — 节点指标

POST   /api/v1/tasks/submit       — 提交任务（node_id + command）
POST   /api/v1/tasks/result       — 提交结果
POST   /api/v1/tasks/cancel       — 取消任务
GET    /api/v1/tasks/list         — 任务列表
GET    /api/v1/tasks/detail       — 任务详情
POST   /api/v1/tasks/poll         — Worker 轮询待处理任务
POST   /api/v1/tasks/progress     — 流式输出推送

GET    /api/v1/download?file=xxx  — 文件下载（Worker 自举传输）
GET    /api/v1/upgrade/check      — 检查更新
POST   /api/v1/upgrade/config     — 设置版本号
```

### API 响应格式
```json
{"id": "", "success": true, "data": {...}, "error": "<nil>", "verified": false, "duration": "15.1µs"}
```

## 三、Worker Agent

### 启动流程
```
main() → runWorker() 循环（退出后 3s 自动重启）
  parseConfig()           — CLI 参数（--gw, --node-id, --gpu-type 等）
  state.register()        — POST /api/v1/nodes/register
  go state.heartbeatLoop() — 每 10s 发送心跳
  go state.upgradeLoop()   — 每 5min 检查更新
  go state.taskPollLoop()  — 每 500ms 轮询任务
  等待 SIGINT/SIGTERM
```

### Worker CLI 参数
```
--gw <url>       Gateway 地址（默认 http://localhost:8282）
--node-id <id>   节点 ID（默认 worker-<hostname>）
--gpu-type <t>   GPU 型号
--region <r>     区域（默认 cn-east）
--interval <s>   轮询间隔秒（默认 0.5）
--heartbeat <s>  心跳间隔秒（默认 10）
--concurrent <n> 最大并发（默认 4）
```

### 平台适配（worker_util_*.go）
| 功能 | Linux | Windows |
|------|-------|---------|
| 命令执行 | `sh -c` | `cmd /c` |
| 内存检测 | `/proc/meminfo` | `GlobalMemoryStatusEx` |
| CPU 负载 | `/proc/loadavg` | 固定 50% |
| GPU 检测 | nvidia-smi | nvidia-smi |
| 进程终止 | SIGTERM | Kill |

### 任务执行流程（executeTask）
```
pollTask() → 领取任务
  └→ cmd = runCommand(task.Command) → Stdout/Stderr PIPE
  └→ cmd.Start()
  └→ 两个 goroutine 分别读 stdout/stderr
  └→ streamTicker 每 500ms 推送增量到 /api/v1/tasks/progress
  └→ cmd.Wait() → 收集最终结果
  └→ submitTaskResult() → POST /api/v1/tasks/result
  └→ saveTaskReport() → 写本地 JSON 报告
```

## 四、自动升级系统（auto_upgrade.go）

### 工作流程
```
Worker 启动 → 10s 后 → upgradeLoop() goroutine
  每 5min: GET /api/v1/upgrade/check?current_version=X&node_id=Y
  ├→ 无更新 → 继续等待 5min
  └→ 有更新 → performUpgrade()
      1. 下载新二进制到 .compute-worker.upgrade
      2. 文件大小验证（非致命）
      4. 备份旧版 → xxx.bak.v0.7.0
      5. 新版替换旧版
      6. unregister() 通知 Gateway
      7. 启动新版进程，旧版 os.Exit(0)
```

### Gateway 端（gateway_upgrade.go）
- `deploy/version.txt` 存最新版本号
- `deploy/compute-worker-*` 二进制
- `GET /api/v1/upgrade/check` → 对比版本号，返回是否有更新
- `POST /api/v1/upgrade/config` → 管理员手动设置版本号

### 部署文件结构
```
deploy/
├── version.txt                                          → "0.7.1"
├── compute-worker-linux-amd64                           → Linux x86_64 Worker
├── compute-worker-linux-arm64                           → Linux ARM64 Worker
├── windows-worker/
│   ├── compute-worker-win-amd64.exe                     → Windows x86_64 Worker
│   ├── deploy.ps1                                       → Windows 部署脚本
│   └── worker-source.go                                 → 源码（备用）
```

## 五、编译命令速查

```bash
# 本机 ARM64
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o ./deploy/computehub-gateway-linux-arm64 ./cmd/gateway/
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o ./deploy/compute-worker-linux-arm64 ./cmd/worker/

# 服务器 x86_64
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o ./deploy/computehub-gateway-linux-amd64 ./cmd/gateway/
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o ./deploy/compute-worker-linux-amd64 ./cmd/worker/

# Windows
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -o ./deploy/windows-worker/compute-worker-win-amd64.exe ./cmd/worker/

# 版本升级步骤
# 1. 改 src/version/version.go VERSION
# 2. 编译新二进制
# 3. echo 新版本号 > deploy/version.txt
# 4. 部署新 Gateway
# 5. Worker 5min 内自动检测→下载→替换→重启
```

## 六、关键约定

### Worker 部署命令（最常用）
```bash
# Windows（cmd）
certutil -urlcache -f http://192.168.1.7:8282/api/v1/download?file=compute-worker-win-amd64.exe D:\computehub-worker.exe
&& taskkill /F /IM computehub-worker.exe
&& start /min D:\computehub-worker.exe --gw http://192.168.1.7:8282 --node-id cqf-worker-03 --region cn-east --interval 0.5 --heartbeat 10 --concurrent 4
```

### Gateway 部署（192.168.1.7）
```bash
# 停止旧版 → 复制新版 → 重启
# Gateway 运行在 8282 端口
# 本机（arm64）编译前必须 CGO_ENABLED=0（否则 cgo net 报错）
```

### 测试脚本模板
```python
import requests, time

def submit_and_wait(node_id, cmd, timeout=20, max_poll=15):
    tid = f"test-{int(time.time()*1000)}"
    r = requests.post("http://192.168.1.7:8282/api/v1/tasks/submit", json={
        "task_id": tid, "node_id": node_id,
        "command": cmd, "timeout_seconds": timeout
    }, timeout=10)
    for _ in range(max_poll):
        time.sleep(2)
        gr = requests.get(f"http://192.168.1.7:8282/api/v1/tasks/detail?task_id={tid}&node_id={node_id}")
        d = gr.json().get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return None
```

### 已知坑
1. Gateway 本机 arm64 编译需要 `CGO_ENABLED=0`（cgo newres 报错）
2. edit 工具在重复文本处会失败 → 用 Python 脚本
3. Worker 旧版二进制硬编码 `sh -c` → Windows 任务全失败（新版已用 `cmd /c`）
4. content 字段 null 问题（zhangtuo-ai-common provider 特有）

---

*最后更新: 2026-05-09*
