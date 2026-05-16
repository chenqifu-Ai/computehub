# ComputeHub 命令参数规范 v0.7.9

> 统一管理 ComputeHub 三合一二进制 (`computehub`) 的所有启动方式、配置参数和运行时开关。
> 适用入口: `./cmd/computehub/`（所有子命令合并到一个二进制）

---

## 1. 二进制入口

`computehub` 是一个 **三合一单二进制**（All-in-One），所有功能通过**子命令**区分。

```bash
computehub gateway [--port N]          # 启动 Gateway 服务（核心）
computehub worker  [--flags...]        # 启动 Worker 节点代理
computehub tui     [--gw URL]          # 启动 TUI 终端管理
computehub version                     # 显示版本号
computehub help                        # 显示帮助
```

别名:
| 子命令 | 别名 |
|--------|------|
| `gateway` | `gw`, `g` |
| `worker`  | `w` |
| `version` | `--version`, `-v` |
| `help`    | `--help`, `-h` |

---

## 2. GATEWAY 子命令

`computehub gateway` — 启动核心服务（含 Gallery、Visualizer、Dashboard）

### 2.1 CLI 标志

| 标志 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--port N` | int | `8282` | 覆盖 config.json 中的端口配置 |

### 2.2 配置加载顺序

1. 查找 `./config.json`（当前目录）
2. 查找 `~/config.json`（用户目录）
3. 若都不存在，自动创建 `~/config.json` 并写入默认值
4. CLI `--port` 标志覆盖 config 中的 `gateway.port`

### 2.3 config.json 完整结构

```jsonc
{
  "gateway": {
    "port": 8282,              // Gateway 监听端口
    "max_connections": 100     // 最大连接数
  },
  "kernel": {
    "buffer_size": 100,        // 任务缓冲区大小
    "max_states": 1000         // 最大状态跟踪数
  },
  "executor": {
    "sandbox_path": "/tmp/computehub-sandbox"  // 沙箱路径
  },
  "gene_store": {
    "path": "./genes.json"     // 基因库存储路径
  },
  "visualizer": {
    "enabled": true,            // 启用/禁用 Visualizer
    "simulate": false,          // 模拟数据模式（无真实节点时测试用）
    "port": 8282               // Visualizer 端口（与 gateway port 相同）
  },
  "composer": {
    "api_url": "",              // TaskComposer API 地址（空=禁用）
    "api_key": "",              // API Key
    "model": "",                // 模型名称
    "execute_models": [],       // 执行模型列表（数组）
    "max_concurrency": 8,       // 最大并发数
    "timeout_seconds": 120      // 超时秒数
  },
  "gallery": {
    "root_dir": "~/gallery"     // 作品广场存储目录（支持 ~/ 相对路径）
  }
}
```

### 2.4 各功能模块注册

Gateway 启动后自动注册以下功能和 API 端点：

| 模块 | 条件 | 端点 |
|------|------|------|
| **Gallery**（作品广场） | 始终注册 | `/api/v1/gallery`（HTML/JSON）、`/gallery`、`/api/v1/gallery/upload`、`/api/v1/gallery/delete`、`/api/v1/files/*` |
| **Visualizer**（可视化） | `visualizer.enabled = true` | `/api/v2/*`、`/ws/visual`（WebSocket） |
| **Dashboard**（仪表盘） | 始终注册 | `./code/dashboard` 静态文件 |
| **Video**（视频管线） | 始终注册 | `/api/v1/video/*` |
| **Download**（下载） | 始终注册 | `/api/v1/download` |
| **Upgrade**（升级） | 始终注册 | `/api/v1/upgrade/*` |
| **Prometheus**（指标） | 始终注册 | `/metrics` |
| **Composer**（任务分解） | `composer.api_url` 非空 | 自动启用，否则报 ⚠️ 警告 |

### 2.5 Gateway 启动日志对照

```
[2026-05-16 20:22:07] ✅ Config file loaded: config.json
[2026-05-16 20:22:07] ✅ Prometheus metrics collector started
[2026-05-16 20:22:07] ✅ Gateway initialized, ready to serve
[2026-05-16 20:22:07] ✅ Task dispatcher started
[2026-05-16 20:22:07] ✅ Scheduler initialized with 0 real nodes
[2026-05-16 20:22:07] ✅ Heartbeat monitor started
[2026-05-16 20:22:07] 🌐 Visualizer v2 API registered         ← visualizer.enabled=true
[2026-05-16 20:22:07] 🎬 Gallery registered                    ← 始终有
[2026-05-16 20:22:07] 📂 Dashboard static files                ← 始终有
[2026-05-16 20:22:07] 🎬 Video endpoints registered            ← 始终有
[2026-05-16 20:22:07] 📦 Download endpoint registered          ← 始终有
[2026-05-16 20:22:07] 🔄 Upgrade endpoints registered          ← 始终有
[2026-05-16 20:22:07] [Kernel] Processing Command gw-xxx       ← 心跳处理
```

---

## 3. WORKER 子命令

`computehub worker` — 启动 Worker 节点代理，注册到 Gateway 并执行任务

### 3.1 CLI 标志

| 标志 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--gw` / `--gateway` | string | `http://localhost:8282` | Gateway 地址 |
| `--node-id` / `--id` | string | `worker-<hostname>` | 节点唯一标识 |
| `--ip` / `--address` | string | 自动检测 | 手动指定节点 IP |
| `--gpu-type` / `--gpu` | string | 自动检测或 `CPU` | GPU 型号 |
| `--region` | string | `cn-east` | 区域 |
| `--interval` / `--poll` | int (秒) | `5` | 任务轮询间隔 |
| `--heartbeat` | int (秒) | `25` | 心跳上报间隔 |
| `--concurrent` | int | `4` | 最大并发执行任务数 |
| `--help` / `-h` | — | — | 显示帮助 |

### 3.2 Worker 工作原理

```
1. 注册:  POST /api/v1/nodes/register  (节点 ID / GPU / Region / CPU / 内存)
2. 心跳:  POST /api/v1/nodes/heartbeat  (GPU 利用率 / 温度 / 显存 / CPU 负载)
3. 轮询:  POST /api/v1/tasks/poll       (获取待执行任务)
4. 执行:  本地运行命令，超时自动杀死
5. 流式:  POST /api/v1/tasks/progress   (增量输出推送，500ms 间隔)
6. 结果:  POST /api/v1/tasks/result     (最终结果 + exit code)
7. 注销:  POST /api/v1/nodes/unregister (优雅退出)
```

### 3.3 默认值自动检测

- `--node-id`: 空则 `worker-<hostname>`
- `--cpu-cores`: 空则 `runtime.NumCPU()`
- `--memory-gb`: 空则自动检测（系统内存）
- `--gpu-type`: 空则尝试 `nvidia-smi` 检测，失败则设为 `CPU`
- `--ip`: 空则通过 UDP 连接 8.8.8.8:80 获取出口 IP

---

## 4. TUI 子命令

`computehub tui` — 启动交互式终端管理界面

### 4.1 CLI 标志

| 标志 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--gw` | string | `http://localhost:8282` | 连接的 Gateway 地址 |

### 4.2 TUI 各功能界面

| 快捷键 | 命令 | 功能 |
|--------|------|------|
| `d` | `dashboard` / `d` | 📊 系统仪表板（KPI 卡片、GPU分布、活跃节点Top10、🔥最热GPU Top5） |
| `n` | `nodes` | 🔌 节点浏览器（按区域/状态/GPU类型过滤，支持添加/删除/详情） |
| `g` | `gpu` / `gpumon` | 🎮 GPU 实时监控（按型号聚合 + 🔥高温GPU追踪） |
| `r` | `map` / `regions` | 🌍 全球算力地图（9区域状态/健康度） |
| `t` | `tasks` | 📋 任务管理器（按优先级查看/提交/取消/实时输出监控） |
| `a` | `alerts` | 🔔 告警面板（severity/type 过滤） |
| `h` | `history` | 📈 历史趋势（5项指标火花图） |
| `health` | `health` / `chk` | 🏥 系统健康检查 |
| `shell` | `shell` | 💻 OPC-Shell（Legacy 命令模式） |
| `?` | `help` / `?` | 📖 帮助 |

### 4.3 TUI 节点浏览器特殊命令

| 输入 | 功能 |
|------|------|
| `<node-id>` | 查看节点详情（支持前缀匹配） |
| `d <node-id>` | 删除指定节点 |
| `a` / `add` | 新增节点（交互式填写） |

### 4.4 TUI 任务管理器命令

| 输入 | 功能 |
|------|------|
| `submit <node_id> <cmd>` | 提交任务到指定节点（可追加 `l` 进入实时输出监控） |
| `cancel <task_id>` | 取消指定任务 |
| `list` / `r` | 刷新任务列表 |
| `back` / `q` | 返回 |

---

## 5. 编译开关

`build_all.sh` 编译脚本参数：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `CGO_ENABLED=0` | 禁用 CGO（静态链接） | `0`（必须） |
| `GOOS` | 目标操作系统 | `linux`, `darwin`, `windows` |
| `GOARCH` | 目标架构 | `amd64`, `arm64` |
| `-ldflags` | 注入构建标识 | `-X github.com/computehub/opc/src/version.BUILD=$(date +%s)` |

支持的编译目标：
- `linux-amd64`
- `linux-arm64`
- `darwin-amd64`
- `darwin-arm64`
- `windows-amd64`

输出目录：`bin/{platform}/computehub`

---

## 6. 版本号管理

定义在 `src/version/version.go`：

| 字段 | 值 | 说明 |
|------|----|------|
| `VERSION` | `"0.7.9"` | 语义化版本，修改规则：fix→+0.0.1, feature→+0.1.0, major→+1.0.0 |
| `BUILD` | `"dev"` 或 Unix 时间戳 | ldflags 注入，`go build -ldflags="-X ..."` |

---

## 7. 运行时 API 端点总表

### 7.1 Gateway 核心 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/status` | GET | 系统状态 |
| `/metrics` | GET | Prometheus 指标 |

### 7.2 节点管理

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/nodes/register` | POST | 节点注册 |
| `/api/v1/nodes/unregister` | POST | 节点注销 |
| `/api/v1/nodes/heartbeat` | POST | 心跳上报 |

### 7.3 任务管理

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/tasks/submit` | POST | 提交任务 |
| `/api/v1/tasks/poll` | POST | Worker 轮询任务 |
| `/api/v1/tasks/progress` | GET/POST | 查看/推送进度 |
| `/api/v1/tasks/result` | POST | 回传结果 |
| `/api/v1/tasks/cancel` | POST | 取消任务 |
| `/api/v1/tasks/list` | GET | 任务列表 |

### 7.4 V2 可视化 API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v2/health` | GET | 健康（含可视化元数据） |
| `/api/v2/nodes` | GET | 节点列表（含GPU雷达） |
| `/api/v2/map/global` | GET | 全球算力地图 |
| `/api/v2/gpu/realtime` | GET | GPU 实时状态 |
| `/api/v2/alerts` | GET | 告警列表 |
| `/api/v2/history` | GET | 历史趋势 |
| `/ws/visual` | WebSocket | 实时可视化 WebSocket |

### 7.5 Gallery 作品广场

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/gallery` | GET | 作品广场页面（HTML/JSON） |
| `/api/v1/gallery?format=json` | GET | JSON 接口 |
| `/api/v1/gallery/upload` | POST | 文件上传 (multipart/form-data) |
| `/api/v1/gallery/delete` | POST | 文件删除 |
| `/gallery` | GET | 简洁页面入口 |
| `/api/v1/files/*` | GET | 作品文件下载/预览 |

### 7.6 其他

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/video/*` | — | 视频生产管线 |
| `/api/v1/download` | GET | 二进制下载 |
| `/api/v1/upgrade/*` | — | 自动升级 |
| `/` | GET | 默认页面（Gallery 入口） |
| `./code/dashboard` | 静态文件 | Dashboard 前端 |

---

## 8. 常见问题排查

### 8.1 Gallery 缺失

**症状**: 启动日志无 `🎬 Gallery registered:` 行
**原因**: 编译入口错误，只编译了 `./cmd/gateway/` 而非 `./cmd/computehub/`
**解决**: 
```bash
# ✅ 正确（三合一）
CGO_ENABLED=0 go build -o computehub ./cmd/computehub/

# ❌ 错误（仅 gateway，无 Gallery/TUI）
CGO_ENABLED=0 go build -o computehub ./cmd/gateway/
```

### 8.2 Config 不生效

**症状**: 启动日志显示 `⚠️ Composer not configured` 但 config 中已填写
**原因**: config.json 不在加载路径或格式错误
**解决**: 确保 config.json 在当前目录或 `~/config.json`

### 8.3 版本号不匹配

**症状**: 启动显示 `v0.7.9` 但无 Gallery
**原因**: 版本号是编译时 `-ldflags` 手动注入的，但代码不完整
**解决**: 从完整源码重新编译（`src/version/version.go` 为权威来源）

### 8.4 交叉编译 cgo 错误

**症状**: `gcc_amd64.S:27:8: error: unknown token in expression`
**原因**: ARM64 机器交叉编译 x86_64 时 CGO 启用导致
**解决**: 始终 `CGO_ENABLED=0`（静态链接，无 cgo 依赖）

---

> 版本：v0.7.9 | 更新日期：2026-05-16
