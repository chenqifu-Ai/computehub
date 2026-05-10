# ComputeHub 部署标准规范

> **核心原则**: 先检查后执行，每步必须验证，验证失败立即停止，不跳过步骤。
> 本规范覆盖过去两周踩过的所有坑，每次部署按检查清单走一遍。

---

## 第一部分：踩过的坑（为什么每次都出错）

### 🔴 致命错误 — 每次部署都犯的

#### 坑1: 文件拷贝后不检查完整性
**现象**: `cp` 执行了，但文件可能不完整或没覆盖成功，直接启动旧二进制
**正确做法**: 每次 cp 后立即 md5sum 对比
```bash
cp source target
md5sum source target  # 必须完全一致
```

#### 坑2: 启动新进程前不 kill 旧进程
**现象**: 新旧两个进程在跑，新进程失败或端口被占，还以为是新代码的问题
**正确做法**: 先杀旧进程，sleep 2，再启动新进程
```bash
ps aux | grep computehub-gateway | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2
# 验证端口已释放
ss -tlnp | grep 8282  # 应该无输出
# 再启动
nohup ./deploy/ubuntu/bin/computehub-gateway > /tmp/gateway-new.log 2>&1 &
```

#### 坑3: 跨平台编译没设环境变量
**现象**: Linux 上直接 go build 编译 Windows 版本，CGO 失败
**正确做法**: 跨平台编译必须显式设置 GOOS/GOARCH/CGO_ENABLED
```bash
# Windows Worker
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o deploy/windows-worker/compute-worker-win-amd64.exe ./cmd/worker/
```

#### 坑4: 没确认 Gateway CWD 就定位文件
**现象**: Gateway 从 `deploy/ubuntu/bin/` 启动，CWD 不是项目根目录。代码里用相对路径找 deploy/，找不到就 404
**正确做法**: 用 `findDeployDir()` 从二进制目录找，或者确认 CWD 后再访问
```bash
# 验证 Gateway CWD
cat /proc/PID/cwd
# 部署前确认 deploy/ 在 CWD 下可用
ls -la deploy/
```

#### 坑5: 没验证网络就尝试远程部署
**现象**: Windows 上 curl 失败，以为是二进制问题，实际是网络不通
**正确做法**: 先 ping + nc，通了再传文件
```bash
ping -c 3 192.168.1.8 && nc -zv 192.168.1.8 8282
```

#### 坑6: 版本不一致没发现就部署
**现象**: 源码 0.7.1，二进制 0.7.0，跑的是旧代码
**正确做法**: 每次部署前对比版本号
```bash
cat VERSION  # 源码版本号
strings binary | grep -oE "0\.[0-9]+\.[0-9]+" | head -1  # 二进制内嵌版本
```

### 坑10: 没确认 worker 运行在什么系统上就用错二进制
**现象**: cqf-worker-02 是 Windows 机器（hostname: LAPTOP-QOVCUVAG, Intel i5-13500H, Windows 10.0.26200），但跑的是 Linux worker 二进制（`exec.Command("sh", "-c", cmd)`）
**正确做法**: 部署前先确认目标机器的 OS 类型，再选择对应的二进制
**检查命令**:
```bash
# 提交测试任务确认 OS
curl -X POST http://localhost:8282/api/v1/tasks/submit \
  -d '{"command":"echo OS_CHECK && hostname && uname -a && ver"}'
# 查看任务结果，根据命令输出判断 OS
```

#### 坑10 实际案例（2026-05-09 07:45）
- **发现**: cqf-worker-02 的 hostname = LAPTOP-QOVCUVAG
- **证据**: `ver` 输出 Windows 10.0.26200.8328，`wmic` 能执行成功
- **stderr**: `'uname' 不是内部或外部命令` — Windows CMD 报错
- **根因**: Windows 机器上部署了 Linux worker 二进制
- **纠正**: 停止 Linux worker，部署 Windows worker 二进制
- **影响**: 之前所有对 cqf-worker-02 的测试都是"Windows 机器跑 Linux 二进制"的混合状态

### 坑11: 没区分清楚 Worker 类型和 OS 对应关系
**现象**: cqf-worker-02 本身就是 Windows 机器，一直以为是 Linux worker
**正确做法**: 通过任务执行结果反推 OS（cmd vs sh 命令）
**检查命令**:
```bash
# 查看最近任务执行结果
curl -s "http://localhost:8282/api/v1/tasks/detail?task_id=xxx"
# 根据 stdout/stderr 判断 OS
# Windows 输出: ver, wmic, hostname
# Linux 输出: uname -a, free -h, df -h
```

### 🟡 严重错误 — 导致返工的

#### 坑7: 代码改了一处忘了另一处
**现象**: 只改了 Serve()，忘了 ServeWithServer() 和 ServeHTTP()，导致测试时不生效
**正确做法**: 每次改路由，必须同步改3处：
- Serve() 里的 http.HandleFunc
- ServeWithServer() 里的 http.HandleFunc
- ServeHTTP() 里的 switch case

#### 坑8: 改完代码不编译就部署
**现象**: 以为改了就能用，实际跑的还是旧二进制
**正确做法**: 改完代码 → 编译 → 验证编译产物 → 再部署

#### 坑9: 多个修改混在一起做
**现象**: 同时改多个文件，出了问题不知道哪个导致的
**正确做法**: 每次只改一个东西，编译验证通过再做下一个

---

## 第二部分：部署检查清单

### Phase 0: 启动前检查（每次必须执行）

```bash
# 0.1 确认当前工作目录
cd /root/.openclaw/workspace/projects/computehub
pwd
echo "CWD: $(pwd)"

# 0.2 确认源码状态
git status --short
git log --oneline -3
echo "源码版本: $(cat src/version/version.go | grep 'const VERSION' | cut -d'"' -f2)"

# 0.3 确认 Go 环境
go version
echo "GOOS=$GOOS GOARCH=$GOARCH CGO_ENABLED=$CGO_ENABLED"

# 0.4 确认端口占用
ss -tlnp | grep 8282 2>/dev/null || netstat -tlnp | grep 8282 2>/dev/null
echo "端口检查: $(ss -tlnp | grep 8282 2>/dev/null || echo '端口空闲')"

# 0.5 确认目录结构
ls -la deploy/windows-worker/*.exe 2>/dev/null || echo "Windows二进制: 未找到"
ls -la deploy/ubuntu/bin/ 2>/dev/null || echo "Ubuntu目录: 未找到"
```

**通过标准**: 全部执行成功，无 error

### Phase 1: 代码编译

```bash
# 1.1 编译 Gateway
CGO_ENABLED=0 go build -o /tmp/computehub-gateway-test ./cmd/gateway/
if [ $? -ne 0 ]; then echo "❌ 编译失败"; exit 1; fi
echo "✅ Gateway 编译成功: $(ls -lh /tmp/computehub-gateway-test | awk '{print $5}')"

# 1.2 编译 Windows Worker (如需要)
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o deploy/windows-worker/compute-worker-win-amd64.exe ./cmd/worker/
if [ $? -ne 0 ]; then echo "❌ 编译失败"; exit 1; fi
echo "✅ Windows Worker 编译成功: $(ls -lh deploy/windows-worker/compute-worker-win-amd64.exe | awk '{print $5}')"
```

**通过标准**: 编译无 error

### Phase 2: 本地验证（不启动，先验证代码正确性）

```bash
# 2.1 检查二进制包含修改的函数
strings /tmp/computehub-gateway-test | grep handleFileDownload
if [ $? -ne 0 ]; then echo "❌ 函数不存在于二进制中"; exit 1; fi
echo "✅ handleFileDownload 函数已编译"

# 2.2 验证版本一致性
BINARY_VERSION=$(strings /tmp/computehub-gateway-test | grep -oE "0\.[0-9]+\.[0-9]+" | head -1)
SOURCE_VERSION=$(cat src/version/version.go | grep 'const VERSION' | cut -d'"' -f2)
echo "二进制版本: $BINARY_VERSION | 源码版本: $SOURCE_VERSION"
# 如果不同，记录差异但不阻塞

# 2.3 验证 Gateway 启动（临时启动测试）
nohup /tmp/computehub-gateway-test > /tmp/gateway-test.log 2>&1 &
GW_PID=$!
sleep 3
curl -s http://localhost:8282/api/health
echo ""

# 2.4 验证新端点
curl -s "http://localhost:8282/api/v1/download?file=compute-worker-win-amd64.exe" -o /tmp/test-download.exe -w "HTTP %{http_code}, %{size_download} bytes\n"

# 2.5 验证下载完整性
ORIG_MD5=$(md5sum deploy/windows-worker/compute-worker-win-amd64.exe | awk '{print $1}')
TEST_MD5=$(md5sum /tmp/test-download.exe | awk '{print $1}')
if [ "$ORIG_MD5" != "$TEST_MD5" ]; then echo "❌ MD5 不匹配"; kill -9 $GW_PID 2>/dev/null; exit 1; fi
echo "✅ MD5 一致: $ORIG_MD5"

# 2.6 清理测试进程
kill -9 $GW_PID 2>/dev/null
```

**通过标准**: 所有验证通过，MD5 一致

### Phase 3: 正式部署

```bash
# 3.1 备份旧二进制
cp deploy/ubuntu/bin/computehub-gateway deploy/ubuntu/bin/computehub-gateway.bak.$(date +%s)
echo "✅ 备份完成"

# 3.2 部署新二进制
cp /tmp/computehub-gateway-test deploy/ubuntu/bin/computehub-gateway
NEW_MD5=$(md5sum deploy/ubuntu/bin/computehub-gateway | awk '{print $1}')
if [ "$NEW_MD5" != "$(md5sum /tmp/computehub-gateway-test | awk '{print $1}')" ]; then echo "❌ 部署失败，文件不一致"; exit 1; fi
echo "✅ 部署完成: $NEW_MD5"

# 3.3 停止旧进程
ps aux | grep computehub-gateway | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 2
echo "✅ 旧进程已停止"

# 3.4 验证端口释放
PORT_IN_USE=$(ss -tlnp | grep 8282 2>/dev/null || echo "")
if [ -n "$PORT_IN_USE" ]; then echo "❌ 端口仍被占用: $PORT_IN_USE"; exit 1; fi
echo "✅ 端口已释放"

# 3.5 启动新 Gateway
nohup ./deploy/ubuntu/bin/computehub-gateway > /tmp/gateway-new.log 2>&1 &
GW_PID=$!
echo "✅ 新进程 PID: $GW_PID"
sleep 3

# 3.6 验证 Gateway 运行
HEALTH=$(curl -s http://localhost:8282/api/health)
if echo "$HEALTH" | grep -q "Healthy"; then echo "✅ Gateway 健康检查通过"; else echo "❌ Gateway 启动失败"; tail -20 /tmp/gateway-new.log; exit 1; fi

# 3.7 验证新端点
DL_CODE=$(curl -s "http://localhost:8282/api/v1/download?file=compute-worker-win-amd64.exe" -o /dev/null -w "%{http_code}")
if [ "$DL_CODE" = "200" ]; then echo "✅ 下载端点正常 (HTTP $DL_CODE)"; else echo "❌ 下载端点异常 (HTTP $DL_CODE)"; exit 1; fi

# 3.8 验证节点列表
NODES=$(curl -s http://localhost:8282/api/v1/nodes/list | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['data']))" 2>/dev/null || echo "无法解析")
echo "✅ 节点数: $NODES"

# 3.9 记录部署信息
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gateway 部署完成: PID=$GW_PID MD5=$NEW_MD5" >> /tmp/gateway-deploy.log
```

**通过标准**: 所有验证步骤通过

### Phase 4: 远程部署 (仅当 Gateway 本地验证通过后执行)

```powershell
# 4.1 网络连通性检查
curl -v --connect-timeout 5 http://192.168.1.17:8282/api/health
if ($LASTEXITCODE -ne 0) { Write-Host "❌ 网络不通，终止部署"; exit 1 }
Write-Host "✅ 网络连通"

# 4.2 下载二进制
mkdir C:\computehub -Force
curl -o "C:\computehub\compute-worker-win-amd64.exe" "http://192.168.1.17:8282/api/v1/download?file=compute-worker-win-amd64.exe" -UseBasicParsing
$file = Get-Item "C:\computehub\compute-worker-win-amd64.exe"
if ($file.Length -ne 9027072) { Write-Host "❌ 文件大小错误: $($file.Length) 字节, 预期 9027072"; exit 1 }
Write-Host "✅ 文件下载成功: $($file.Length) bytes"

# 4.3 启动 Worker
$proc = Start-Process "C:\computehub\compute-worker-win-amd64.exe" -ArgumentList "--gw", "http://192.168.1.17:8282", "--node-id", "win-01", "--region", "cn-east" -PassThru -WindowStyle Hidden
Write-Host "✅ Worker 已启动 PID: $($proc.Id)"
Start-Sleep -Seconds 10

# 4.4 验证注册
$nodes = curl -s http://192.168.1.17:8282/api/v1/nodes/list | ConvertFrom-Json
if ($nodes.data.Count -ge 2) { Write-Host "✅ win-01 已注册，集群节点数: $($nodes.data.Count)" }
else { Write-Host "⚠️ 节点列表: $(($nodes.data | ForEach-Object { $_.node_id }) -join ', ')" }
```

**通过标准**: 网络连通、文件正确、Worker 启动、节点列表更新

---

## 第三部分：故障排查速查

### Gateway 不启动
```
1. tail -50 /tmp/gateway-new.log | grep -i "error\|fatal\|fatal"
2. ss -tlnp | grep 8282  (端口是否被占)
3. ls -la deploy/ubuntu/bin/computehub-gateway  (文件是否存在)
4. strings deploy/ubuntu/bin/computehub-gateway | grep handleFileDownload  (函数是否存在)
5. cat deploy/ubuntu/config/config.json  (配置是否合法)
```

### 下载端点 404
```
1. 确认 Gateway 版本包含 handleFileDownload
2. 确认 deploy/ 目录在 Gateway 可访问的位置
3. 确认文件名在白名单内
4. 验证: strings binary | grep handleFileDownload
```

### Worker 注册失败
```
1. 确认启动参数: --gw http://正确IP:8282
2. 确认网络: ping + nc
3. 确认 Gateway 日志: grep NODE_REGISTER /tmp/gateway-new.log
4. 确认 Worker 二进制版本与 Gateway 兼容
```

### 编译失败
```
1. 确认 Go 版本: go version (≥ 1.24)
2. 确认在项目根目录: pwd && ls go.mod
3. 确认无破坏性修改: git status
4. 查看详细错误: go build -v 2>&1 | tail -20
```

---

## 第四部分：快速参考

### 关键路径
```
源码: /root/.openclaw/workspace/projects/computehub
Gateway二进制: deploy/ubuntu/bin/computehub-gateway
Windows Worker: deploy/windows-worker/compute-worker-win-amd64.exe
配置文件: deploy/ubuntu/config/config.json
临时编译: /tmp/computehub-gateway-test
Gateway日志: /tmp/gateway-new.log
```

### 关键端口
```
Gateway: 8282
```

### 关键命令
```bash
# 编译
CGO_ENABLED=0 go build -o computehub-gateway ./cmd/gateway/
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o worker.exe ./cmd/worker/

# 部署
cp source target && md5sum source target  # 必须一致
ps aux | grep process | awk '{print $2}' | xargs kill -9; sleep 2
nohup ./target > /tmp/log.log 2>&1 &

# 验证
curl -s http://localhost:8282/api/health
curl -s "http://localhost:8282/api/v1/download?file=NAME" -o /dev/null -w "%{http_code}"
curl -s http://localhost:8282/api/v1/nodes/list | python3 -m json.tool
```

### 版本对照
```
源码: src/version/version.go → const VERSION = "0.7.1"
VERSION文件: VERSION → 0.7.0
Windows 二进制: v0.7.0 (May 7) ← 需重新编译
Gateway 二进制: v0.7.1 (刚刚编译) ← 已更新
```

---

## 第五部分：本次调试决策记录

### 2026-05-09 06:25-06:40 添加下载端点
**决策**: Gateway 加 `/api/v1/download` 端点让 Windows 自己拉二进制
**理由**: 
- 无法远程操作 Windows 机器，让它主动从 Gateway 拉文件
- 符合自举传输理念（之前文档提过的方案）
**修改**: `src/gateway/gateway.go` — 5处同步修改
**验证**: HTTP 200, 9MB, MD5 一致

### 2026-05-09 07:00-07:16 发现流程问题
**发现**: 每次都在不同环节出错，没有检查机制
**原因**: 缺少标准流程，凭感觉操作
**对策**: 本规范 — 每步必验证，错了就停

### 2026-05-09 07:30-07:45 发现重大认知错误
**发现**: cqf-worker-02 本身就是 Windows 机器（hostname: LAPTOP-QOVCUVAG）
- Windows 10.0.26200.8328, Intel i5-13500H, 8GB 内存
- 但跑的是 **Linux worker 二进制**（exec.Command("sh", "-c", ...)）
- 不是 Windows worker 二进制（应该是 exec.Command("cmd", "/c", ...)）
- 错误信息: `exec: "sh": executable file not found in %PATH%`
**根因**: 部署了错误的二进制文件到 Windows 机器
**纠正**: 停止 Linux worker，部署 Windows worker 二进制
**影响**: 之前所有对 cqf-worker-02 的操作都是错的——cqf-worker-02 就是 192.168.1.8

### 2026-05-09 07:50 状态确认（cqf-worker-02 重启后）
```
cqf-worker-02: ✅ 已重新上线（之前离线过，重启后 online）
cqf-worker-02 OS: Windows 10.0.26200 (LAPTOP-QOVCUVAG)
cqf-worker-02 二进制: Linux worker (错误) → 需要换成 Windows worker
cqf-worker-02 CPU: Intel i5-13500H (8核), 8GB RAM
cqf-worker-02 硬盘: C:200G, D:562G, E:195G
cqf-worker-02 GPU: 无 GPU (CPU 模式)
Gateway: ✅ v0.7.1 运行中 (PID 5218), 下载端点正常
Windows 二进制: deploy/windows-worker/compute-worker-win-amd64.exe (6.2MB, 已重新编译)
```

### 2026-05-09 07:55 当前核心任务
```
任务: cqf-worker-02 换 Windows 二进制并重启
步骤:
  1. cqf-worker-02 自己下载新版 Windows 二进制
  2. 替换旧二进制
  3. 重启 worker 进程
  4. 验证注册成功并在线

下载端点: http://192.168.1.17:8282/api/v1/download?file=compute-worker-win-amd64.exe
启动命令: compute-worker.exe --gw http://192.168.1.17:8282 --node-id cqf-worker-02 --region cn-east

注意: 不需要 192.168.1.8 了，cqf-worker-02 就是那台 Windows 机器
```

---

> 最后更新: 2026-05-09 07:30
> 维护者: 小智
> 更新频率: 每次重大部署或版本变更后
> 任何人看到这个文件，按 Phase 0→1→2→3→4 顺序执行，每步通过才能继续。

### 2026-05-09 07:55 当前状态
```
Gateway: ✅ v0.7.1 运行中 (PID 5218)
cqf-worker-02: ✅ online (Windows 10.0.26200, LAPTOP-QOVCUVAG)
cqf-worker-02 二进制: Linux worker (错误) → 需要换成 Windows worker
Windows 二进制: deploy/windows-worker/compute-worker-win-amd64.exe
下载端点: http://192.168.1.17:8282/api/v1/download
```
