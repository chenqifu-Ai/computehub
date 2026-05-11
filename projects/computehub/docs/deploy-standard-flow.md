# ComputeHub 编译与部署标准流程

> 版本: 2026-05-10
> 适用范围: compute-worker / computehub-gateway

---

## 核心原则

**upgrade 链路硬编码了无后缀文件名**，deploy 目录中的二进制**不能加版本号后缀**，否则 Worker 自升级会 404。

- `build/` 里带版本号（方便回滚/比较）
- `deploy/` 里无后缀（升级链路需要）
- `version.txt` 是唯一的版本信息来源
- 升级前必须归档旧版到 `archive/`

---

## 目录结构

```
computehub/
├── build/                          # 编译输出（带版本号后缀）
│   ├── compute-worker-linux-arm64-0.7.5
│   ├── compute-worker-linux-amd64-0.7.5
│   └── ...
├── deploy/                         # 部署目录（无后缀，供升级链路读取）
│   ├── version.txt                 # 当前版本号（升级链路唯一读取）
│   ├── compute-worker-linux-arm64
│   ├── compute-worker-linux-amd64
│   ├── compute-worker-win-amd64.exe
│   ├── compute-worker-win-arm64.exe
│   ├── computehub-gateway
│   ├── VERSIONS.md                 # 版本记录（SHA256 + 部署时间）
│   ├── sha256-current.txt          # 当前版本校验和
│   └── archive/                    # 旧版本归档（保留最近 3 版）
│       ├── 0.7.3/
│       └── 0.7.1/
└── ...
```

---

## 编译与部署流程

### Step 0: 准备工作

```bash
cd /root/.openclaw/workspace/projects/computehub

# 确认 Go 环境
go version

# 拉取最新代码（如有远程仓库）
# git pull origin master
```

### Step 1: 确认新版本号

```bash
# 读当前版本号
cat deploy/version.txt
# 输出: 0.7.4

# 确定新版本（semver: 主.次.修订）
NEW_VERSION="0.7.5"
OLD_VERSION="0.7.4"
```

### Step 2: 编译所有平台

```bash
cd /root/.openclaw/workspace/projects/computehub
mkdir -p build

# 清理旧 build
rm -f build/compute-worker-* build/computehub-*

# 编译 Worker - Linux ARM64（主力）
go build -ldflags="-X main.Version=${NEW_VERSION}" \
  -o build/compute-worker-linux-arm64-${NEW_VERSION} \
  ./cmd/worker/ 2>&1

# 编译 Worker - Linux AMD64
GOOS=linux GOARCH=amd64 go build -ldflags="-X main.Version=${NEW_VERSION}" \
  -o build/compute-worker-linux-amd64-${NEW_VERSION} \
  ./cmd/worker/ 2>&1

# 编译 Worker - Windows AMD64
GOOS=windows GOARCH=amd64 go build -ldflags="-X main.Version=${NEW_VERSION}" \
  -o build/compute-worker-win-amd64.exe-${NEW_VERSION} \
  ./cmd/worker/ 2>&1

# 编译 Worker - Windows ARM64
GOOS=windows GOARCH=arm64 go build -ldflags="-X main.Version=${NEW_VERSION}" \
  -o build/compute-worker-win-arm64.exe-${NEW_VERSION} \
  ./cmd/worker/ 2>&1

# 编译 Gateway - Linux ARM64
go build -ldflags="-X main.Version=${NEW_VERSION}" \
  -o build/computehub-gateway-${NEW_VERSION} \
  ./cmd/gateway/ 2>&1

# 编译 TUI - Linux ARM64
go build -ldflags="-X main.Version=${NEW_VERSION}" \
  -o build/computehub-tui-${NEW_VERSION} \
  ./cmd/tui/ 2>&1
```

### Step 3: 验证编译产物

```bash
# 检查所有产物
ls -la build/

# 验证二进制可执行
./build/compute-worker-linux-arm64-${NEW_VERSION} -v
./build/computehub-gateway-${NEW_VERSION} -v
./build/computehub-tui-${NEW_VERSION} -v

# 检查版本信息
./build/compute-worker-linux-arm64-${NEW_VERSION} -v | grep -i version
```

### Step 4: 部署到 deploy 目录

```bash
cd /root/.openclaw/workspace/projects/computehub

# 备份旧二进制（如果版本不同）
if [ "$(cat deploy/version.txt 2>/dev/null)" != "${NEW_VERSION}" ]; then

  # 创建归档目录
  mkdir -p "deploy/archive/${OLD_VERSION}"

  # 归档旧二进制（如果存在）
  if [ -f "deploy/compute-worker-linux-arm64" ]; then
    cp deploy/compute-worker-linux-arm64 "deploy/archive/${OLD_VERSION}/"
  fi
  if [ -f "deploy/compute-worker-linux-amd64" ]; then
    cp deploy/compute-worker-linux-amd64 "deploy/archive/${OLD_VERSION}/"
  fi
  if [ -f "deploy/compute-worker-win-amd64.exe" ]; then
    cp deploy/compute-worker-win-amd64.exe "deploy/archive/${OLD_VERSION}/"
  fi
  if [ -f "deploy/compute-worker-win-arm64.exe" ]; then
    cp deploy/compute-worker-win-arm64.exe "deploy/archive/${OLD_VERSION}/"
  fi
  if [ -f "deploy/computehub-gateway" ]; then
    cp deploy/computehub-gateway "deploy/archive/${OLD_VERSION}/"
  fi

  echo "✅ 旧版本 ${OLD_VERSION} 已归档到 deploy/archive/${OLD_VERSION}/"
fi

# 复制新二进制到 deploy（覆盖同名无后缀文件）
cp build/compute-worker-linux-arm64-${NEW_VERSION} deploy/compute-worker-linux-arm64
cp build/compute-worker-linux-amd64-${NEW_VERSION} deploy/compute-worker-linux-amd64
cp build/compute-worker-win-amd64.exe-${NEW_VERSION} deploy/compute-worker-win-amd64.exe
cp build/compute-worker-win-arm64.exe-${NEW_VERSION} deploy/compute-worker-win-arm64.exe
cp build/computehub-gateway-${NEW_VERSION} deploy/computehub-gateway

# 设置可执行权限
chmod +x deploy/compute-worker-linux-arm64
chmod +x deploy/compute-worker-linux-amd64
chmod +x deploy/computehub-gateway

echo "✅ 二进制已部署到 deploy/"
```

### Step 5: 更新版本号

```bash
echo "${NEW_VERSION}" > deploy/version.txt
echo "✅ version.txt 已更新: $(cat deploy/version.txt)"
```

### Step 6: 生成校验和

```bash
cd deploy
sha256sum compute-worker-linux-arm64 \
    compute-worker-linux-amd64 \
    compute-worker-win-amd64.exe \
    compute-worker-win-arm64.exe \
    computehub-gateway > sha256-current.txt

echo "✅ SHA256 已生成"
cat sha256-current.txt
```

### Step 7: 更新 VERSIONS.md

```bash
cd deploy

# 追加新版本记录
cat >> VERSIONS.md << EOF

## ${NEW_VERSION} ($(date +%Y-%m-%d))
- SHA256 (arm64): \$(sha256sum compute-worker-linux-arm64 | awk '{print \$1}')
- SHA256 (amd64): \$(sha256sum compute-worker-linux-amd64 | awk '{print \$1}')
EOF

echo "✅ VERSIONS.md 已更新"
tail -5 VERSIONS.md
```

### Step 8: 清理旧归档（保留最近 3 版）

```bash
cd deploy/archive

# 列出所有归档版本
ls -1 | sort -V

# 如果超过 3 个版本，删除最旧的
COUNT=$(ls -1 | wc -l)
if [ "$COUNT" -gt 3 ]; then
  REMOVE=$(ls -1 | sort -V | head -1)
  echo "⚠️  清理旧归档: ${REMOVE}"
  rm -rf "${REMOVE}"
else
  echo "✅ 归档版本数: ${COUNT}/3"
fi
```

### Step 9: 重启 Gateway（如需）

```bash
# 停止旧 Gateway
pkill -f "computehub-gateway" 2>&1 || true

# 启动新 Gateway
cd /root/.openclaw/workspace/projects/computehub
nohup ./deploy/computehub-gateway --config config/config.json > gateway.log 2>&1 &
echo "🚀 Gateway 已启动 PID: $!"

# 等待启动
sleep 3
curl -s http://localhost:8282/api/v2/health | head -5
```

### Step 10: 验证升级链路

```bash
# 测试 Worker 升级检查 API
curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=0.7.3&platform=linux/arm64" | python3 -m json.tool 2>/dev/null || \
curl -s "http://localhost:8282/api/v1/upgrade/check?current_version=0.7.3&platform=linux/arm64"

# 测试下载 API（确认无 404）
curl -s "http://localhost:8282/api/v1/download?file=compute-worker-linux-arm64" -o /dev/null -w "HTTP %{http_code}, Size: %{size_download} bytes\n"
```

---

## 快速脚本

把以上流程封装成一个脚本 `scripts/deploy.sh`：

```bash
#!/bin/bash
# ComputeHub 编译与部署脚本
# 用法: bash scripts/deploy.sh 0.7.5
set -e

cd /root/.openclaw/workspace/projects/computehub

NEW_VERSION="${1:?用法: bash scripts/deploy.sh <版本号>}"
OLD_VERSION=$(cat deploy/version.txt 2>/dev/null || echo "none")

echo "🔨 编译 ${NEW_VERSION}..."
echo "📦 旧版本: ${OLD_VERSION}"
echo "🚀 新版本: ${NEW_VERSION}"

# ... 自动执行上述所有步骤 ...

echo "✅ 部署完成!"
```

---

## 回滚流程

```bash
cd /root/.openclaw/workspace/projects/computehub

# 从 archive 恢复
VERSION_TO_RESTORE="0.7.4"
cp "deploy/archive/${VERSION_TO_RESTORE}/compute-worker-linux-arm64" deploy/compute-worker-linux-arm64
cp "deploy/archive/${VERSION_TO_RESTORE}/compute-worker-linux-amd64" deploy/compute-worker-linux-amd64
chmod +x deploy/compute-worker-linux-arm64 deploy/compute-worker-linux-amd64

# 更新版本号
echo "${VERSION_TO_RESTORE}" > deploy/version.txt

# 重启 Gateway
pkill -f "computehub-gateway" 2>&1 || true
cd deploy && ./computehub-gateway --config ../config/config.json &

echo "✅ 已回滚到 ${VERSION_TO_RESTORE}"
```

---

## 注意事项

1. **deploy 文件名绝对不能加后缀** — 升级链路硬编码 `compute-worker-linux-arm64`
2. **version.txt 是黄金标准** — Worker 只读这个判断是否有新版本
3. **编译前确认架构** — ARM64 用 `compute-worker-linux-arm64`，交叉编译用 `GOOS/GOARCH`
4. **归档优先于删除** — 旧二进制移到 archive/ 而不是 rm
5. **部署前先验证二进制** — `./build/xxx -v` 确认可执行
6. **Gateway 重启后验证 API** — `/api/v1/upgrade/check` 和 `/api/v1/download`

---

## 常见问题

### Q: Worker 升级失败，下载 404
**A:** 检查 deploy 目录下是否有 `compute-worker-linux-arm64`（无后缀）。如果加了版本号后缀就会 404。

### Q: 如何确认版本是否正确？
**A:** `cat deploy/version.txt` 和 `sha256sum deploy/compute-worker-linux-arm64` 对比 VERSIONS.md。

### Q: 交叉编译报错？
**A:** 确保安装了对应平台的 GCC 或 CGO_ENABLED=0。
