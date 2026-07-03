# Knowledge: ComputeHub 架构经验库 — 源码目录/API路由/组件关系
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 架构, ComputeHub, 源码结构, API路由, Gateway
> Timestamp: 2026-07-02T12:22:16+08:00

## Content

## 源码目录结构
computehub/
├── cmd/              # 入口: gateway/worker/node/tui
├── src/              # 核心包
│   ├── gateway/      → API路由、节点/任务管理、文件下载
│   ├── kernel/       → 任务调度、状态机、节点管理
│   ├── executor/     → 命令执行器
│   ├── composer/     → LLM任务分解
│   ├── scheduler/    → 任务调度算法
│   ├── pure/         → 过滤管道
│   ├── gene/         → 基因存储器（学习优化）
│   ├── discover/     → 节点发现
│   ├── health/       → 健康检查
│   ├── monitor/      → 监控
│   ├── prometheus/   → 指标收集
│   ├── visualizer/   → 全球算力地图 + v2 API
│   └── version/      → 版本号管理
├── deploy/           # 部署二进制
├── scripts/          # 工具脚本
└── config.json       # Gateway配置

## Gateway 核心组件
OpcGateway {
    Kernel — 任务调度 + 节点管理 + 状态机
    Pipeline — 请求过滤管道（语法/语义/边界过滤）
    Executor — 本地命令执行器
    GeneStore — 学习/优化记忆
    Composer — LLM任务分解器
    TaskDispatcher — 从kernel队列拿任务→本地Runner执行
    Metrics — Prometheus指标
    Scheduler — 任务调度算法
}

## API路由（v1）
POST /api/dispatch — 遗留调度
GET /api/health — 健康检查
GET /api/status — 系统状态
POST /api/v1/task — 创建任务
GET /api/v1/task/:id — 查询任务
GET /api/v1/tasks — 任务列表
POST /api/v1/node/register — 节点注册
GET /api/v1/nodes — 节点列表
GET /api/v1/files/:id — Gallery文件下载
POST /api/v1/knowledge/put — 知识写入
GET /api/v1/knowledge/query — 知识查询
GET /api/v1/knowledge/stats — 知识统计

## 完整文档
memory/topics/技术经验/computehub-架构经验库.md
