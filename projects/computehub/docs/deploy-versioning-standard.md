# 部署版本号控制规范

## 问题
deploy 目录下的二进制没有带版本号，旧二进制无法清理，也无法追踪升级记录。

## 规范

### 目录结构
```
deploy/
├── version.txt              # 当前版本号（如 0.7.4），每版只改这行
├── compute-worker-linux-amd64-0.7.4
├── compute-worker-linux-arm64-0.7.4
├── compute-worker-win-amd64.exe-0.7.4
├── compute-worker-win-arm64.exe-0.7.4
├── computehub-gateway-0.7.4
├── sha256sums-0.7.4.txt     # 当前版本的 SHA256 校验和
└── CHANGELOG.md             # 版本变更日志
```

### 版本命名规则
- 格式: `主.次.修订` (semver 最小集)
- 示例: `0.7.4`, `0.7.5`, `0.8.0`
- 文件名 = 原文件名 + `-` + 版本号
  - ✅ `compute-worker-linux-arm64-0.7.4`
  - ❌ `compute-worker-linux-arm64`（旧规范，废弃）

### 编译到部署流程
```bash
# 1. 确认版本号（go build -ldflags）
VERSION="0.7.4"

# 2. 编译
cd /root/.openclaw/workspace/projects/computehub
go build -ldflags="-X main.Version=${VERSION}" -o build/compute-worker-linux-arm64 -v ./cmd/worker/

# 3. 复制到 deploy（带版本号）
cp build/compute-worker-linux-arm64 deploy/compute-worker-linux-arm64-${VERSION}

# 4. 生成校验和
cd deploy && sha256sum compute-worker-linux-arm64-${VERSION} > sha256sums-${VERSION}.txt

# 5. 更新全局 version.txt
echo "${VERSION}" > version.txt

# 6. 清理旧版本（可选，保留最近 2 版）
find deploy -name '*-0.7.3' -type f -delete
```

### Worker 升级协议
Worker 通过 Gateway 静态文件服务下载：
```
http://<gateway-host>:8282/compute-worker-linux-arm64-${VERSION}
```

Gateway 配置中 deploy 目录需通过静态文件服务暴露。

### CHANGELOG.md 格式
```
## 0.7.4 (2026-05-10)
### 新增
- ARM64 Worker 支持
### 修复
- Worker 自动升级死循环
- Stdout pipe 冲突

## 0.7.3 (2026-05-09)
### 修复
- findDeployDir symlink 修复
```
