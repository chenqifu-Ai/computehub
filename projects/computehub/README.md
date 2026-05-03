# ComputeHub - 确定性算力调度平台

**项目状态**: 🟢 Phase 1-4 核心代码完成 | Docker 部署就绪  
**创建日期**: 2026-04-22  
**最后更新**: 2026-05-03  
**负责人**: 小智  
**核心目标**: 基于确定性内核的海外算力调度平台

## 🚀 核心理念

**物理交付 ≫ 认知描述**

ComputeHub 是一个**物理确定性操作系统**，提供确定性的算力任务调度和系统状态管理。

## 📦 系统架构

```
Client → Gateway API (8282) → Pure Pipeline(4 级过滤) → Kernel → Executor → 算力节点
                                                         ↓
                                                   Scheduler → 区域熔断器 + 健康检查
                                                         ↓
                                                   Composer → 任务编排 (拆解/并行/汇总)
                                                         ↓
                                                   Visualizer → REST + WebSocket 可视化
```

### 核心组件 (14个子包)

| 组件 | 路径 | 功能 | 阶段 |
|------|------|------|------|
| **Gateway** | `src/gateway/` | REST API (端口 8282, 12 个端点) | P1 |
| **Kernel** | `src/kernel/` | 确定性命令调度器 (单队列无竞态) | P1 |
| **Executor** | `src/executor/` | 命令执行 + 验证循环 | P1 |
| **Pure Pipeline** | `src/pure/` | 4 级输入过滤 (语法/语义/边界/上下文) | P1 |
| **Gene Store** | `src/gene/` | 学习进化存储 (出错→修复→永久记忆) | P1 |
| **Scheduler** | `src/scheduler/` | 延迟感知调度 + 熔断器 + 优先级队列 | P2 |
| **Health** | `src/health/` | TCP ping 真实延迟测量 | P2 |
| **Discover** | `src/discover/` | 广播/多播/手动节点发现 | P2 |
| **Monitor** | `src/monitor/` | GPU 监控模拟 | P2 |
| **Composer** | `src/composer/` | 大模型拆解→并行分发→汇总 | P3 |
| **Visualizer** | `src/visualizer/` | 全球算力地图 + GPU 看板 + WS 推送 | P4 |
| **API** | `src/api/` | 权限控制 + 状态机 | - |

## 🐳 Docker 部署 (推荐)

### 前置条件

- Docker 24.0+
- Docker Compose v2+

### 快速启动

```bash
cd projects/computehub

# 构建并启动所有服务
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f gateway
```

### 服务访问

| 服务 | 地址 | 说明 |
|------|------|------|
| Gateway API | http://localhost:8282 | REST API |
| Dashboard | http://localhost:8080 | 可视化面板 |
| TUI 客户端 | `docker compose --profile tui run tui` | 交互式终端 |

### API 测试

```bash
# 健康检查
curl http://localhost:8282/api/health

# 系统状态
curl http://localhost:8282/api/status

# 节点列表
curl http://localhost:8282/api/v1/nodes/list

# 可视化地图
curl http://localhost:8282/api/v2/map/global
```

### 管理命令

```bash
# 停止
docker compose down

# 重启
docker compose restart gateway

# 仅启动 gateway（不含 dashboard）
docker compose up -d gateway

# 重新构建
docker compose build --no-cache gateway

# 一键重建并启动
docker compose up -d --build
```

## 🛠️ 手动构建 (Go)

### 前置条件
- Go 1.24+
- Linux/macOS/Windows

```bash
cd projects/computehub

# 编译 gateway
CGO_ENABLED=0 go build -o computehub-gateway ./cmd/gateway/

# 编译 TUI
CGO_ENABLED=0 go build -o computehub-tui ./cmd/tui/

# 运行
./computehub-gateway
```

### 运行测试

```bash
# 全量测试
CGO_ENABLED=0 go test ./...

# 单包测试
go test ./src/scheduler/
go test ./src/kernel/
```

## 📊 测试状态

- **所有 12 个子包** ✅ 全部通过
- **约 90+ 测试用例** ✅
- **编译** ✅ `CGO_ENABLED=0` 静态编译

## 📁 项目结构

```
computehub/
├── Dockerfile             ← Gateway 镜像
├── Dockerfile.tui         ← TUI 镜像
├── docker-compose.yml     ← 一键部署
├── .dockerignore          ← 构建忽略
├── README.md              ← 你在这
├── SOUL.md                ← 工程哲学
├── config.json            ← 配置文件
├── genes.json             ← 基因存储
├── go.mod / go.sum        ← Go 依赖
├── cmd/
│   ├── gateway/main.go    ← Gateway 入口
│   └── tui/main.go        ← TUI 入口
├── src/                   ← 14 个子包 (见上表)
│   ├── gateway/
│   ├── kernel/
│   ├── executor/
│   ├── pure/
│   ├── gene/
│   ├── scheduler/
│   ├── health/
│   ├── discover/
│   ├── monitor/
│   ├── composer/
│   ├── visualizer/
│   ├── api/
│   ├── blockchain/        ← (待实现)
│   └── metrics/           ← (待实现)
├── deploy/
│   └── nginx-dashboard.conf  ← Dashboard 反代配置
├── code/
│   ├── compute_overseas_landing.html  ← 落地页
│   └── token_compute_overseas.html    ← Token 页面
├── docs/                  ← 文档
├── scripts/               ← 管理脚本
└── tests/                 ← 测试资源
```

## 🎯 工程哲学

详见 [SOUL.md](SOUL.md)

### 核心原则
1. **绝对确定性** - 消除竞态，状态可回溯
2. **防御性鲁棒性** - 默认不可信，内置自救
3. **物理真实优先** - 拒绝 Mock，真实硬件数据
4. **多级纯化** - 4 层输入过滤
5. **进化架构** - 错误→基因→永久修复

## 📈 下一步

- [ ] Docker 部署实测 (需要 docker 环境)
- [ ] GitHub CI/CD 推送 (需要新 PAT)
- [ ] 真实 GPU 节点接入验证
- [ ] 区块链集成 (src/blockchain/)
- [ ] Prometheus 指标采集 (src/metrics/)

---

*最后更新: 2026-05-03*  
*版本: v0.3 Alpha (Docker 就绪)*
