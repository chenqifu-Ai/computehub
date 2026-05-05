# ComputeHub 构建规范 (2026-05-04 制定)

## 🐛 背景

**问题**: `go build` 默认启用 cgo，但在本环境（Termux/PRoot）下 cgo/net 编译失败：
```
cannot use _Ctype_socklen_t(len(b)) (value of uint32 type) as _Ctype_size_t value
```

**修复**: 添加 `CGO_ENABLED=0` 跳过 cgo，编译成功。

**教训**: 这不是第一次出现了，必须有规范。

---

## 规范 MCP-BUILD-001: ComputeHub 构建

### 1️⃣ 构建时必须加 CGO_ENABLED=0

```bash
# ✅ 正确
CGO_ENABLED=0 go build -o output cmd/xxx/main.go

# ❌ 错误（本环境会失败）
go build -o output cmd/xxx/main.go
```

### 2️⃣ 一键构建部署脚本

```bash
# 构建所有组件（gateway + tui + worker）
cd /root/.openclaw/workspace/projects/computehub

CGO_ENABLED=0 go build -o code/bin/computehub-gateway cmd/gateway/main.go
CGO_ENABLED=0 go build -o code/bin/computehub-tui cmd/tui/main.go
CGO_ENABLED=0 go build -o code/bin/computehub-worker cmd/worker/main.go
```

### 3️⃣ 版本号修改三部曲

1. **改源文件**: `cmd/tui/main.go` 的 `const version = "x.y.z"`
2. **重新编译**: `CGO_ENABLED=0 go build ...`
3. **重启服务**: 停旧进程 → 启动新进程

**❌ 只改源文件不编译重启 → 不生效**

### 4️⃣ 验证编译产物版本

```bash
strings code/bin/computehub-tui | grep '^[0-9]\+\.[0-9]\+\.[0-9]\+$'
```

### 5️⃣ 一键部署脚本

**位置**: `scripts/build-computehub.sh`

功能：编译 + 替换二进制 + 重启服务
