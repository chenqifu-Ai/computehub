# 📦 ComputeHub 编译部署标准流程

## 架构

```
build/          → 编译产物（git tracked）
deploy/         → 部署产物（git tracked）
  └── {version}/  → 版本归档
  └── {platform}/ → 当前平台目录
  └── sha256sums.txt → 校验和

/usr/local/bin/computehub → Gateway 实际运行路径（systemd）
```

## 核心规则

### 1. 目录职责

| 目录 | 用途 | Git |
|------|------|-----|
| `bin/` | 编译产物（中间目录） | ✅ tracked |
| `deploy/` | 部署产物（含版本归档） | ✅ tracked |
| `deploy/{version}/` | 每个版本的完整归档 | ✅ tracked |
| `deploy/{platform}/` | 当前各平台 binary | ✅ tracked |
| `deploy/computehub` | Gateway 运行用的 binary | ✅ tracked |
| `deploy/sha256sums.txt` | 当前 SHA256 校验和 | ✅ tracked |
| `deploy/sha256sums-{version}.txt` | 各版本校验和 | ✅ tracked |
| `deploy/version.txt` | 当前版本号 | ✅ tracked |
| `deploy/*.bak*` | 旧版本备份 | ❌ 不 tracked |
| `deploy/gateway.*` | 日志 | ❌ 不 tracked |

### 2. systemd 服务

```
ExecStart=/usr/local/bin/computehub gateway --port 8282
```

Gateway 从 `/usr/local/bin/computehub` 启动。
**不要改 systemd 指向 deploy/ 下的文件**（会导致文件被占用无法覆盖）。

### 3. Gateway 提供下载的 API 路径

Gateway 从 `findDeployDir()` 找 deploy/ 目录下的文件，通过 `/api/v1/download?file={name}&platform={os/arch}` 提供给 Worker 下载。

---

## 流程

### Step 1: 编译

```bash
cd /home/computehub/ComputeHub
bash scripts/build_all.sh
```

产出：`bin/{platform}/computehub{.exe}`

验证：
```bash
file bin/linux-amd64/computehub    # 应该 x86-64
file bin/linux-arm64/computehub    # 应该 ARM aarch64
file bin/windows-amd64/computehub.exe  # 应该 PE32+ Windows
./bin/linux-amd64/computehub version  # 应该显示 vX.Y.Z
```

### Step 2: 同步到 deploy/

```bash
bash scripts/sync-deploy.sh
```

产出：
- `deploy/{version}/{platform}/computehub{.exe}`
- `deploy/{platform}/computehub{.exe}`
- `deploy/sha256sums.txt`
- `deploy/sha256sums-{version}.txt`

### Step 3: 更新 Gateway 运行二进制

```bash
cp bin/linux-amd64/computehub /usr/local/bin/computehub
chmod +x /usr/local/bin/computehub
```

⚠️ 不要修改 systemd 配置！

### Step 4: 重启 Gateway

```bash
systemctl restart computehub-gateway
sleep 3
systemctl status computehub-gateway
```

### Step 5: 验证

```bash
# Gateway 健康检查
curl -s http://localhost:8282/api/health

# 下载链路验证（各平台）
curl -s "http://localhost:8282/api/v1/download?file=computehub&platform=linux/arm64" -o /tmp/test.arm -w "%{size_download}B\n" && file /tmp/test.arm
curl -s "http://localhost:8282/api/v1/download?file=computehub.exe&platform=windows/amd64" -o /tmp/test.win -w "%{size_download}B\n" && file /tmp/test.win

# 升级检查
curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=1.3.25&platform=linux/arm64&node_id=worker-arm" | python3 -m json.tool

# 集群状态
curl -s http://localhost:8282/api/v2/nodes | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'{n[\"id\"]:20s} v{n[\"version\"]:10s} {n[\"status\"]}') for n in d['nodes']]"
```

### Step 6: 上传 Gallery（供远程节点下载）

```bash
bash scripts/sync-deploy.sh  # 已经包含 Gallery 上传（Step 6）
```

如果单独执行：
```bash
curl -s -X POST "http://localhost:8282/api/v1/gallery/delete?name=computehub-linux-arm64" > /dev/null
curl -s -F "file=@bin/linux-arm64/computehub;filename=computehub-linux-arm64" "http://localhost:8282/api/v1/gallery/upload"
```

### Step 7: 推送远程节点（如需）

```bash
# 仅推送 Worker binary（不停 Gateway）
bash scripts/sync-deploy.sh push 183.251.21.92 --action worker --key ~/.ssh/id_ed25519_computehub --gateway http://36.250.122.43:8282

# 全节点推送+重启
bash scripts/sync-deploy.sh push 183.251.21.92 --action restart-all --key ~/.ssh/id_ed25519_computehub --gateway http://36.250.122.43:8282
```

---

## 常见问题

### Q: sync-deploy.sh 卡住 "Text file busy"
**A**: Gateway 正在运行 deploy/computehub。先重启 Gateway：
```bash
systemctl restart computehub-gateway
sleep 3
bash scripts/sync-deploy.sh
```

### Q: 编译出来的版本不对
**A**: 检查 git tag：
```bash
git describe --tags --abbrev=0   # 应该返回最新版 tag
git tag -l | sort -V | tail -5
```

### Q: Worker 不自动升级
**A**: 
1. 确认 Gateway 升级检查接口正常：
   ```bash
   curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=1.3.25&platform=linux/arm64&node_id=worker-arm"
   ```
2. 确认 Worker 日志有升级相关输出（`[Upgrade]` 开头）
3. 确认 Worker 策略是 `auto`（默认）
4. 确认 Worker 没有正在运行的任务（有任务会阻止升级）

### Q: arm64 节点收到 x86-64 二进制
**A**: 检查 `deploy/linux-arm64/computehub` 的架构：
```bash
file deploy/linux-arm64/computehub  # 必须是 ARM aarch64
```

---

## 快速一键部署

```bash
cd /home/computehub/ComputeHub
bash scripts/build_all.sh && bash scripts/sync-deploy.sh
```

这会自动完成：编译 → 同步 deploy → 上传 Gallery。
Gateway 运行二进制需手动复制到 `/usr/local/bin/computehub`。
