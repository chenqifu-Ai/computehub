# ComputeHub 部署文档

> **版本**: 2026-05-11  
> **适用范围**: computehub-gateway / compute-worker / computehub-tui  
> **核心原则**: 先检查后执行，每步必须验证，验证失败立即停止

---

## 目录

1. [命名约定](#命名约定)
2. [目录结构](#目录结构)
3. [快速编译](#快速编译)
4. [本地运行](#本地运行)
5. [Docker 部署](#docker-部署)
6. [远程部署](#远程部署)
7. [版本升级](#版本升级)
8. [回滚](#回滚)
9. [部署检查清单](#部署检查清单)
10. [踩过的坑](#踩过的坑)
11. [故障排查](#故障排查)

---

## 命名约定

**代码硬编码的文件名（无版本号后缀）**：

| 组件 | 文件名 | 说明 |
|------|--------|------|
| Gateway | `computehub-gateway` | 服务主进程 |
| Worker (Linux ARM64) | `compute-worker-linux-arm64` | 主力平台 |
| Worker (Linux AMD64) | `compute-worker-linux-amd64` | x86_64 机器 |
| Worker (Windows) | `compute-worker-win-amd64.exe` | Windows 机器 |
| Worker (macOS) | `compute-worker-darwin-amd64` | macOS 测试 |
| TUI | `computehub-tui` | 终端界面 |

**为什么无后缀？** Worker 自升级通过 Gateway 的 `/api/v1/download?file=compute-worker-linux-arm64` 下载，URL 中的文件名是硬编码的，不能加版本号。

> ⚠️ **旧规范已废弃**: `deploy-versioning-standard.md` 中带的版本号后缀方案与代码不符，已停止使用。

---

## 目录结构

```
computehub/
├── cmd/                          # 入口
│   ├── gateway/main.go           # Gateway 入口
│   ├── worker/main.go            # Worker 入口
│   └── tui/main.go              # TUI 入口
├── src/                          # 14 个源包
│   ├── gateway/                  # HTTP 路由 + API
│   ├── kernel/                   # 确定性内核
│   ├── executor/                 # 命令执行
│   ├── scheduler/                # 调度器 + 熔断器
│   ├── composer/                 # AI 任务编排
│   ├── visualizer/              # WebSocket 推送
│   └── ...
├── deploy/                       # 部署目录（无后缀二进制）
│   ├── version.txt               # 当前版本号（升级链路唯一读取）
│   ├── computehub-gateway        # Gateway 二进制
│   ├── computehub-worker         # Worker 二进制
│   ├── computehub-tui           # TUI 二进制
│   └── archive/                  # 旧版本归档
├── bin/                          # 多平台编译产物
│   ├── linux-arm64/
│   ├── linux-amd64/
│   ├── windows-amd64/
│   └── darwin-amd64/
├── scripts/
│   └── deploy.sh                 # 一键部署脚本
├── config.json                   # 配置文件
└── deploy-docs.md               # 本文档
```

---

## 快速编译

```bash
cd /root/.openclaw/workspace/projects/computehub

# Gateway
CGO_ENABLED=0 go build -o computehub-gateway ./cmd/gateway/

# Worker
CGO_ENABLED=0 go build -o computehub-worker ./cmd/worker/

# TUI
CGO_ENABLED=0 go build -o computehub-tui ./cmd/tui/

# Windows Worker（交叉编译）
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o compute-worker-win-amd64.exe ./cmd/worker/
```

**环境变量说明**:
- `CGO_ENABLED=0` — 静态链接，不依赖系统 C 库
- `GOOS/GOARCH` — 指定目标平台
- `-ldflags="-X github.com/computehub/opc/src/version.VERSION=0.7.5"` — 注入版本号

---

## 本地运行

```bash
# 1. 确保 deploy/ 目录存在（Gateway 需要从这里提供文件下载）
mkdir -p deploy

# 2. 复制二进制到 deploy/
cp computehub-gateway deploy/computehub-gateway
cp computehub-worker deploy/computehub-worker

# 3. 写入版本号
echo "0.7.4" > deploy/version.txt

# 4. 启动 Gateway（端口 8282）
nohup ./deploy/computehub-gateway > gateway.log 2>&1 &

# 5. 验证
sleep 3
curl -s http://localhost:8282/api/health
```

**Worker 启动**:
```bash
./deploy/computehub-worker \
  --gw http://localhost:8282 \
  --node-id my-gpu-01 \
  --region cn-east
```

---

## Docker 部署

### 前置条件
- Docker 24.0+
- Docker Compose v2+

### 快速启动

```bash
cd projects/computehub

# 构建并启动所有服务
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f gateway
```

### 服务访问

| 服务 | 地址 | 说明 |
|------|------|------|
| Gateway API | http://localhost:8282 | REST API + Dashboard |
| TUI | `docker compose --profile tui run tui` | 交互式终端 |

---

## 远程部署

使用 `scripts/deploy.sh`：

```bash
# 只构建（本地全平台编译）
bash scripts/deploy.sh build 0.7.5

# 构建 + 远程部署（需要 sshpass）
bash scripts/deploy.sh all 192.168.2.140 'password' 0.7.5

# 只部署已构建的二进制到远程
bash scripts/deploy.sh deploy 192.168.2.140 'password' gateway

# 自定义环境变量
GATEWAY_ADDR=192.168.1.17:8282 NODE_ID=server-01 REGION=us-west \
  bash scripts/deploy.sh deploy 10.0.0.5 'password' all
```

**远程部署自动处理**:
1. 检测目标机器 OS（uname）
2. 选择对应平台的二进制
3. SCP 传输文件
4. chmod +x + systemd 配置
5. 重启服务 + 验证

---

## 版本升级

### Worker 自动升级流程

```
Worker 启动
  → GET /api/v1/upgrade/check?current_version=0.7.3&platform=linux/arm64
  → Gateway 读取 deploy/version.txt 得到最新 0.7.5
  → 版本不同 → 返回 download_url=/api/v1/download?file=compute-worker-linux-arm64
  → Worker 下载新二进制 → 重启
```

**关键文件**:
- `deploy/version.txt` — Worker 升级链路唯一读取的版本来源
- `deploy/compute-worker-linux-arm64` — 下载端点服务的二进制（无后缀）

### 手动版本升级

```bash
cd /root/.openclaw/workspace/projects/computehub

# 1. 编译新版本
CGO_ENABLED=0 go build -ldflags="-X main.Version=0.7.5" -o /tmp/gw-new ./cmd/gateway/
CGO_ENABLED=0 go build -ldflags="-X main.Version=0.7.5" -o /tmp/w-new ./cmd/worker/

# 2. 备份旧版本
cp deploy/computehub-gateway deploy/archive/computehub-gateway.bak

# 3. 部署新版本
cp /tmp/gw-new deploy/computehub-gateway
cp /tmp/w-new deploy/computehub-worker

# 4. 更新版本记录
echo "0.7.5" > deploy/version.txt

# 5. 重启 Gateway
pkill -f computehub-gateway; sleep 2
nohup deploy/computehub-gateway > gateway.log 2>&1 &

# 6. 验证
curl -s http://localhost:8282/api/health
```

---

## 回滚

```bash
cd /root/.openclaw/workspace/projects/computehub

# 从 archive 恢复
VERSION="0.7.4"
cp "deploy/archive/computehub-gateway.bak" deploy/computehub-gateway
echo "0.7.4" > deploy/version.txt

# 重启
pkill -f computehub-gateway; sleep 2
nohup deploy/computehub-gateway > gateway.log 2>&1 &
```

---

## 部署检查清单

每次部署按此顺序执行，每步通过才能继续。

### Phase 0: 启动前检查

```bash
# 0.1 确认项目目录
cd /root/.openclaw/workspace/projects/computehub
pwd

# 0.2 确认源码版本
cat src/version/version.go | grep VERSION
cat VERSION 2>/dev/null || echo "(VERSION 文件不存在)"

# 0.3 确认 Go 环境
go version

# 0.4 确认端口占用
ss -tlnp | grep 8282 2>/dev/null || echo "端口空闲"

# 0.5 确认 deploy/ 目录
ls deploy/version.txt deploy/computehub-gateway 2>/dev/null || echo "⚠️ deploy/ 缺失"
```

### Phase 1: 编译

```bash
# 编译 Gateway
CGO_ENABLED=0 go build -o /tmp/computehub-gateway-test ./cmd/gateway/
test $? -eq 0 || { echo "❌ Gateway 编译失败"; exit 1; }
echo "✅ Gateway 编译成功: $(ls -lh /tmp/computehub-gateway-test | awk '{print $5}')"
```

### Phase 2: 验证

```bash
# 启动测试
nohup /tmp/computehub-gateway-test > /tmp/gw-test.log 2>&1 &
GW_PID=$!
sleep 3

# 健康检查
curl -s http://localhost:8282/api/health || { echo "❌ 健康检查失败"; kill $GW_PID; exit 1; }
echo "✅ Gateway 启动正常"

# 清理
kill $GW_PID 2>/dev/null; wait $GW_PID 2>/dev/null
```

### Phase 3: 正式部署

```bash
# 备份旧二进制
test -f deploy/computehub-gateway && cp deploy/computehub-gateway deploy/archive/

# 部署新二进制
cp /tmp/computehub-gateway-test deploy/computehub-gateway
chmod +x deploy/computehub-gateway

# 更新版本号
echo "$(cat src/version/version.go | grep 'VERSION' | cut -d'"' -f2)" > deploy/version.txt

# 重启 Gateway
pkill -f computehub-gateway 2>/dev/null; sleep 2
nohup deploy/computehub-gateway > gateway.log 2>&1 &
sleep 3

# 验证
curl -s http://localhost:8282/api/health | grep -q Healthy && echo "✅ 部署成功"
```

---

## 踩过的坑

### 🔴 致命错误

**坑 1: 文件拷贝后不检查完整性**
```bash
# ❌ 错误
cp source target

# ✅ 正确
cp source target
md5sum source target  # 必须完全一致
```

**坑 2: 启动新进程前不 kill 旧进程**
```bash
# ❌ 错误
nohup ./new-gateway > new.log 2>&1 &
# 端口被占，新进程启动失败

# ✅ 正确
pkill -f computehub-gateway 2>/dev/null
sleep 2
ss -tlnp | grep 8282 && echo "端口仍被占用" || echo "端口已释放"
nohup ./deploy/computehub-gateway > new.log 2>&1 &
```

**坑 3: 跨平台编译没设环境变量**
```bash
# ❌ 错误（在 Linux 上编译 Windows 版本）
go build -o worker.exe ./cmd/worker/  # 可能包含 CGO 依赖

# ✅ 正确
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o worker.exe ./cmd/worker/
```

**坑 4: deploy/ 目录缺失导致 404**
- Worker 自升级通过 `GET /api/v1/download?file=compute-worker-linux-arm64` 下载二进制
- 如果 `deploy/` 目录不存在，`findDeployDir()` 找不到文件，返回 404
- **修复**: 每次部署前确保 `deploy/` 存在且包含对应二进制

**坑 5: Windows 机器部署了 Linux 二进制**
- 现象: `exec: "sh": executable file not found in %PATH%`
- 根因: cqf-worker-02 (192.168.1.8) 是 Windows 10，但跑了 Linux worker
- 修复: 部署 `compute-worker-win-amd64.exe` 而非 `compute-worker-linux-amd64`
- 确认方法: `curl .../tasks/detail?task_id=xxx` 看 stdout/stderr

**坑 6: 路由处理器注册重复**
- `Serve()` 和 `ServeWithServer()` 两套方法各注册一遍路由
- `ServeHTTP()` 的 switch case 也要同步
- **规范**: 每次修改路由，必须 3 处同步

### 🟡 严重错误

**坑 7: 代码改了一处忘了另一处**
- 只改了 `Serve()` 里的路由，没改 `ServeWithServer()` 和 `ServeHTTP()`
- **规范**: 改路由必须 3 处同步

**坑 8: 改完代码不编译就部署**
- **规范**: 改完 → 编译 → 验证编译产物 → 再部署

**坑 9: 多个修改混在一起**
- **规范**: 每次只改一个东西，编译验证通过再做下一个

---

## 故障排查

### Gateway 不启动
```bash
# 1. 查看日志
tail -50 gateway.log | grep -i "error\|fatal"

# 2. 检查端口占用
ss -tlnp | grep 8282

# 3. 验证二进制
strings deploy/computehub-gateway | grep -i "version"

# 4. 检查配置
cat config.json | python3 -m json.tool
```

### Worker 注册失败
```bash
# 1. 检查 Gateway 是否运行
curl -s http://localhost:8282/api/health

# 2. 检查网络连接
ping 192.168.1.17
nc -zv 192.168.1.17 8282

# 3. 检查启动参数
# --gw 地址是否正确
# --node-id 是否重复
```

### 下载端点 404
```bash
# 1. 确认 deploy/ 目录存在
ls -la deploy/compute-worker-linux-arm64

# 2. 确认文件名正确（无版本号后缀）
ls deploy/compute-worker-*

# 3. 验证端点
curl -s "http://localhost:8282/api/v1/download?file=compute-worker-linux-arm64" \
  -o /tmp/test-worker -w "HTTP %{http_code}, %{size_download} bytes"
```

### Worker 升级 404
```bash
# 1. 确认 deploy/version.txt 存在且有版本号
cat deploy/version.txt

# 2. 确认二进制文件存在且无后缀
ls deploy/compute-worker-linux-arm64

# 3. 手动测试升级检查
curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=0.7.3&platform=linux/arm64" | python3 -m json.tool
```

---

## API 参考

### 任务 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks/submit` | 提交任务 |
| POST | `/api/v1/tasks/poll` | Worker 轮询任务 |
| GET | `/api/v1/tasks/detail?task_id=xxx` | 任务详情 |
| GET | `/api/v1/tasks/progress?task_id=xxx` | 任务输出 |
| POST | `/api/v1/tasks/progress` | Worker 推送输出 |
| POST | `/api/v1/tasks/cancel?task_id=xxx` | 取消任务 |
| GET | `/api/v1/tasks/list` | 任务列表 |

### 节点 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/nodes/register` | Worker 注册 |
| POST | `/api/v1/nodes/heartbeat` | 心跳 |
| GET | `/api/v1/nodes/list` | 节点列表 |

### 文件 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/download?file=NAME` | 下载二进制 |
| GET | `/api/v1/upgrade/check` | 检查升级 |
| POST | `/api/v1/upgrade/config` | 设置版本（内部） |

---

> 最后更新: 2026-05-11  
> 维护者: 小智  
> 本文档是部署的唯一权威来源，旧文档见 `_archive/deploy/`
