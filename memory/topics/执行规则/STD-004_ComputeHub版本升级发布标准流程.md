# STD-004: ComputeHub 版本升级与发布标准流程

## 1. 概述

**目的**: 统一 ComputeHub 版本发布和节点升级流程，确保所有节点（Linux/Windows）可自动或手动完成升级。

**核心原则**: 
- 统一 binary（`computehub`）一编多用，不再分拆多个独立二进制
- 跨平台编译必须从源码同一 commit 出发
- 所有 deploy 文件必须有 SHA256 校验和
- Linux 节点可通过 Gateway 自动升级；Windows 节点通过新版 Worker 30分钟自动检测升级

## 2. 版本号管理

版本号在 `src/version/version.go` 中定义：
```go
var VERSION = "1.3.1"
```

**规则**:
- 编译时通过 `-ldflags="-X .../version.BUILD=$(date +%s)"` 注入构建时间戳
- 版本号仅通过修改源码 `version.go` 变更，不用 ldflags 注入 VERSION

## 3. 发布步骤

### 3.1 编译跨平台二进制

在开发机（支持交叉编译的 arm64 设备）上执行：

```bash
# 进入项目根目录
cd /path/to/OPC

# 记录当前版本
VERSION=$(grep 'VERSION = ' src/version/version.go | head -1 | cut -d'"' -f2)
echo "Building v$VERSION"

# Linux amd64 (ECS 主力)
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
  -ldflags="-s -w -X github.com/computehub/opc/src/version.BUILD=$(date +%s)" \
  -o /tmp/computehub-linux-amd64 ./cmd/computehub/

# Windows amd64
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build \
  -ldflags="-s -w -X github.com/computehub/opc/src/version.BUILD=$(date +%s)" \
  -o /tmp/computehub-windows-amd64.exe ./cmd/computehub/
```

**注意**: 必须加 `CGO_ENABLED=0`，否则 arm64 交叉编译 amd64 会报 `gcc_amd64.S: error: unknown token` 错误。

### 3.2 计算 SHA256 校验和

```bash
sha256sum /tmp/computehub-linux-amd64 | cut -d' ' -f1
sha256sum /tmp/computehub-windows-amd64.exe | cut -d' ' -f1
```

### 3.3 更新 ECS 上的 deploy/ 目录

```bash
# SSH 到 ECS
DEPLOY=/home/computehub/ComputeHub/deploy

# 复制 Linux binary
cp /tmp/computehub-linux-amd64 $DEPLOY/computehub
chmod 755 $DEPLOY/computehub

# 复制 Windows binary（统一 binary computehub.exe）
cp /tmp/computehub-windows-amd64.exe $DEPLOY/computehub.exe
chmod 755 $DEPLOY/computehub.exe
cp /tmp/computehub-windows-amd64.exe $DEPLOY/windows-worker/computehub.exe
chmod 755 $DEPLOY/windows-worker/computehub.exe

# 复制到平台子目录（日志兼容）
mkdir -p $DEPLOY/linux-amd64 $DEPLOY/windows-amd64
cp /tmp/computehub-linux-amd64 $DEPLOY/linux-amd64/computehub
cp /tmp/computehub-windows-amd64.exe $DEPLOY/windows-amd64/computehub.exe

# 写 SHA256 校验和文件
echo "<LINUX_SHA256>  computehub" > $DEPLOY/sha256sums-$VERSION.txt
echo "<WIN_SHA256>  computehub.exe" >> $DEPLOY/sha256sums-$VERSION.txt
echo "<WIN_SHA256>  windows-worker/computehub.exe" >> $DEPLOY/sha256sums-$VERSION.txt

# 更新版本号
echo -n "$VERSION" > $DEPLOY/version.txt
```

### 3.4 启动 / 重启 Gateway

```bash
# Kill old gateway
kill $(pgrep -f "computehub gateway") 2>/dev/null

# Start new gateway
cd /home/computehub && nohup ./computehub gateway > /dev/null 2>&1 &
```

Gateway 重启后，Worker 会在下一次心跳时通过 `GET /api/v1/upgrade/check?current_version=...&platform=...` 检测到新版本并自动触发升级。

## 4. 节点升级机制

### 4.1 新版 Worker 自动升级（推荐方式）

所有新版 Worker（v1.3.1+）内置 `UpgradeManager`，启动后自动执行：

```
Worker → 每 30 分钟 → 检查 Gateway /api/v1/upgrade/check
  ├─ 无新版本 → 继续等待
  └─ 有新版本 → 
       ├─ 条件检查（无活跃任务、磁盘空间>20MB、冷却>5min）→ 跳过则等待下次
       ├─ 下载 binary + SHA256 校验
       ├─ 执行 --version 验证
       ├─ 备份当前 binary
       ├─ 生成独立升级脚本（.sh / .bat）
       ├─ 进程退出，脚本接替
       └─ 脚本：等待→替换→验证→启动新Worker→健康检查→失败回滚
```

**策略可配置**（通过环境变量 `COMPUTEHUB_UPGRADE_STRATEGY`）：
- `auto` — 检测到新版立即升级（默认）
- `scheduled` — 只在凌晨窗口（02:00-04:00）内升级
- `manual` — 只缓存不执行，等管理员指令
- `rolling` — 逐节点滚动升级（预留）

### 4.2 Windows 节点手动升级（首次部署用）

当 Windows 节点跑的是旧版（无 UpgradeManager）时，通过 Gateway 提交任务手动推送：

```python
# 分步执行（避免 cmd & 截断 URL）
1. submit('curl -sf -o C:\\computehub_new.exe "http://<ECS_IP>:8282/api/v1/download?file=computehub.exe"', 60)
2. submit('C:\\computehub_new.exe version', 10)  # 验证 v1.3.1
3. submit('taskkill /f /im computehub.exe', 10)
4. submit('timeout /t 3', 10)
5. submit('copy /Y C:\\computehub_new.exe C:\\computehub.exe', 10)
6. submit('start /B C:\\computehub.exe worker --agent --gw http://<ECS_IP>:8282 --node-id <NODE_ID> --interval 3 --concurrent 8 --heartbeat 10', 10)
```

**关键经验**:
- Windows cmd 中 `&` 是命令分隔符，URL 带 `?file=xxx` 时会被截断
- **必须用双引号包裹整个 URL**: `"http://...?file=computehub.exe"`
- 多个命令用 `^&` 逃逸：`cmd1 ^&^& cmd2` 或分多次提交

### 4.3 Linux Worker 升级（自动）

ECS 上跑的新版 Worker 自带 UpgradeManager，检测到新版本后自动下载→验证→替换→重启，无需人工介入。

## 5. 验证清单

发布后必须验证以下内容：

| 检查项 | 方法 | 预期 |
|--------|------|------|
| Gateway 存活 | `curl http://<ECS>:8282/api/health` | `"ComputeHub System Healthy"` |
| deploy/ version.txt | `cat deploy/version.txt` | 版本号正确 |
| SHA256 校验和 | `cat deploy/sha256sums-<VERSION>.txt` | 3行（linux + windows x 2） |
| Linux 节点自动升级 | 查看 worker.log | UpgradeManager 触发升级 |
| Windows 节点状态 | curl nodes/list | `platform=windows/amd64` |
| Gateway 版本响应 | `curl .../upgrade/check?current_version=...&platform=windows/amd64` | `update_available: true/false` |
| 文件下载 | `curl .../download?file=computehub.exe -o /dev/null -w "%{size_download}"` | >10MB |

## 6. 已知问题 / 注意事项

1. **Windows cmd URL 截断**: `&` 字符在 cmd 中是命令分隔符，URL 必须加双引号
2. **交叉编译必须 CGO_ENABLED=0**: arm64 设备上交叉编译 amd64 需要关闭 CGO
3. **旧 WMI agent 不支持 base64**: 旧版 `WMI-agent` 直接传命令，不支持 `__base64:` 前缀
4. **升级完成后 ActiveTasks 不归零**: 见 `gateway_worker.go` 的 `findPendingTaskForNode` bug（已修复）

---

*版本: 1.0 | 制定: 2026-06-02 | 适用于: ComputeHub 统一 binary 架构*