# COM-DEP-001: 编译部署标准流程 v3.0

**生效日期**: 2026-06-19  
**适用工程**: ComputeHub_new  
**维护者**: 端智  
**状态**: ✅ 已验证（v1.3.39 实战通过）

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

---

## 🎯 核心原则（精简版）

1. **版本号三统一**: git tag = version.go = deploy/version.txt
2. **Gateway 二进制不动 systemd** — 直接替换 deploy/computehub 后重启
3. **远程节点不 scp** — 通过 Gallery 自动升级
4. **ECS 远端仓库是唯一真相源** — 本地 push 后 ECS pull

---

## 📋 标准流程（5 步法，实测 48 秒）

### Step 0: 前置检查

```bash
cd /data/data/com.termux/files/home/ComputeHub_new

# 确认当前版本
cat deploy/version.txt
git tag -l | sort -V | tail -3

# 确认 git 状态干净
git status --short
```

### Step 1: 版本号 + Tag

```bash
# 1a. 改 version.go（从 "dev" → 目标版本）
# 文件: src/version/version.go
# 改: var VERSION = "dev" → var VERSION = "1.3.39"

# 1b. 打 tag
git tag v1.3.39

# 1c. 验证 tag 生效
bash scripts/get_version.sh   # 应输出 1.3.39
```

### Step 2: 编译

```bash
bash scripts/build_all.sh
# 产出: bin/{5 platforms}/computehub
# 验证: file bin/linux-arm64/computehub → ARM aarch64
```

### Step 3: 同步 deploy/ + Gallery

```bash
bash scripts/sync-deploy.sh
# 产出: deploy/1.3.39/ + deploy/{platform}/ + sha256sums
# 自动: Gallery 上传 3 个平台 binary 到 ECS Gateway
```

### Step 4: 部署到 ECS

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
  echo "1.3.39" > /home/computehub/ComputeHub/deploy/version.txt

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
  echo "=== Cluster ==="
  curl -s http://127.0.0.1:8282/api/v2/nodes | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d[\"nodes\"]:
    print(f\"  {n['id']:20s} v{n['version']:10s} {n['status']}\")
print(f\"  Total: {d['online_nodes']} online / {d['total_nodes']} nodes\")
"
'
```

### Step 5: 验证 + Git 提交

```bash
# 5a. 验证集群
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  curl -s http://127.0.0.1:8282/api/health
  echo ""
  curl -s http://127.0.0.1:8282/api/v1/nodes/list | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d.get(\"data\",[]):
    print(f\"  {n['node_id']:20s} {n['status']:10s} v{n['version']}\")
"
'

# 5b. 验证下载链路
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  curl -s --max-time 10 "http://127.0.0.1:8282/api/v1/download?file=computehub&platform=linux/arm64" -o /tmp/test-arm -w "%{size_download}B\n"
  file /tmp/test-arm
  rm -f /tmp/test-arm
'

# 5c. 验证升级检查
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 '
  curl -s "http://127.0.0.1:8282/api/v1/upgrade/check?current_version=1.3.25&platform=linux/arm64&node_id=worker-arm" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"update_available={d['data']['update_available']}, latest={d['data']['latest_version']}\")
"
'

# 5d. Git 提交 + 推送
git add -A
git commit -m "deploy: 发布 v1.3.39"
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_computehub -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
  git push origin master --force
```

---

## 🚀 一键部署（48 秒版）

```bash
# 完整流程：编译 → 同步 → SCP → 重启 → 验证 → 提交
# 前提: version.go 已改好 + git tag 已打

cd /data/data/com.termux/files/home/ComputeHub_new
VERSION=$(bash scripts/get_version.sh)

echo "=== 1/5 编译 ===" && bash scripts/build_all.sh && \
echo "=== 2/5 同步 ===" && bash scripts/sync-deploy.sh && \
echo "=== 3/5 SCP ===" && \
  scp -i ~/.ssh/id_ed25519_computehub -P 8022 deploy/computehub-linux-amd64 \
    computehub@36.250.122.43:/home/computehub/ComputeHub/deploy/computehub && \
echo "=== 4/5 重启 ===" && \
  ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43 "
    pkill -9 -f computehub 2>/dev/null; sleep 3; fuser -k 8282/tcp 2>/dev/null; fuser -k 8383/tcp 2>/dev/null; sleep 2;
    echo '${VERSION}' > /home/computehub/ComputeHub/deploy/version.txt;
    nohup /home/computehub/ComputeHub/deploy/computehub gateway --port 8282 > /tmp/gw.log 2>&1 & sleep 4;
    nohup /home/computehub/ComputeHub/deploy/computehub worker --agent --gw http://127.0.0.1:8282 --node-id ecs-p2ph --interval 3 --concurrent 8 --heartbeat 10 > /tmp/worker.log 2>&1 & sleep 6;
    echo 'GW:' && ss -tlnp | grep 8282;
    echo 'Worker:' && ss -tlnp | grep 8383;
    echo 'Ver:' && /home/computehub/ComputeHub/deploy/computehub --version;
  " && \
echo "=== 5/5 提交 ===" && \
  git add -A && git commit -m "deploy: 发布 v${VERSION}" && \
  GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_computehub -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    git push origin master --force && \
echo "🎉 v${VERSION} 部署完成"
```

---

## ⚠️ 常见问题（实战踩坑记录）

### Q1: version.go 还是 "dev"
**原因**: 源码中 `var VERSION = "dev"`，ldflags 注入只在构建时生效  
**解决**: 每次发版前手动改 version.go 为实际版本号

### Q2: ECS 上 version.txt 是 "dev"
**原因**: sync-deploy.sh 没同步到 ECS，或旧版遗留  
**解决**: 重启时手动 `echo "1.3.39" > deploy/version.txt`

### Q3: SHA256 校验失败
**原因**: ECS deploy/ 目录有旧版本归档（1.3.30-1.3.35）但文件缺失  
**解决**: 在 ECS 上重新生成 sha256sums：
```bash
cd /home/computehub/ComputeHub/deploy
find . -type f \( -name 'computehub' -o -name 'computehub.exe' \) | sort | xargs sha256sum > sha256sums-1.3.39.txt
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

---

## 🔒 安全规则

1. **--force push 只用于单开发者场景** — 多人协作时用 merge
2. **SCP 前确认目标路径正确** — 别覆盖错文件
3. **重启前先 kill 旧进程** — 避免端口冲突
4. **验证集群状态** — 确保所有节点在线再收工

---

## 📊 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05-27 | 初始版本 |
| v1.5 | 2026-06-08 | 增加 Gallery 上传、Worker 升级流程 |
| v2.0 | 2026-06-15 | 标准化 7 步法、安全规则 |
| **v3.0** | **2026-06-19** | **精简 5 步法 + 一键部署命令 + 实战踩坑记录** |

---

*文档位置: `web/COM-DEP-001_v3.0.md`*  
*最后更新: 2026-06-19 20:51 (端智)*
