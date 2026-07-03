# ComputeHub 工程深度分析 & 重构规划

> 审查日期: 2026-07-03
> 审查人: 小智
> 代码量: 50,870 行 Go / 110 文件 / 20 包

---

## 一、现状分析

### 1.1 架构总览

```
┌─────────────────────────────────────────────────────┐
│                  ComputeHub (单binary)                │
│                                                      │
│  computehub gateway ──── Gateway 服务 (:8282)        │
│  computehub worker  ──── Worker 节点                │
│  computehub tui     ──── 终端管理界面                 │
│                                                      │
│  模块依赖:                                           │
│    gateway (15K) → kernel, agent, scheduler, ...,    │
│    workercmd (10K) → agent, composer, kernel         │
│    agent (7K) → composer, kernel                     │
│    tuicmd (3.3K) → version                            │
│    visualizer (2.3K) → kernel, discover, health      │
│    kernel (2.3K) → scheduler                         │
│    scheduler (2.3K) → (独立)                          │
│    composer (1.8K) → (独立)                           │
└─────────────────────────────────────────────────────┘
```

### 1.2 优点

- ✅ **单 binary 部署** — `go build` 搞定所有平台
- ✅ **外部依赖极少** — 仅 gorilla/websocket + golang.org/x/term
- ✅ **功能完整** — 100+ API 端点，涵盖任务调度、AI Agent、Hall 聊天、Gallery 等
- ✅ **跨平台** — linux-amd64/arm64, windows-amd64, darwin-amd64/arm64
- ✅ **WS 实时通信** — 已实现 Ping/Pong, FanOut, PushTask
- ✅ **AI Agent 集成** — 三智/五智家族，跨节点协作
- ✅ **自升级机制** — Worker 自动检测升级

### 1.3 问题

| 类别 | 问题 | 严重度 |
|------|------|--------|
| 🔴 工程 | **deploy/ 目录 858MB，版本混乱** | P0 |
| 🔴 工程 | **config.json 30000+ 行，模型配置与系统配置混在一起** | P0 |
| 🔴 质量 | **gateway_ws.go 零测试** — 刚出过 P0 生产 bug | P0 |
| 🟡 质量 | **28 个测试文件，但 gateway 核心模块覆盖率低** | P1 |
| 🟡 质量 | **29 个 TODO/FIXME/BUG 标记散落代码中** | P1 |
| 🟡 工程 | **无版本发布流程** — 无 tag, 无 changelog, 无 release notes | P1 |
| 🟡 工程 | **bin/ 和 deploy/ 同时有 binary，路径混乱** | P1 |
| 🟡 工程 | **入口点 cmd/computehub 和 src/bin/ 重复** | P1 |
| 🟡 监控 | **无结构化日志** — 全 log.Printf, 无级别, 无追踪 | P1 |
| 🟢 运维 | **无健康检查端点** — Gateway 宕了只能靠心跳 | P2 |
| 🟢 监控 | **无性能指标** — goroutine 数, 内存, 请求延迟 | P2 |
| 🟢 前端 | **Web 界面仅 2 个 HTML 文件** — 功能有限 | P2 |

---

## 二、重构规划 (5 阶段)

### Phase 1: 工程整顿 (2-3天)

**目标**: 清理目录，建立发布流程，消除 P0 隐患

#### 1.1 目录整理

```
ComputeHub/
├── cmd/           ← 入口点 (保留)
│   ├── computehub/   ← 主入口 (main.go)
│   ├── gateway/      ← 已废弃？移入 src/
│   └── tui/          ← 已废弃？
├── src/           ← 核心源码 (保留)
│   ├── gateway/      ← 15K 行
│   ├── workercmd/    ← 10K 行
│   ├── agent/        ← 7K 行
│   └── ...
├── deploy/        
│   └── v1.3.52/      ← 每个版本独立目录，不混文件
│       ├── linux-amd64/computehub
│       ├── linux-arm64/computehub
│       ├── windows-amd64/computehub.exe
│       ├── darwin-amd64/computehub
│       └── darwin-arm64/computehub
├── scripts/       ← 保留 (但要清理)
│   └── deploy/       ← 部署脚本
├── docs/          ← 保留
├── web/           ← 保留
├── data/          ← 运行时数据
├── config/        ← 配置文件模板 (分开模型配置和系统配置)
│   ├── computehub.json  ← 系统配置
│   └── models.json      ← 模型配置 (可单独管理)
└── Makefile       ← 新增：统一构建入口
```

#### 1.2 清理清单

- [ ] 删除 `bin/` 目录（binary 统一在 deploy/ 下）
- [ ] 清理 `deploy/` 根目录的散落文件（只保留版本子目录）
- [ ] 清理 `src/bin/`（如果已废弃）
- [ ] 清理 `src/gateway/fix_delete.py``
- [ ] 删除 `C:openclaw-install`, `C:openclaw-installnode_modules`, `nul` 等垃圾文件
- [ ] 删除 `upgrade.sh`, `upgrade2.sh`, `upgrade3.sh` 等根目录脚本
- [ ] 删除 `dl_arm.py`, `patch_ai_page2.py`, `run_v1.3.17.sh` 等临时脚本

#### 1.3 发布流程

```
Makefile:
  make build        → 全平台编译, 输出到 deploy/v{VERSION}/
  make test         → go test ./...
  make release TAG=v1.4.0  → build + test + tag + deploy/
  make clean        → 清理 deploy/ 旧版本 (保留最近 3 个)
```

### Phase 2: 质量加固 (2-3天)

**目标**: 补测试，消 TODO，加日志

#### 2.1 关键模块测试

- [ ] `gateway_ws.go` — WS 连接管理，FanOut, writePump, 超时机
- [ ] `gateway/gateway.go` — 路由注册，事件处理
- [ ] `kernel/kernel.go` — 命令处理
- [ ] `scheduler/scheduler.go` — 任务调度
- [ ] 加入 CI：`go test ./...` 必须通过才能合并

#### 2.2 代码清理

- [ ] 遍历 29 个 TODO/FIXME/BUG，逐个解决或归档
- [ ] 统一错误处理模式（返回 error 而非 log.Printf）
- [ ] 分离 `config.json` 为系统配置 + 模型配置

#### 2.3 日志系统

```
现有: log.Printf("📡 WS Hub: %s 已连接", nodeID)
改进: logger.Info("ws_connected", "node", nodeID, "total", len(h.clients))
      logger.Error("ws_write_timeout", "node", nodeID, "error", err)
      logger.Warn("disk_high", "usage", diskUsage)
```

- 支持日志级别: DEBUG, INFO, WARN, ERROR
- 支持结构化字段
- 支持 JSON 输出（给日志聚合用）

### Phase 3: 监控与可观测性 (2天)

**目标**: 知道系统在干什么

#### 3.1 健康检查

- `GET /api/v1/health` → Gateway 自身健康状态
- `GET /api/v1/health/ws` → WS 连接池状态
- `GET /api/v1/health/tasks` → 任务队列状态

#### 3.2 指标采集

```json
GET /api/v1/metrics
{
  "goroutines": 44,
  "memory_mb": 64.3,
  "ws_connections": 5,
  "ws_disconnects_total": 2600,
  "tasks_pending": 0,
  "tasks_completed": 351,
  "tasks_failed": 9,
  "uptime_seconds": 36000
}
```

#### 3.3 TUI 增强

- 仪表板显示实时指标
- 告警推送（磁盘、内存、WS 断连率）
- 节点状态固化（不依赖 v2 API）

### Phase 4: 架构优化 (3-5天)

**目标**: 消除单点瓶颈，提升稳定性

#### 4.1 Gateway 高可用

- 当前: 单 Gateway, 单点故障
- 方案: Gateway 集群 + 共享状态 (hall_data.json, task_queue)
- 简化: 至少 Gateway 重启后自动恢复 Worker 连接

#### 4.2 WS 连接管理

- 当前: 30s ping / 60s read deadline / 10s write deadline
- 优化: 自适应 ping 间隔（根据网络延迟）
- 优化: 连接池化，减少重建开销

#### 4.3 任务调度

- 当前: 轮询 + WS 推送双模式
- 优化: WS 优先，HTTP 轮询仅作为兜底
- 优化: 任务优先级、超时、重试

### Phase 5: 前端与文档 (3-5天)

**目标**: 让用户能看懂、用好

#### 5.1 Web 管理界面

- 基于现有 `web/` 扩展
- 仪表板: 节点状态, 任务队列, 系统指标
- 任务管理: 提交, 查看, 取消
- 节点管理: 查看, 升级, 配置

#### 5.2 文档完善

- ARCHITECTURE.md 更新到最新
- API 文档（自动生成）
- 部署指南
- 开发指南

---

## 三、优先级路线图

```
Week 1 (7/3-7/10)
├── 🔴 Phase 1: 工程整顿
│   ├── 目录清理 (删垃圾, 规整 deploy/)
│   ├── config.json 拆分
│   └── Makefile + 发布流程
│
├── 🔴 Phase 2: 质量加固
│   ├── gateway_ws.go 测试
│   ├── 29 个 TODO 清理
│   └── 日志系统基础

Week 2 (7/11-7/17)
├── 🟡 Phase 2: 继续
│   └── 核心模块测试
│
├── 🟡 Phase 3: 监控
│   ├── /api/v1/health
│   ├── /api/v1/metrics
│   └── TUI 增强

Week 3 (7/18-7/24)
├── 🟢 Phase 4: 架构优化
│   ├── Gateway 重启恢复
│   └── WS 连接管理优化
│
├── 🟢 Phase 5: 前端
│   └── Web 管理界面 v1
```

---

## 四、立即行动项 (今天)

1. **清理垃圾文件** — 根目录: `C:openclaw-install`, `nul`, `upgrade*.sh`, `dl_arm.py` 等
2. **清理 deploy/ 根目录** — 只保留版本子目录
3. **删除旧版本** — 1.3.50, 1.3.51（保留 1.3.52）
4. **config.json 拆分** — 系统配置 100 行 + 模型配置独立文件

---

## 五、附录: 模块详细分析

| 模块 | 行数 | 测试文件 | 依赖 | 职责 |
|------|------|---------|------|------|
| gateway | 15,027 | 4 | 8 个内部包 | HTTP 路由, WS 管理, Hall, Gallery, 知识库 |
| workercmd | 10,140 | 3 | 5 个内部包 | Worker 主循环, Agent, 升级, WS 客户端 |
| agent | 7,177 | 3 | 2 个内部包 | AI Agent 引擎, 工具调用, 记忆系统 |
| tuicmd | 3,367 | 1 | 1 个内部包 | TUI 终端界面 |
| visualizer | 2,281 | 1 | 5 个内部包 | 全球算力地图, GPU 监控 |
| kernel | 2,350 | 2 | 1 个内部包 | 命令处理引擎, TriggerEngine |
| scheduler | 2,307 | 3 | 0 个内部包 | 任务队列, 调度, 断路器 |
| composer | 1,835 | 2 | 0 个内部包 | 任务分解, LLM 编排 |
| api | 1,309 | 2 | 0 个内部包 | 权限, 状态机 |
| monitor | 998 | 1 | 0 个内部包 | 节点监控, 指标 |
| health | 633 | 1 | 0 个内部包 | 健康检查 |
| discover | 528 | 1 | 0 个内部包 | 节点发现, 网络探测 |
| pure | 391 | 1 | 0 个内部包 | 流水线, 过滤 |
| gene | 337 | 1 | 0 个内部包 | 状态存储 |
| prometheus | 223 | 0 | 1 个内部包 | 指标暴露 |
| executor | 261 | 1 | 1 个内部包 | 命令执行, 沙箱 |
| executil | 68 | 0 | 0 个内部包 | 安全命令执行 |
| tuicmd | 3,367 | 1 | 1 个内部包 | TUI 界面 |
| gatewaycmd | 231 | 0 | 3 个内部包 | Gateway 启动入口 |
| version | 40 | 0 | 0 个内部包 | 版本信息 |