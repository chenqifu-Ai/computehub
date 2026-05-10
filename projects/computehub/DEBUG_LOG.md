# ComputeHub Windows Worker 调试日志

> 记录所有调试决策、代码位置、编译参数，方便任何人/会话接续

---

## 1. 架构理解

### 1.1 组件关系
```
Windows 192.168.1.8 (待部署)
  ↓ HTTP
Gateway 192.168.1.17:8282 (已运行)
  ↓
cqf-worker-02 (Linux, 已在线)
```

### 1.2 Worker 通信协议
Worker 向 Gateway 发送三个请求：
```
1. 注册: POST /api/v1/nodes/register
   Body: {node_id, gpu_type, region, cpu_cores, memory_gb, status, ip_address, max_concurrency}
   失败时自动重试 (10s 间隔)

2. 心跳: POST /api/v1/nodes/heartbeat (每10s)
   Body: {node_id, gpu_utilization, gpu_temperature, memory_used_gb, memory_total_gb, cpu_load}

3. 轮询任务: POST /api/v1/tasks/poll (每5s)
   Body: {node_id, gpu_type, region, running_task_count}
   有任务则执行，无任务则 sleep 5s 重试
```

### 1.3 Worker 启动流程
```
main() → parseConfig() → register() → [start heartbeatLoop()] → [start taskPollLoop()] → <-sigCh
```

---

## 2. 代码修改记录

### 2.1 Gateway 下载端点 (2026-05-09 06:25-06:40)

**文件**: `src/gateway/gateway.go`

**修改1**: import 新增 `"os"`
```go
import (
    ...
    "os"    // ← 新增
    ...
)
```

**修改2**: Serve() 注册端点
```go
// 位置: 第270行附近 (Serve 函数)
http.HandleFunc("/api/v1/download", g.handleFileDownload)
logWithTimestamp("📦 Download endpoint registered: /api/v1/download")
```

**修改3**: ServeWithServer() 注册端点
```go
// 位置: 第300行附近 (ServeWithServer 函数)
http.HandleFunc("/api/v1/download", g.handleFileDownload)
logWithTimestamp("📦 Download endpoint registered: /api/v1/download")
```

**修改4**: ServeHTTP() 添加 case
```go
// 位置: 第365行附近 (ServeHTTP 函数)
case "/api/v1/download":
    g.handleFileDownload(w, r)
```

**修改5**: 新增 handler 和辅助函数
```go
// 位置: 文件末尾 (第865行后)

func findDeployDir() string {
    // 1. 尝试 CWD/deploy
    // 2. 尝试 二进制目录/deploy
    // 3. 回退到 deploy
}

func (g *OpcGateway) handleFileDownload(w http.ResponseWriter, r *http.Request) {
    // 1. 检查 GET 方法
    // 2. 检查文件名白名单 (compute-worker-*, compute-gateway-*, computehub-tui, opc-*)
    // 3. 定位 deploy 目录
    // 4. 尝试 deploy/filename
    // 5. 尝试 deploy/windows-worker/filename
    // 6. 返回文件
}
```

**验证**:
```bash
# 编译
cd /root/.openclaw/workspace/projects/computehub
CGO_ENABLED=0 go build -o /tmp/computehub-gateway-v071-patch ./cmd/gateway/
# 编译成功

# 部署
cp /tmp/computehub-gateway-v071-patch deploy/ubuntu/bin/computehub-gateway

# 重启
kill -9 4080  # 旧进程
nohup ./deploy/ubuntu/bin/computehub-gateway > /tmp/gateway-v071p.log 2>&1 &
# 新进程 PID 5218

# 测试
curl -s http://localhost:8282/api/health
# {"id":"health-check","success":true,"data":"ComputeHub System Healthy",...}

curl -s "http://localhost:8282/api/v1/download?file=compute-worker-win-amd64.exe" -o /tmp/test.exe -w "%{http_code} %{size_download}\n"
# HTTP 200 9027072

# 校验
md5sum /tmp/test.exe
# ff267914628ac05627548a5cf1c7851a  (与源码二进制一致)
```

---

## 3. 编译配置

### 3.1 Gateway (Linux AMD64)
```bash
cd /root/.openclaw/workspace/projects/computehub
CGO_ENABLED=0 go build -o computehub-gateway ./cmd/gateway/
```

### 3.2 Windows Worker (待编译最新版)
```bash
cd /root/.openclaw/workspace/projects/computehub
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o deploy/windows-worker/compute-worker-win-amd64.exe ./cmd/worker/
```

### 3.3 当前 Windows 二进制信息
- 文件: `deploy/windows-worker/compute-worker-win-amd64.exe`
- 大小: 9,027,072 bytes (9MB)
- 时间: 2026-05-07 05:07
- 版本: 0.7.0 (从字符串中识别)
- 编译参数: CGO_ENABLED=1 (包含 Windows API 调用)

---

## 4. Windows 部署方案

### 4.1 方案 A: 从 Gateway 下载 (推荐)
```powershell
# 1. 创建目录
New-Item -ItemType Directory -Force -Path "C:\computehub"

# 2. 下载二进制
Invoke-WebRequest -Uri "http://192.168.1.17:8282/api/v1/download?file=compute-worker-win-amd64.exe" -OutFile "C:\computehub\compute-worker-win-amd64.exe" -UseBasicParsing

# 3. 验证
(Get-Item "C:\computehub\compute-worker-win-amd64.exe").Length
# 应该输出 9027072

# 4. 启动
Start-Process "C:\computehub\compute-worker-win-amd64.exe" -ArgumentList "--gw", "http://192.168.1.17:8282", "--node-id", "win-01", "--region", "cn-east" -WindowStyle Hidden
```

### 4.2 方案 B: 从本机复制
```powershell
# 从本机复制到 192.168.1.8 (需要凭据)
$cred = Get-Credential
Copy-Item -Path "\\192.168.1.17\share\computehub\compute-worker-win-amd64.exe" -Destination "C:\computehub\" -Credential $cred
```

### 4.3 方案 C: 手动拷贝
1. 用 U盘/局域网共享 把 `compute-worker-win-amd64.exe` 拷到 192.168.1.8
2. 在 192.168.1.8 上执行方案 A 的第3、4步

---

## 5. 已知问题和约束

### 5.1 版本不一致
- 源码版本: 0.7.1 (src/version/version.go)
- Windows 二进制: 0.7.0
- **影响**: 无，注册/心跳协议未变更，可兼容

### 5.2 Gateway CWD 问题
- Gateway 从 `deploy/ubuntu/bin/` 启动
- `findDeployDir()` 会查找二进制目录下的 deploy/ 或 CWD 的 deploy/
- Windows 二进制已放到 `deploy/ubuntu/deploy/` (通过之前的复制)

### 5.3 网络约束
- 192.168.1.8 必须能访问 192.168.1.17:8282
- Windows 防火墙需放行出站 TCP 8282 (或测试时临时关闭)

### 5.4 GPU 依赖
- Worker 用 `nvidia-smi` 采集 GPU 信息
- 没有 GPU 会自动识别为 CPU 模式 (不影响功能)

---

## 6. 调试步骤记录

### 步骤 1: Gateway 加下载端点 (2026-05-09 06:25-06:40)
- [x] 阅读 Gateway 代码结构
- [x] 确定 3 处修改点 (Serve, ServeWithServer, ServeHTTP)
- [x] 实现 findDeployDir() 和 handleFileDownload()
- [x] 添加 `"os"` import
- [x] 编译验证 (CGO_ENABLED=0 go build)
- [x] 部署二进制
- [x] 重启 Gateway
- [x] 测试下载端点 (HTTP 200, MD5 验证)
- 耗时: ~15分钟

### 步骤 2: 尝试连接 192.168.1.8 (2026-05-09 06:40-07:00)
- [x] 检查节点注册情况
- [x] 查看 Gateway 日志
- [x] 确认只有 cqf-worker-02 在线
- [x] 发现 192.168.1.8 远程不通
- [ ] 未能连接到 192.168.1.8
- 卡住原因: 无法远程操作 Windows 机器

### 步骤 3: 整理调试计划 (2026-05-09 07:00-07:16)
- [x] 记录所有上下文
- [x] 编写 deploy.ps1 一键部署脚本
- [x] 创建调试日志 (本文件)
- [ ] 等待连接 192.168.1.8 的条件满足

---

## 7. 下一步操作指令

当获得 192.168.1.8 访问权限时，按以下顺序执行：

### 7.1 首次部署
```powershell
# 以管理员 PowerShell 运行
cd C:\
mkdir computehub -Force

# 从 Gateway 下载
curl -o C:\computehub\compute-worker-win-amd64.exe http://192.168.1.17:8282/api/v1/download?file=compute-worker-win-amd64.exe

# 验证大小
ls C:\computehub\compute-worker-win-amd64.exe
# 应该显示 9027072 bytes

# 启动 Worker
& C:\computehub\compute-worker-win-amd64.exe --gw http://192.168.1.17:8282 --node-id win-01 --region cn-east
```

### 7.2 验证上线
```bash
# 在 Gateway 侧检查
curl http://192.168.1.17:8282/api/v1/nodes/list
# 应该看到 2 个节点 (cqf-worker-02 和 win-01)

# 提交测试任务
curl -X POST http://192.168.1.17:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"node_id":"win-01","command":"echo WIN_TEST_OK && ver"}'

# 查看任务结果
curl http://192.168.1.17:8282/api/v1/tasks/list
```

### 7.3 配置为 Windows 服务 (可选)
```powershell
# 使用 NSSM 注册为服务
nssm install ComputeHubWorker "C:\computehub\compute-worker-win-amd64.exe"
nssm set ComputeHubWorker AppArguments "--gw http://192.168.1.17:8282 --node-id win-01 --region cn-east"
nssm set ComputeHubWorker AppDirectory "C:\computehub"
nssm set ComputeHubWorker Start SERVICE_AUTO_START
nssm start ComputeHubWorker
```

---

## 8. 相关文件索引

| 文件 | 说明 |
|------|------|
| `src/gateway/gateway.go` | Gateway 主文件 (已修改) |
| `src/version/version.go` | 版本定义 (0.7.1) |
| `cmd/worker/main.go` | Worker 主文件 (待编译) |
| `cmd/worker/worker_util_windows.go` | Windows 平台特定代码 |
| `deploy/windows-worker/worker-source.go` | Worker 源码 (943行) |
| `deploy/windows-worker/compute-worker-win-amd64.exe` | Windows 二进制 (v0.7.0) |
| `deploy/windows-worker/deploy.ps1` | 一键部署脚本 |
| `deploy/ubuntu/bin/computehub-gateway` | 当前运行中的 Gateway |
| `debug.log` | 本调试日志 |

---

> 最后更新: 2026-05-09 07:16
> 当前状态: 等待 192.168.1.8 连接权限
