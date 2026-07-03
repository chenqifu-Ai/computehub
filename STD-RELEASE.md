# STD-RELEASE — ComputeHub 发布标准流程 v1.0

## 🎯 核心理念

**发布不是琐事，是一次不可逆的操作。** 走标准流程是为了让每次发布可预期、可复现、可回滚。

---

## 0. 坐标系

```
    手机 (termux)                        ECS (生产)
  ┌─────────────────┐                ┌─────────────────────┐
  │ OPC/             │               │ ~/computehub        │ ← Gateway binary
  │   cmd/           │    ssh/scp    │ ~/ComputeHub/deploy/│ ← deploy 仓库
  │   src/           │ ───────────→  │ ~/deploy/           │ ← deploy 平铺
  │   deploy/        │               │ systemd:            │
  │   scripts/       │               │   computehub-gateway│
  └─────────────────┘               │   computehub-worker │
                                     └─────────────────────┘
```

**关键事实**:
- 手机 arm64 交叉编译（不能直接跑 amd64 binary）
- systemd 的 `ExecStart` 指向 `~/computehub`（不是 deploy 目录）
- Worker 和 Gateway 共用同一个 binary

---

## 1. 发布前检查清单

### □ 代码就绪
```
git status                           # 确认修改范围
git add -A && git commit -m "..."    # 提交
git push origin master               # 推送到 ECS
```

### □ Git tag 同步
```bash
git tag v<版本>                       # 打 tag
git push origin v<版本>               # 推 tag
git describe --tags --abbrev=0       # 确认 tag 生效
```

> ⚠️ `build_all.sh` 和 `deploy.sh build` 都从 git tag 读版本号，**
> **不打 tag 编译出来显示 "1.3.2" 或 "dev"，上线后升级检测会认为无更新。**

### □ SSH 连通性
```bash
ssh -p 8022 -i ~/.ssh/id_ed25519_computehub computehub@36.250.122.43 "echo ok"
```

### □ Gateway 路径确认
```bash
ssh <ecs> "systemctl cat computehub-gateway | grep ExecStart"
# 返回: ExecStart=/home/computehub/computehub gateway
# 目标路径: ~/computehub
```

### □ deploy 路径统一（ECS 上）
```bash
# 确认三个地方指向同一个版本:
ls -la ~/computehub ~/deploy/computehub ~/ComputeHub/deploy/computehub
```

---

## 2. 编译（手机 termux）

```bash
cd /data/data/com.termux/files/home/OPC

# 方式 A: 全平台编译（推荐，一次搞定）
bash scripts/build_all.sh
# 输出: bin/{platform}/computehub(,exe)

# 方式 B: 特定平台 + 版本指定
VERSION="1.3.3"
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
  -ldflags="-s -w -X github.com/computehub/opc/src/version.VERSION=${VERSION}" \
  -o bin/linux-amd64/computehub ./cmd/computehub/

# 验证版本号
bin/linux-amd64/computehub version
# → 必须显示 "ComputeHub v1.3.3"
```

**编译产物**:
| 文件 | 用途 |
|------|------|
| `bin/linux-amd64/computehub` | ECS Gateway + Worker (x86_64) |
| `bin/linux-arm64/computehub` | 备用 arm64 节点 |
| `bin/windows-amd64/computehub.exe` | Windows Worker |
| `bin/darwin-*/computehub` | macOS 开发用 |

---

## 3. 同步到 deploy/ 目录

```bash
# 复制 bin/ → deploy/ + 生成 sha256sums + 写 version.txt
bash scripts/sync-deploy.sh

# 验证
cat deploy/version.txt          # → 1.3.3
ls -la deploy/computehub        # → 最新 binary
head -3 deploy/sha256sums-1.3.3.txt
```

---

## 4. 推送到 ECS

### 4.1 上传 binary
```bash
# 方案 A: deploy.sh（推荐）
VERSION="1.3.3"
ssh -p 8022 -i ~/.ssh/id_ed25519_computehub computehub@36.250.122.43 \
  "sudo systemctl stop computehub-gateway computehub-worker 2>/dev/null; sleep 2"
scp -P 8022 -i ~/.ssh/id_ed25519_computehub \
  deploy/computehub \
  computehub@36.250.122.43:~/computehub

# 方案 B: stdin pipe（当 scp 因 Text file busy 失败时使用）
cat deploy/computehub | ssh -p 8022 -i ~/.ssh/id_ed25519_computehub \
  computehub@36.250.122.43 \
  "cat > /home/computehub/computehub"
```

> ⚠️ binary 如正在被 systemd 使用，scp 会报 `Text file busy`。
> **必须先 stop 再传。** 所以 4.1 第一步停服务是必须的。

### 4.2 验证上传
```bash
ssh -p 8022 -i ~/.ssh/id_ed25519_computehub computehub@36.250.122.43 \
  "chmod +x ~/computehub && ~/computehub version"
# → ComputeHub v1.3.3  ✅
```

### 4.3 更新 deploy 目录（可选，供升级通道用）
```bash
scp -P 8022 -i ~/.ssh/id_ed25519_computehub \
  deploy/computehub \
  deploy/sha256sums-1.3.3.txt \
  deploy/version.txt \
  computehub@36.250.122.43:/home/computehub/ComputeHub/deploy/

# 同步到 ~/deploy/（如果存在）
ssh ecs "cp /home/computehub/ComputeHub/deploy/computehub /home/computehub/deploy/computehub"
```

> `~/deploy/` 和 `ComputeHub/deploy/` 必须一致，
> Worker 升级管理器从 version.txt 检查版本，**两处不一致会导致版本检测混乱**。

### 4.4 启动服务
```bash
ssh -p 8022 -i ~/.ssh/id_ed25519_computehub computehub@36.250.122.43 \
  "sudo systemctl start computehub-gateway && sleep 3 && sudo systemctl start computehub-worker"
```

---

## 5. 验证上线

```bash
# 5.1 Gateway 健康检查
curl -s http://36.250.122.43:8282/api/health
# → {"success":true,"data":"ComputeHub System Healthy"}

# 5.2 进程确认
ssh ecs "pgrep -a computehub"
# → /home/computehub/computehub gateway
# → /home/computehub/computehub worker --gw http://localhost:8282 ...

# 5.3 升级通道
curl -s "http://36.250.122.43:8282/api/v1/upgrade/check?current_version=1.3.2"
# → update_available: true, latest_version: "1.3.3"

# 5.4 Worker 注册确认
# 本地:
curl -s http://36.250.122.43:8282/api/v1/nodes 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
    [print(f'  {n.get(\"node_id\",\"?\")}: v{n.get(\"version\",\"?\")}') for n in d.get('data',[])]"
```

---

## 6. Git 提交

```bash
git add -A
git status
git commit -m "v<版本>: <描述>

- 变更说明
- 主要改动"
git push origin master
```

---

## 7. 回滚流程

```bash
# 条件: 新版本不可用，需恢复旧版
# 前提: deploy/ 目录下有上一个版本备份

VERSION="1.3.2"              # 目标回滚版本
TAG="v1.3.2"

# 7.1 切回旧版本代码
git checkout $TAG
bash scripts/build_all.sh

# 7.2 推送旧版本到 ECS
ssh ecs "sudo systemctl stop computehub-gateway computehub-worker"
cat bin/linux-amd64/computehub | ssh ecs "cat > /home/computehub/computehub"
ssh ecs "chmod +x ~/computehub && ~/computehub version"

# 7.3 恢复 deploy/ 版本号
echo "$VERSION" | ssh ecs "cat > /home/computehub/ComputeHub/deploy/version.txt"
ssh ecs "cp /home/computehub/ComputeHub/deploy/computehub /home/computehub/deploy/computehub"

# 7.4 重启
ssh ecs "sudo systemctl start computehub-gateway && sleep 3 && sudo systemctl start computehub-worker"

# 7.5 回切 master
git checkout master
```

---

## 8. 常见错误及处理

| 症状 | 根因 | 处理 |
|------|------|------|
| `Text file busy` | binary 被 systemd 锁定 | ⚡ 先 `systemctl stop` 再传 |
| `Exec format error` | binary 架构不匹配（arm64 vs amd64） | 检查 `remote_arch`，用正确平台编译 |
| `version` 显示 dev | 没打 tag 或 ldflags 没传 | `git tag vX.Y.Z && git push origin vX.Y.Z` 重新编译 |
| 升级检测不到新版本 | deploy/version.txt 没更新 | `echo "1.3.3" > deploy/version.txt` |
| Worker 没自动启动 | systemd 停用 | `sudo systemctl enable --now computehub-worker` |
| scp 连接中断 | ECS 内存不足或网络抖动 | 改用 `cat | ssh` 管道 |
| `unable to resolve host ecs-p2ph` | /etc/hosts 缺域名（无害） | 忽略，sudo 会报但不影响执行 |

---

## 9. 完整流程速查（一行一条）

```bash
# 1. 提交代码
git add -A && git commit -m "v1.3.3: xxx" && git push origin master

# 2. 打 tag
git tag v1.3.3 && git push origin v1.3.3

# 3. 编译
bash scripts/build_all.sh

# 4. 同步
bash scripts/sync-deploy.sh

# 5. 推送 (STOP → SCP → START 三步)
ssh ecs "sudo systemctl stop computehub-gateway computehub-worker"
scp -P 8022 deploy/computehub ecs:~/computehub
ssh ecs "sudo systemctl start computehub-gateway && sleep 3 && sudo systemctl start computehub-worker"

# 6. 验证
ssh ecs "~/computehub version"
curl http://36.250.122.43:8282/api/health
```

---

*STD-RELEASE v1.0 — 2026-06-02*
*所有发布遵循此标准，踩坑记入常见错误表。*