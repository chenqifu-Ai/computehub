# 💻 ComputeHub 项目完整概述

> 生成: 2026-05-04 14:20  
> 位置: `/root/.openclaw/workspace/projects/computehub/`  
> 版本: v0.6.0 (Phase 1-4 核心完成)

---

## 一、项目定位

**ComputeHub = 确定性算力调度平台**  
为中小企业提供海外 GPU/CPU 算力一站式调度与计费服务。

**核心理念**: 物理交付 ≫ 认知描述  
**一句话**: 让算力出海像用电一样简单。

---

## 二、系统架构

```
Client → Gateway API (8282) 
  → Pure Pipeline (4级过滤) 
  → Kernel (确定性调度) 
  → Executor → 算力节点
         ↓
   Scheduler → 区域熔断器 + 健康检查
         ↓
   Composer → 任务编排 (拆解/并行/汇总)
         ↓
   Visualizer → REST + WebSocket 可视化
```

---

## 三、14个子包详解 (11,644行Go代码)

| # | 子包 | 行数 | 功能 | 阶段 |
|---|------|------|------|------|
| 1 | **gateway** | 1,060 | REST API, 端口8282, 12+端点, Dashboard服务 | P1 |
| 2 | **kernel** | 878 | 确定性调度内核, 单队列无竞态 | P1 |
| 3 | **scheduler** | 1,584 | 延迟感知调度+熔断器+优先级队列 | P2 |
| 4 | **visualizer** | 1,835 | 数据聚合+Web Bridge+Gateway桥接 | P2 |
| 5 | **monitor** | 998 | GPU监控+节点健康+指标采集 | P2 |
| 6 | **discover** | 527 | 广播/多播/手动节点发现 | P2 |
| 7 | **health** | 633 | TCP ping真实延迟测量 | P2 |
| 8 | **executor** | 259 | 命令执行+验证循环 | P1 |
| 9 | **pure** | 391 | 4级输入过滤(语法/语义/边界/上下文) | P1 |
| 10 | **gene** | 337 | 学习进化存储(出错→修复→永久记忆) | P1 |
| 11 | **composer** | 862 | 大模型拆解→并行分发→汇总 | P3 |
| 12 | **api** | 1,037 | 权限控制+状态机 | — |
| — | **bridge** | 73 | TUI←→Gateway 数据桥接 | P2 |

---

## 四、6大工程哲学

### 1. 绝对确定性
算力调度可预测、可回溯，消除竞态条件。
- 单队列内核 → 无竞态
- 状态机管理 → 状态可回溯
- 任务ID追踪 → 全链路可观测

### 2. 防御性鲁棒性
默认所有节点不可信，所有链路可能崩塌。
- 区域熔断器 → 故障隔离
- 健康检查 → 节点不可用时自动剔除
- 优雅降级 → 极端资源下保证内核生存

### 3. 物理真实优先
- GPU监控采集真实硬件数据
- 拒绝 Mock
- 计费基于真实GPU利用率

### 4. 多级纯化流水线
任务输入必经4层过滤：
```
语法过滤 → 语义过滤 → 边界过滤 → 上下文过滤
```

### 5. 环境解耦
- 能力协商 → 梯度可用性
- CGO_ENABLED=0 全静态编译
- 单二进制部署

### 6. 可回溯的进化架构
- 基因存储 (Gene Store)
- 一次出错，永久修复
- 出错→修复→基因化→永久记忆

---

## 五、代码组成

| 文件 | 路径 | 用途 |
|------|------|------|
| **Gateway入口** | `cmd/gateway/main.go` | REST服务主入口 |
| **TUI入口** | `cmd/tui/main.go` | 终端交互界面 |
| **Node入口** | `cmd/node/main.go` | 计算节点CLI |
| **Worker入口** | `cmd/worker/main.go` | Worker代理CLI |
| **main.go** | `main.go` | 原统一入口 |

### 二进制文件

| 文件 | 大小 | 用途 |
|------|------|------|
| `computehub-gateway` | 5.6MB | Gateway API服务 |
| `computehub-tui` | 8.1MB | 终端交互界面 |
| `compute-node` | 5.4MB | 节点管理CLI |
| `compute-worker` | 5.4MB | Worker代理 |

### 配置文件

| 文件 | 用途 |
|------|------|
| `config.json` | Gateway运行时配置 |
| `config.yaml` | 模型调度配置 |
| `genes.json` | 基因存储(错误记忆) |
| `go.mod` | Go模块依赖 |

### 部署文件

| 文件 | 用途 |
|------|------|
| `Dockerfile` | Gateway容器镜像 |
| `Dockerfile.tui` | TUI容器镜像 |
| `docker-compose.yml` | 一键部署编排 |
| `.dockerignore` | 构建过滤 |
| `deploy/nginx-dashboard.conf` | Nginx反代配置 |

### Web UI

| 文件 | 用途 |
|------|------|
| `code/dashboard/index.html` | 主监控面板(纯静态) |
| `code/compute_overseas_landing.html` | 海外算力落地页 |
| `code/token_compute_overseas.html` | Token经济页面 |

---

## 六、API端点

### 健康/状态
```
GET  /api/health      → 健康检查
GET  /api/status      → 系统状态(9模块全绿)
```

### 节点管理 (v1)
```
GET  /api/v1/nodes/list     → 节点列表
GET  /api/v1/nodes/:id      → 节点详情
POST /api/v1/nodes/register → 注册节点
POST /api/v1/nodes/unregister/:id → 注销节点
```

### 任务管理 (v1)
```
GET  /api/v1/tasks/list     → 任务列表
POST /api/v1/tasks/submit   → 提交任务
GET  /api/v1/tasks/:id      → 任务详情
POST /api/v1/tasks/:id/cancel → 取消任务
```

### 计费 (v1)
```
GET  /api/v1/billing/balance  → 查询余额
POST /api/v1/billing/charge   → 充值
POST /api/v1/billing/transfer → 转账
```

### 可视化 (v2)
```
GET  /api/v2/map/global       → 全球算力地图
GET  /api/v2/gpu/realtime     → GPU实时数据
GET  /api/v2/health           → 系统健康雷达图
WS   /ws/visual               → WebSocket实时推送(2s间隔)
```

---

## 七、测试状态

| 子包 | 状态 | 测试数 |
|------|------|--------|
| gateway | ✅ | 7项 |
| kernel | ✅ | ~15项 |
| scheduler | ✅ | ~18项 |
| pure | ✅ | 6项 |
| executor | ✅ | 4项 |
| discover | ✅ | 6项 |
| health | ✅ | 6项 |
| monitor | ✅ | 10项 |
| composer | ✅ | 8项 |
| visualizer | ✅ | ~18项 |
| gene | ✅ | 6项 |
| api | ✅ | 8项 |
| **总计** | **✅** | **~90+项** |

---

## 八、Docker部署

```bash
# 一键启动所有服务
docker compose up -d

# 服务访问
Gateway API + Dashboard → http://localhost:8282

# 启动TUI客户端
docker compose --profile tui run tui

# 管理命令
docker compose down            # 停止
docker compose up -d --build   # 重建并启动
```

---

## 九、Dashboard功能

| 模块 | 数据源 | 更新方式 |
|------|--------|----------|
| 🌍 全球算力地图 | GET /api/v2/map/global | 30s轮询 |
| 📊 GPU利用率分布 | GET /api/v2/gpu/realtime | REST+WS实时 |
| 📋 节点列表 | GET /api/v2/nodes | REST |
| 🔔 告警面板 | 嵌套在地图数据中 | REST |
| 📈 系统健康雷达图 | GET /api/v2/health | REST+WS实时 |
| 🔄 WebSocket推送 | WS /ws/visual | 2s间隔 |

---

## 十、技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Go | 1.24+ | 后端开发语言 |
| CGO_ENABLED=0 | — | 全静态编译 |
| Alpine | — | 容器基础镜像 |
| Docker | 24.0+ | 容器部署 |
| Docker Compose | v2+ | 编排部署 |
| HTML/CSS/JS | — | Dashboard前端 |

---

## 十一、项目结构

```
computehub/
├── cmd/          ← 4个入口(main.go)
│   ├── gateway/  ← Gateway API服务
│   ├── tui/      ← 终端交互界面
│   ├── node/     ← 节点管理CLI
│   └── worker/   ← Worker代理
├── src/          ← 14个子包(1.16万行)
│   ├── gateway/  ← REST API
│   ├── kernel/   ← 调度内核
│   ├── scheduler/← 调度器+队列+熔断
│   ├── visualizer/← 数据聚合+桥接
│   ├── monitor/  ← GPU监控
│   ├── discover/ ← 节点发现
│   ├── health/   ← 健康检查
│   ├── executor/ ← 执行器
│   ├── pure/     ← 输入过滤
│   ├── gene/     ← 基因存储
│   ├── composer/ ← 任务编排
│   └── api/      ← 权限+状态机
├── code/         ← Web资源
│   ├── dashboard/← 监控面板HTML
│   └── bin/      ← 编译好的二进制
├── deploy/       ← Nginx反代配置
├── docs/         ← 文档
├── scripts/      ← 启动脚本
├── tests/        ← 测试数据
├── _archive/     ← 备份文件
├── Dockerfile    ← 容器构建
├── README.md     ← 项目说明
├── SOUL.md       ← 工程哲学
├── config.json   ← 运行时配置
└── genes.json    ← 基因存储
```

---

## 十二、开发路线图

```
Phase 1 (P0)      Phase 2 (P1)      Phase 3 (P2)      Phase 4 (P3)
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ 核心增强 │  →   │ K8s集成   │  →   │ 弹性适配  │  →   │ 国产适配  │
│ 2周      │      │ 1月      │      │ 2月      │      │ 3月      │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
├─ Task优先级     ├─ GPU Operator   ├─ Karpenter      ├─ 昇腾CANN
├─ GPU监控        ├─ Kueue队列      ├─ 多云          ├─ 寒武纪
└─ Prometheus      └─ Prometheus     └─ AI框架集成     └─ 天数智芯
```

---

*项目完整状态: ✅ Phase1-4 核心代码完成 | ✅ ~90+测试用例全通 | ✅ 5.6MB+8.1MB 二进制就绪 | ✅ Docker部署就绪*
