# COM-DEP-001: 编译部署标准流程 v4.0 — 银河计划

**生效日期**: 2026-06-24  
**适用工程**: ComputeHub_new  
**维护者**: 端智  
**状态**: ✅ 已验证（v1.3.45 实战通过）

---

## 📌 架构概览

```
ComputeHub_new/
├── bin/              → 编译产物（git tracked）
├── deploy/           → 部署产物（git tracked）
│   ├── {version}/    → 版本归档
│   ├── {platform}/   → 当前平台 binary
│   ├── sha256sums-{version}.txt
│   └── version.txt
├── src/version/      → 版本号源码（需手动改 version.go）
├── scripts/          → 工具脚本
└── web/              → 文档
```

**关键路径**:
- 本地编译 → `deploy/` → Gallery 上传 → 远程节点自动升级
- 本地编译 → SCP → ECS 重启 → 集群验证
- Gallery 上传 → Windows 节点通过 ComputeHub 任务手动升级

---

## 🌌 银河计划集群拓扑

### 三层架构（与白皮书对齐）

```
        🌌 银河进化计划
           │
           ├── 🎮 协调层 (小智、端智)
           │    ├── 任务分配
           │    ├── 进度跟踪
           │    └── 异常处理
           │
           ├── 💻 计算层 (各节点)
           │    ├── GPU计算节点 (wanlida-opc01, RTX 4060)
           │    ├── CPU计算节点 (ECS, wanlida-ubuntu, xingke-work01)
           │    └── ARM计算节点 (local-arm, xiaomi-table)
           │
           └── 🌐 网络层
                ├── WebSocket通信 (ws://36.250.122.43:8282/api/v1/ws)
                ├── HTTP API (http://36.250.122.43:8282)
                └── 安全通道 (SSH 8022)
```

### 节点分工

| 节点 | 系统 | 架构 | IP | 角色 | 升级方式 |
|------|------|------|----|------|----------|
| **ECS Gateway** | Ubuntu | linux/amd64 | 36.250.122.43:8282 | 主 Gateway / 协调中心 | SCP + SSH 重启 |
| **ecs-p2ph** (小智) | Ubuntu | linux/amd64 | 36.250.122.43:8383 | 总指挥 / 协调层 | SCP + SSH 重启 |
| **local-arm** (端智) | Android Termux | linux/arm64 | 36.248.233.177 | 协调官 / 日常运维 | Gallery 自动升级 |
| **wanlida-opc01** | Windows Server 2022 | windows/amd64 | 183.251.21.92 | GPU计算主力 (RTX 4060) | ComputeHub 任务升级 |
| **wanlida-ubuntu** | Ubuntu | linux/amd64 | 112.48.4.56 | 计算平台 (达智Agent) | Gallery 自动升级 |
| **xingke-work01** | Windows | windows/amd64 | 120.41.115.133 | 计算节点 | ComputeHub 任务升级 |
| **windows-mobile01** | Windows | windows/amd64 | 112.48.104.210 | GPU计算节点 (10 GPU) | ComputeHub 任务升级 |
| **xiaomi-table** | Android | linux/arm64 | 112.48.48.185 | ARM移动计算 | Gallery 自动升级 |

### 唯一接入通道

**🚨 所有节点必须通过 ComputeHub Gateway 接入，禁止其他方式！**

- **唯一主 Gateway**: http://36.250.122.43:8282
- **唯一 WebSocket**: ws://36.250.122.43:8282/api/v1/ws
- **唯一 SSH**: 36.250.122.43:8022 (仅协调层使用)
- **禁止**: 直接 SSH 连接计算节点、使用其他 Gateway 地址、绕过 ComputeHub 的直接访问

### 进化路线图

| Phase | 状态 | 内容 |
|-------|------|------|
| **Phase 1: 基础建设** | ✅ 已完成 | 跨Agent通信、承诺管理、三国志后端API、协调框架 |
| **Phase 2: 协同计算** | 🟡 进行中 | AI大厅完善、任务智能分配、进度跟踪、安全审计 |
| **Phase 3: 自主进化** | ⏳ 规划中 | 自主学习优化、创新探索、多领域扩展、自组织生态 |

### 参考文档

- 银河计划白皮书: `~/GalaxyPlan/docs/galaxy_whitepaper.md` (ECS)
- Windows Agent 修复经验: `memory/topics/技术经验/Windows_Agent修复经验总结.md`
- 集群跨Agent通信标准: `memory/topics/执行规则/CLU-STM-001_集群跨Agent通信标准流程.md`

---

## 🎯 核心原则（精简版）

1. **版本号三统一**: git tag = version.go = deploy/version.txt
2. **Gateway 二进制不动 systemd** — 直接替换 deploy/computehub 后重启
3. **远程节点不 scp** — 通过 Gallery 自动升级（Windows 节点通过 ComputeHub 任务手动触发）
4. **ECS 远端仓库是唯一真相源** — 本地 push 后 ECS pull
5. **银河计划全集群验证** — 部署后检查所有节点版本一致

---

## 📋 标准流程（6 步法）

### Step 0: 前置检查

```bash
cd /data/data/com.termux/files/home/ComputeHub_new

# 确认当前版本
cat deploy/version.txt
git tag -l | sort -V | tail -3

# 确认 git 状态干净
git status --short

# 确认 ECS 可达
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 -o ConnectTimeout=5 computehub@36.250.122.43 "echo OK"
```

### Step 1: 版本号 + Tag

```bash
# 1a. 改 version.go（从 "dev" → 目标版本）
# 文件: src/version/version.go
# 改: var VERSION = "dev" → var VERSION = "1.3.46"

# 1b. 打 tag
git tag v1.3.46

# 1c. 验证 tag 生效
bash scripts/get_version.sh   # 应输出 1.3.46
```

### Step 2: 编译

```bash
bash scripts/build_all.sh
# 产出: bin/{5 platforms}/computehub
# 验证: file bin/linux-arm64/computehub → ARM aarch64
```

### Step 3: 同步 deploy/ + Gallery 上传

```bash
bash scripts/sync-deploy.sh
# 产出: deploy/1.3.46/ + deploy/{platform}/ + sha256sums
# 自动: Gallery 上传 3 个平台 binary 到 ECS Gateway
```

### Step 4: 部署到 ECS（Gateway + Worker）

```bash
# 4a. SCP 新 binary
scp -i ~/.ssh/id_ed25519_computehub -P 8022 \
  deploy/computehub-linux-amd64 \
  computehub@36.250.122.43:/home/computehub/ComputeHub/deploy/computehub

# 4b. 重启 Gateway + Worker（一条命令）
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  # 停旧进程
  pkill -9 -f computehub 2>/dev/null
  sleep 3
  fuser -k 8282/tcp 2>/dev/null
  fuser -k 8383/tcp 2>/dev/null
  sleep 2

  # 更新 version.txt
  echo "1.3.46" > /home/computehub/ComputeHub/deploy/version.txt

  # 启动 Gateway
  nohup /home/computehub/ComputeHub/deploy/computehub gateway --port 8282 > /tmp/gw.log 2>&1 &
  sleep 4

  # 启动 Worker
  nohup /home/computehub/ComputeHub/deploy/computehub worker --agent \
    --gw http://127.0.0.1:8282 --node-id ecs-p2ph \
    --interval 3 --concurrent 8 --heartbeat 10 > /tmp/worker.log 2>&1 &
  sleep 6

  # 验证
  echo "=== Gateway ==="
  ss -tlnp | grep 8282
  echo "=== Worker ==="
  ss -tlnp | grep 8383
  echo "=== Version ==="
  /home/computehub/ComputeHub/deploy/computehub --version
'
```

### Step 5: 银河计划 — 全集群节点升级

#### 5a. Linux 节点（Gallery 自动升级）

Linux 节点（local-arm、wanlida-ubuntu、xiaomi-table）会在 30 分钟升级检查周期内自动升级。如需立即升级：

```bash
# 通过 ECS Gateway 触发升级检查
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  # 触发 local-arm 升级检查
  curl -s "http://127.0.0.1:8282/api/v1/upgrade/check?current_version=1.3.45&platform=linux/arm64&node_id=local-arm"
  echo ""
  # 触发 wanlida-ubuntu 升级检查
  curl -s "http://127.0.0.1:8282/api/v1/upgrade/check?current_version=1.3.45&platform=linux/amd64&node_id=wanlida-ubuntu"
  echo ""
  # 触发 xiaomi-table 升级检查
  curl -s "http://127.0.0.1:8282/api/v1/upgrade/check?current_version=1.3.45&platform=linux/arm64&node_id=xiaomi-table"
'
```

#### 5b. Windows 节点（ComputeHub 任务升级）

Windows 节点（wanlida-opc01、xingke-work01、windows-mobile01）通过 ComputeHub 任务手动触发升级。

**升级脚本模板**（PowerShell -EncodedCommand）：

```powershell
# 1. 下载新 binary
$url = "http://36.250.122.43:8282/api/v1/files/computehub-windows-amd64.exe"
$dest = "C:\ComputeHub\computehub.exe"
$backup = "C:\ComputeHub\computehub.exe.bak"

# 2. 备份旧 binary
Copy-Item $dest $backup -Force

# 3. 下载新 binary
Invoke-WebRequest -Uri $url -OutFile $dest -TimeoutSec 30

# 4. 验证下载
if ((Get-Item $dest).Length -gt 10MB) {
    Write-Output "✅ 下载成功: $((Get-Item $dest).Length) bytes"
} else {
    Write-Output "❌ 下载失败，文件太小"
    Copy-Item $backup $dest -Force
    exit 1
}

# 5. 重启 Worker（通过 taskkill + 新进程）
$workerPid = (Get-Process -Name "computehub" -ErrorAction SilentlyContinue).Id
if ($workerPid) {
    Stop-Process -Id $workerPid -Force
    Start-Sleep -Seconds 3
}

# 6. 启动新 Worker
$gwUrl = "http://36.250.122.43:8282"
$nodeId = "wanlida-opc01"  # 按节点修改
Start-Process -FilePath $dest -ArgumentList "worker --agent --gw $gwUrl --node-id $nodeId --interval 3 --concurrent 4 --heartbeat 10"

Write-Output "✅ 升级完成，Worker 已重启"
```

**生成 EncodedCommand 并提交任务**：

```bash
# 生成 EncodedCommand
python3 -c "
import base64, sys
script = '''$url = \"http://36.250.122.43:8282/api/v1/files/computehub-windows-amd64.exe\"
$dest = \"C:\\\ComputeHub\\\computehub.exe\"
$backup = \"C:\\\ComputeHub\\\computehub.exe.bak\"
Copy-Item \$dest \$backup -Force
Invoke-WebRequest -Uri \$url -OutFile \$dest -TimeoutSec 30
if ((Get-Item \$dest).Length -gt 10MB) {
    Write-Output \"✅ 下载成功: \$((Get-Item \$dest).Length) bytes\"
} else {
    Write-Output \"❌ 下载失败\"
    Copy-Item \$backup \$dest -Force
    exit 1
}
\$workerPid = (Get-Process -Name \"computehub\" -ErrorAction SilentlyContinue).Id
if (\$workerPid) { Stop-Process -Id \$workerPid -Force; Start-Sleep -Seconds 3 }
Start-Process -FilePath \$dest -ArgumentList \"worker --agent --gw http://36.250.122.43:8282 --node-id wanlida-opc01 --interval 3 --concurrent 4 --heartbeat 10\"
Write-Output \"✅ 升级完成\"
'''
b64 = base64.b64encode(script.encode('utf-16le')).decode()
print(b64)
" > /tmp/win_upgrade_b64.txt

# 通过 ComputeHub 提交任务到 Windows 节点
# 方式：通过 ECS Gateway API 提交
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  B64=$(cat /tmp/win_upgrade_b64.txt)
  curl -s -X POST "http://127.0.0.1:8282/api/v1/tasks/submit" \
    -H "Content-Type: application/json" \
    -d "{
      \"node_id\": \"wanlida-opc01\",
      \"type\": \"exec\",
      \"command\": \"powershell -EncodedCommand ${B64}\",
      \"timeout\": 60
    }"
'
```

> **注意**: 每个 Windows 节点需修改 `node-id` 和脚本中的 `$nodeId` 变量。

### Step 6: 验证 + Git 提交

#### 6a. 验证 ECS 集群

```bash
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  echo "=== Health ==="
  curl -s http://127.0.0.1:8282/api/health
  echo ""
  echo "=== Nodes ==="
  curl -s http://127.0.0.1:8282/api/v1/nodes/list | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d.get(\"data\",[]):
    print(f\"  {n['node_id']:20s} {n['status']:10s} v{n['version']}\")
"
'
```

#### 6b. 验证下载链路

```bash
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  for plat in linux/amd64 linux/arm64 windows/amd64; do
    echo "=== ${plat} ==="
    curl -s --max-time 10 "http://127.0.0.1:8282/api/v1/download?file=computehub&platform=${plat}" -o /tmp/test-${plat//\//-} -w "%{size_download}B\n"
    file /tmp/test-${plat//\//-}
  done
  rm -f /tmp/test-*
'
```

#### 6c. 验证升级检查

```bash
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  for node in local-arm ecs-p2ph wanlida-ubuntu; do
    echo "=== ${node} ==="
    curl -s "http://127.0.0.1:8282/api/v1/upgrade/check?current_version=1.3.45&platform=linux/arm64&node_id=${node}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"  update_available={d['data']['update_available']}, latest={d['data']['latest_version']}\")
"
  done
'
```

#### 6d. 银河计划全集群版本一致性检查

```bash
# 通过 ECS Gateway 获取所有节点版本
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  echo "=== 🌌 银河计划集群版本状态 ==="
  curl -s http://127.0.0.1:8282/api/v1/nodes/list | python3 -c "
import sys,json
d=json.load(sys.stdin)
nodes = d.get(\"data\",[])
versions = set()
for n in nodes:
    v = n.get(\"version\",\"unknown\")
    versions.add(v)
    status_icon = \"🟢\" if n[\"status\"] == \"online\" else \"🔴\"
    print(f\"  {status_icon} {n['node_id']:20s} v{v:10s} {n['status']}\")
print()
if len(versions) == 1:
    print(f\"  ✅ 全集群版本一致: v{list(versions)[0]}\")
elif len(versions) == 0:
    print(\"  ⚠️  无节点在线\")
else:
    print(f\"  ⚠️  版本不一致: {versions}\")
print(f\"  📊 在线: {d.get('online_nodes',0)} / 总计: {d.get('total_nodes',0)}\")
"
'
```

#### 6e. Git 提交 + 推送

```bash
git add -A
git commit -m "deploy: 发布 v1.3.46（银河计划）"
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_computehub -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
  git push origin master --force
```

---

## 🚀 一键部署（银河计划版）

```bash
# 完整流程：编译 → 同步 → SCP → 重启 → 银河节点升级 → 验证 → 提交
# 前提: version.go 已改好 + git tag 已打

cd /data/data/com.termux/files/home/ComputeHub_new
VERSION=$(bash scripts/get_version.sh)

echo "=== 1/6 编译 ===" && bash scripts/build_all.sh && \
echo "=== 2/6 同步 ===" && bash scripts/sync-deploy.sh && \
echo "=== 3/6 SCP ===" && \
  scp -i ~/.ssh/id_ed25519_computehub -P 8022 deploy/computehub-linux-amd64 \
    computehub@36.250.122.43:/home/computehub/ComputeHub/deploy/computehub && \
echo "=== 4/6 重启 ECS ===" && \
  ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 "
    pkill -9 -f computehub 2>/dev/null; sleep 3; fuser -k 8282/tcp 2>/dev/null; fuser -k 8383/tcp 2>/dev/null; sleep 2;
    echo '${VERSION}' > /home/computehub/ComputeHub/deploy/version.txt;
    nohup /home/computehub/ComputeHub/deploy/computehub gateway --port 8282 > /tmp/gw.log 2>&1 & sleep 4;
    nohup /home/computehub/ComputeHub/deploy/computehub worker --agent --gw http://127.0.0.1:8282 --node-id ecs-p2ph --interval 3 --concurrent 8 --heartbeat 10 > /tmp/worker.log 2>&1 & sleep 6;
    echo 'GW:' && ss -tlnp | grep 8282;
    echo 'Worker:' && ss -tlnp | grep 8383;
    echo 'Ver:' && /home/computehub/ComputeHub/deploy/computehub --version;
  " && \
echo "=== 5/6 银河节点升级（Linux 自动 / Windows 手动）===" && \
  echo "  Linux 节点将在 30 分钟内自动升级" && \
  echo "  Windows 节点需通过 ComputeHub 任务手动触发" && \
echo "=== 6/6 验证 + 提交 ===" && \
  ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 "
    echo '=== 集群状态 ===';
    curl -s http://127.0.0.1:8282/api/v1/nodes/list | python3 -c \"
import sys,json
d=json.load(sys.stdin)
for n in d.get('data',[]):
    print(f\\\"  {'🟢' if n['status']=='online' else '🔴'} {n['node_id']:20s} v{n['version']:10s} {n['status']}\\\")
print(f\\\"  📊 在线: {d.get('online_nodes',0)} / 总计: {d.get('total_nodes',0)}\\\")
\";
  " && \
  git add -A && git commit -m "deploy: 发布 v${VERSION}（银河计划）" && \
  GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_computehub -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    git push origin master --force && \
echo "🎉 v${VERSION} 银河计划部署完成"
```

---

## ⚠️ 常见问题（实战踩坑记录）

### Q1: version.go 还是 "dev"
**原因**: 源码中 `var VERSION = "dev"`，ldflags 注入只在构建时生效  
**解决**: 每次发版前手动改 version.go 为实际版本号

### Q2: ECS 上 version.txt 是 "dev"
**原因**: sync-deploy.sh 没同步到 ECS，或旧版遗留  
**解决**: 重启时手动 `echo "1.3.46" > deploy/version.txt`

### Q3: SHA256 校验失败
**原因**: ECS deploy/ 目录有旧版本归档但文件缺失  
**解决**: 在 ECS 上重新生成 sha256sums：
```bash
cd /home/computehub/ComputeHub/deploy
find . -type f \( -name 'computehub' -o -name 'computehub.exe' \) | sort | xargs sha256sum > sha256sums-1.3.46.txt
```

### Q4: Git push 被拒
**原因**: 远端有本地没有的 commit（多人协作或 ECS 直接改过）  
**解决**: `git push origin master --force`（单开发者场景安全）

### Q5: SSH 到 ECS 用 git 用户失败
**原因**: ECS 没有 `git` 用户，只有 `computehub` 用户  
**解决**: 用 `computehub` 用户 + `GIT_SSH_COMMAND` 环境变量

### Q6: Gallery 上传后远程节点不升级
**原因**: Worker 升级检查周期 30 分钟，或 version.txt 没更新  
**解决**: 确认 `deploy/version.txt` 版本号正确，或手动触发升级检查

### Q7: Windows 节点升级失败（银河计划特有）
**原因**: PowerShell 脚本编码问题、SYSTEM 账户路径、certutil 下载超时  
**解决**: 
- 使用 `PowerShell -EncodedCommand` 绕过 cmd 转义
- 确认 Worker 以 `admin` 账户运行（非 SYSTEM）
- 下载超时用 `Invoke-WebRequest -TimeoutSec 60`
- 参考 `memory/topics/技术经验/Windows_Agent修复经验总结.md`

### Q8: Windows 节点离线
**原因**: Gateway 重启后 Worker 断连、计划任务未自动启动  
**解决**: 
```bash
# 通过 ECS 检查 Windows 节点状态
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  curl -s http://127.0.0.1:8282/api/v1/nodes/list | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d.get(\"data\",[]):
    if n[\"status\"] != \"online\":
        print(f\"🔴 {n['node_id']} 离线\")
"
'
```

---

## 🔒 安全规则

1. **--force push 只用于单开发者场景** — 多人协作时用 merge
2. **SCP 前确认目标路径正确** — 别覆盖错文件
3. **重启前先 kill 旧进程** — 避免端口冲突
4. **Windows 节点升级前先备份** — 保留 `computehub.exe.bak`
5. **银河计划全集群验证** — 确保所有节点版本一致再收工

---

## 📊 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05-27 | 初始版本 |
| v1.5 | 2026-06-08 | 增加 Gallery 上传、Worker 升级流程 |
| v2.0 | 2026-06-15 | 标准化 7 步法、安全规则 |
| v3.0 | 2026-06-19 | 精简 5 步法 + 一键部署命令 + 实战踩坑记录 |
| **v4.0** | **2026-06-24** | **银河计划：全集群 8 节点统一部署 + Windows 节点升级 + 版本一致性验证** |

---

*文档位置: `web/COM-DEP-001_v4.0.md`*  
*最后更新: 2026-06-24 05:30 (端智)*
