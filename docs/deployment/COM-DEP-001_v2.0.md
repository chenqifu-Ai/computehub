# COM-DEP-001: 编译部署标准流程 v2.0

**生效日期**: 2026-06-15  
**适用工程**: ComputeHub_new  
**维护者**: 端智（小智）  
**状态**: ✅ 已验证

---

## 📌 架构概览

```
ComputeHub_new/
├── bin/              → 编译产物（中间目录，git tracked）
│   ├── linux-amd64/
│   ├── linux-arm64/
│   ├── darwin-amd64/
│   ├── darwin-arm64/
│   └── windows-amd64/
├── web/              → 前端页面（新增 v2.0）
│   └── ai.html       → AI 对话页面
├── deploy/           → 部署产物（git tracked）
│   ├── {version}/    → 版本归档（如 1.3.30/）
│   ├── {platform}/   → 当前平台 binary
│   ├── sha256sums.txt
│   └── version.txt
├── src/              → 源代码
├── scripts/          → 工具脚本
└── README.md
```

---

## 🎯 核心原则

1. **编译产物进 git** — 每次编译可追溯
2. **版本归档进 git** — 每版 deploy/{version}/ 完整保留
3. **Gateway 二进制不动** — `/usr/local/bin/computehub` 独立于 deploy/
4. **前端页面独立** — `web/` 目录，改 HTML 不碰 Go 代码
5. **远程节点通过 Gallery 下载** — 不 scp 二进制

---

## 📋 标准流程（7 步法）

### Step 1: 版本管理

```bash
cd /data/data/com.termux/files/home/ComputeHub_new

# 查看当前版本
cat deploy/version.txt

# 查看 git 状态
git status
git log --oneline -3

# 如果有新代码，提交
git add -A
git commit -m "feat: 描述变更"
git push origin master
```

### Step 2: 编译

```bash
# 方式 A: 全平台交叉编译
cd /data/data/com.termux/files/home/ComputeHub_new
bash scripts/build_all.sh

# 方式 B: 单平台编译（测试用）
cd /data/data/com.termux/files/home/ComputeHub_new
GOOS=linux GOARCH=amd64 go build -o bin/linux-amd64/computehub ./cmd/computehub
```

**验证编译产物**:
```bash
file bin/linux-amd64/computehub      # x86-64 ELF
file bin/linux-arm64/computehub      # ARM aarch64 ELF
file bin/windows-amd64/computehub.exe # PE32+ Windows
./bin/linux-arm64/computehub version  # 显示 vX.Y.Z
```

### Step 3: 同步到 deploy/

```bash
cd /data/data/com.termux/files/home/ComputeHub_new
bash scripts/sync-deploy.sh
```

**产出**:
- `deploy/{version}/` — 版本归档（含所有平台 binary）
- `deploy/{platform}/` — 当前平台 binary
- `deploy/sha256sums-{version}.txt` — 版本校验和
- `deploy/sha256sums.txt` — 当前校验和
- Gallery 自动上传（供远程节点下载）

### Step 4: 更新 Gateway 运行二进制

```bash
# ⚠️ 注意: 这是本地机器，不是 systemd 的 ECS
cp bin/linux-arm64/computehub computehub
chmod +x computehub

# 验证
./computehub version
```

**注意**: 如果是 systemd 机器（ECS），不要改 systemd 指向！
```bash
# systemd 机器
cp bin/linux-amd64/computehub /usr/local/bin/computehub
systemctl restart computehub-gateway
```

### Step 5: 重启 Gateway

```bash
# 本地模式（Android/ Termux）
pkill -f computehub
sleep 2
./computehub gateway --port 8282

# 或 systemd 模式
systemctl restart computehub-gateway
systemctl status computehub-gateway
```

### Step 6: 验证部署

```bash
# 健康检查
curl -s http://localhost:8282/api/health

# AI 页面访问
curl -s http://localhost:8282/ai | head -5

# 节点列表
curl -s http://localhost:8282/api/v1/nodes/list

# 下载链路
curl -s "http://localhost:8282/api/v1/download?file=computehub&platform=linux/arm64" -o /tmp/test.arm
file /tmp/test.arm

# 升级检查
curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=1.3.30&platform=linux/arm64&node_id=localhost"
```

### Step 7: 提交更新

```bash
cd /data/data/com.termux/files/home/ComputeHub_new
git add -A
git commit -m "deploy: 发布 v$(cat deploy/version.txt)"
git push origin master
```

---

## 🛠️ 工具脚本

### `scripts/build_all.sh` — 全平台交叉编译
```bash
# 产出: bin/{platform}/computehub{.exe}
```

### `scripts/sync-deploy.sh` — 同步 deploy/ + 上传 Gallery
```bash
# 产出: deploy/{version}/, deploy/{platform}/, sha256sums
```

### `scripts/build-deploy.sh` — 编译 + 同步一键执行
```bash
# 等价于: build_all.sh && sync-deploy.sh
```

### `scripts/bump_version.py` — 版本号递增
```bash
# 从 1.3.30 递增到 1.3.31
```

---

## ⚠️ 常见问题

### Q1: Gateway 下载 "Text file busy"
**原因**: Gateway 正在运行 `deploy/computehub`，文件被占用  
**解决**:
```bash
systemctl restart computehub-gateway
sleep 3
bash scripts/sync-deploy.sh
```

### Q2: 版本不对
**原因**: deploy/version.txt 未更新或 git tag 不一致  
**解决**:
```bash
cat deploy/version.txt
git describe --tags --abbrev=0
git tag -l | sort -V | tail -5
```

### Q3: Worker 不自动升级
**排查**:
1. Gateway 升级接口正常:
   ```bash
   curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=1.3.30&platform=linux/arm64&node_id=worker-arm"
   ```
2. Worker 日志有 `[Upgrade]` 输出
3. Worker 策略 `auto`（默认）
4. Worker 没有正在运行的任务

### Q4: arm64 节点收到 x86-64 二进制
**原因**: `deploy/linux-arm64/computehub` 架构不对  
**解决**:
```bash
file deploy/linux-arm64/computehub  # 必须是 ARM aarch64
```

### Q5: 前端页面不生效
**原因**: 改的是内联字符串，不是 `web/ai.html`  
**解决**: 修改 `web/ai.html`，然后重新编译

---

## 🔒 安全规则

1. **永远不 scp 二进制到 Gateway** — 通过 Gallery 下载
2. **永远不改 systemd 指向** — `/usr/local/bin/computehub` 独立管理
3. **永远不改 deploy/ 下正在被 Gateway 打开的文件** — 先重启 Gateway
4. **永远不跳过 sha256 校验** — 每个版本必须有 checksum

---

## 📊 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05-27 | 初始版本 |
| v1.5 | 2026-06-08 | 增加 Gallery 上传、Worker 升级流程 |
| v2.0 | 2026-06-15 | **新增** web/ 前端管理、标准化 7 步法、安全规则 |

---

*文档位置: `web/COM-DEP-001_v2.0.md`*  
*最后更新: 2026-06-15 06:30 (端智)*
