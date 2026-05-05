# ComputeHub 开发路线图 v1.0

> 制定日期: 2026-05-04  
> 制定者: 小智  
> 类型: 开发规划文档  
> 目的: 为后续开发提供可执行的路线图参考

---

## 目录

1. [项目概述](#1-项目概述)
2. [生态位分析](#2-生态位分析)
3. [核心定位](#3-核心定位)
4. [架构演进路线](#4-架构演进路线)
5. [分阶段开发计划](#5-分阶段开发计划)
6. [技术选型决策](#6-技术选型决策)
7. [集成规范](#7-集成规范)
8. [风险与应对](#8-风险与应对)
9. [里程碑检查点](#9-里程碑检查点)

---

## 1. 项目概述

### 1.1 项目背景

ComputeHub 是一个轻量级 GPU 集群管理与调度平台，旨在为中小企业和边缘计算场景提供低成本、易部署的 GPU 资源池化解决方案。

### 1.2 当前状态

```
┌──────────────────────────────────────┐
│  已完成功能                           │
│  ┌────────────────────────────────┐  │
│  │ TUI Dashboard (v0.6.0)         │  │
│  │ Gateway (Go 网关)              │  │
│  │ Worker Agent (Go)              │  │
│  │ Bridge (Go)                    │  │
│  │ 节点管理 (register/list/delete) │  │
│  │ Task 队列 (基础)                │  │
│  │ 基础监控                        │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### 1.3 项目目标

- **短期**: 补齐核心功能（优先级队列、细粒度监控、告警系统）
- **中期**: K8s 集成（GPU Operator + Kueue + Prometheus）
- **长期**: 多云/弹性 + 国产化适配（昇腾/寒武纪）

---

## 2. 生态位分析

### 2.1 竞品对比矩阵

| 功能维度 | Run:ai (PWM) | Kueue | Volcano | GPU Operator | ComputeHub |
|----------|-------------|-------|---------|-------------|------------|
| GPU 节点管理 | ✅ | ❌ | ❌ | ❌ | ✅ |
| Task 队列 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 优先级调度 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 抢占机制 | ✅ | ✅ | ✅ | ❌ | ❌ |
| GPU-Share 时间片 | ✅ | ❌ | ❌ | ❌ | ❌ |
| MIG 动态分区 | ✅ | ❌ | ❌ | ✅ | ❌ |
| 拓扑感知调度 | ✅ | ❌ | ✅ | ❌ | ❌ |
| 弹性伸缩 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 多租户隔离 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 成本核算 | ✅ | ❌ | ❌ | ❌ | ✅ |
| Dashboard | ✅ Web | ❌ | ❌ | ❌ | ✅ TUI |
| 多云支持 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 国产化适配 | ❌ | ❌ | ❌ | ❌ | ❌ |

### 2.2 竞争定位

```
                    复杂度
                     ↑
          高         │  Run:ai/PWM
                     │  (企业级，$7亿)
          中         │  Kueue/Volcano
                     │  (K8s 生态)
                     │
          低  ───────┼─────────────────→ 价格
                     │  ComputeHub ← 我们
                     │  (轻量级，免费/低成本)
```

### 2.3 差异化优势

| 优势 | 说明 |
|------|------|
| ✅ 轻量易部署 | 单二进制，无需 K8s |
| ✅ 成本极低 | 开源免费 |
| ✅ 中文本地化 | 原生中文支持 |
| ✅ 灵活定制 | Go 语言，代码结构清晰 |
| ✅ TUI 交互 | 终端友好，适合运维场景 |

---

## 3. 核心定位

### 3.1 一句话定位

**ComputeHub = 轻量级 GPU 集群调度器 + 成本核算系统**

### 3.2 核心能力

```
ComputeHub 核心 = GPU 调度 + 成本核算

GPU 调度:
├─ 节点管理 (注册/注销/监控)
├─ 任务调度 (队列/优先级/抢占)
└─ GPU 池化 (硬切分 → 未来软切分)

成本核算:
├─ GPU 使用时间统计
├─ 按量计费
└─ 成本分析报告
```

### 3.3 不做的事

| 不做 | 原因 | 替代方案 |
|------|------|---------|
| AI 训练框架 | 不是 AI 框架 | 集成 PyTorch/TensorFlow |
| ML 流水线编排 | 不是 MLOps 平台 | 集成 Airflow/Kubeflow |
| 模型推理服务 | 不是推理服务 | 集成 KServe/Ray Serve |
| 容器运行时 | 不是 K8s | 集成 K8s/GPU Operator |
| 监控采集 | 可集成标准方案 | 集成 Prometheus |

---

## 4. 架构演进路线

### 4.1 阶段 1: 当前架构（已完成）

```
┌────────────────────────────────────────────┐
│  TUI Dashboard (终端界面)                   │
│  ┌──────────────────────────────────────┐  │
│  │ 节点管理 | Task 管理 | 监控 | 成本    │  │
│  └──────────────────────────────────────┘  │
├────────────────────────────────────────────┤
│  Gateway (Go 网关)                         │
│  ├─ 节点注册/注销                           │
│  ├─ Task 提交/查询                          │
│  └─ 监控数据聚合                            │
├────────────────────────────────────────────┤
│  Bridge (Go)                                │
│  └─ 连接 Gateway ↔ Worker                   │
├────────────────────────────────────────────┤
│  Worker Agent (Go)                          │
│  ├─ 心跳上报                                │
│  ├─ Task 执行                               │
│  └─ 结果回传                                │
└────────────────────────────────────────────┘
```

**特点**: 全自研，无依赖，单二进制部署。

### 4.2 阶段 2: 增强版（P0-P1 任务）

```
┌────────────────────────────────────────────┐
│  TUI Dashboard + Web Dashboard (双模式)     │
├────────────────────────────────────────────┤
│  Gateway (Go 网关)                         │
│  ├─ 节点注册/注销                           │
│  ├─ Task 队列 (优先级)                      │
│  ├─ 抢占调度                                │
│  └─ 成本核算                                │
├────────────────────────────────────────────┤
│  Bridge (Go)                                │
├────────────────────────────────────────────┤
│  Worker Agent (Go)                          │
│  ├─ 心跳上报                                │
│  ├─ Task 执行                               │
│  ├─ 结果回传                                │
│  └─ 细粒度 GPU 监控                         │
├────────────────────────────────────────────┤
│  Prometheus (监控)                          │
│  └─ GPU 指标采集                            │
└────────────────────────────────────────────┘
```

**新增**: 优先级队列、抢占调度、细粒度 GPU 监控、Prometheus 集成。

### 4.3 阶段 3: K8s 集成版（P2 任务）

```
┌────────────────────────────────────────────┐
│  TUI/Web Dashboard                         │
├────────────────────────────────────────────┤
│  ComputeHub Gateway (Go)                   │
│  └─ GPU 调度核心                            │
├────────────────────────────────────────────┤
│  Kubernetes Cluster                        │
│  ├── GPU Operator (GPU 驱动管理)           │
│  ├── Kueue (作业队列管理)                  │
│  ├── Prometheus (监控)                     │
│  └── Karpenter (弹性伸缩)                  │
├────────────────────────────────────────────┤
│  ComputeHub Bridge (Go)                    │
│  └─ 对接 K8s API + Kueue API               │
└────────────────────────────────────────────┘
```

**新增**: K8s 原生集成、Kueue 队列管理、Karpenter 弹性伸缩。

### 4.4 阶段 4: 国产化适配版（P3 任务）

```
┌────────────────────────────────────────────┐
│  TUI/Web Dashboard                         │
├────────────────────────────────────────────┤
│  ComputeHub Gateway (Go)                   │
│  └─ GPU 调度核心 + 多芯片适配               │
├────────────────────────────────────────────┤
│  Kubernetes + GPU Operator                 │
│  ├── NVIDIA (CUDA)                         │
│  ├── 昇腾 (CANN)                           │
│  ├── 寒武纪 (MLU)                          │
│  └─ 天数智芯 (BCI)                         │
├────────────────────────────────────────────┤
│  ComputeHub Bridge                         │
│  └─ 多芯片适配层                            │
└────────────────────────────────────────────┘
```

**新增**: 昇腾/寒武纪/天数智芯等多芯片适配。

---

## 5. 分阶段开发计划

### 5.1 Phase 1: P0 - 核心功能增强 (2 周)

#### 1.1 Task 优先级系统 (1 周)

**目标**: 实现 Task 优先级队列，支持高优先级任务抢占低优先级任务。

**任务分解**:

| 序号 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| 1.1.1 | 扩展 Task 模型，添加 Priority 字段 | 2h | - |
| 1.1.2 | 实现 Priority Queue 数据结构 | 4h | 1.1.1 |
| 1.1.3 | 修改 Gateway Task 提交接口，支持优先级 | 2h | 1.1.2 |
| 1.1.4 | 实现 Task 抢占逻辑 | 6h | 1.1.3 |
| 1.1.5 | TUI Dashboard 优先级显示 | 2h | 1.1.4 |
| 1.1.6 | 单元测试 + 集成测试 | 4h | 1.1.5 |

**技术要点**:

```go
// Task Priority 定义
type Priority int32

const (
    PriorityCritical Priority = 4  // 关键任务
    PriorityHigh     Priority = 3  // 高优先级
    PriorityMedium   Priority = 2  // 中优先级（默认）
    PriorityLow      Priority = 1  // 低优先级
    PriorityBatch    Priority = 0  // 批处理
)

// Priority Queue 实现
type PriorityQueue struct {
    items []*TaskItem
    mu    sync.Mutex
}

type TaskItem struct {
    Task      *Task
    Priority  Priority
    Submitted time.Time
    index     int
}
```

**验收标准**:
- [ ] Task 提交时指定优先级
- [ ] 高优先级 Task 优先调度
- [ ] 低优先级 Task 可被抢占
- [ ] 抢占时保存 checkpoint（优雅终止）
- [ ] TUI 显示优先级信息

#### 1.2 细粒度 GPU 监控 (1 周)

**目标**: 采集更详细的 GPU 指标，接入 Prometheus。

**任务分解**:

| 序号 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| 1.2.1 | 集成 nvidia-ml-py / nvidia-ml-py3 | 2h | - |
| 1.2.2 | 扩展 Worker 监控数据采集 | 4h | 1.2.1 |
| 1.2.3 | 添加 Prometheus Exporter | 4h | 1.2.2 |
| 1.2.4 | 集成 Grafana Dashboard | 2h | 1.2.3 |
| 1.2.5 | TUI 监控页面增强 | 4h | 1.2.4 |

**新增监控指标**:

```go
type GPUMetric struct {
    Utilization       float64 // GPU 利用率 (%)
    MemoryUsed        uint64  // 已用显存 (MB)
    MemoryTotal       uint64  // 总显存 (MB)
    Temperature       uint32  // 温度 (°C)
    PowerDraw         uint32  // 功耗 (W)
    SMUtilization     float64 // SM 利用率 (%)
    TensorUtilization float64 // Tensor Core 利用率 (%)
    ECCErrors         uint32  // ECC 错误数
    FanSpeed          uint32  // 风扇转速 (%)
    Clocks            struct {
        SM      uint32 // SM 频率 (MHz)
        Memory  uint32 // 显存频率 (MHz)
        Video   uint32 // 视频编码器频率 (MHz)
    }
}
```

**验收标准**:
- [ ] 采集 10+ 项 GPU 指标
- [ ] Prometheus 可抓取指标
- [ ] Grafana 有现成 Dashboard
- [ ] TUI 显示关键指标

### 5.2 Phase 2: P1 - K8s 集成评估 (1 月)

#### 2.1 GPU Operator 集成

**目标**: 评估是否用 GPU Operator 替代自研 Worker。

**评估维度**:

| 维度 | 当前 Worker | GPU Operator | 建议 |
|------|-----------|-------------|------|
| 部署复杂度 | 低（单二进制） | 中（Helm Chart） | 当前方案 |
| 功能覆盖 | 基础 | 全面（驱动/MIG/vGPU） | GPU Operator 优 |
| 维护成本 | 自研维护 | NVIDIA 维护 | GPU Operator 优 |
| 国产化支持 | 需自研 | 仅 NVIDIA | 当前方案优 |
| 学习曲线 | 低 | 中 | 当前方案优 |

**结论**: 
- 短期保留自研 Worker，保持轻量
- 中期提供 "K8s Worker" 模式（可选）
- 长期考虑 GPU Operator 兼容

#### 2.2 Kueue 集成评估

**目标**: 评估是否用 Kueue 替代自研队列。

**评估维度**:

| 维度 | 当前队列 | Kueue | 建议 |
|------|---------|-------|------|
| 功能完整度 | 基础 | 全面 | Kueue 优 |
| 多租户 | 无 | 强 | Kueue 优 |
| 优先级调度 | 无 | 强 | Kueue 优 |
| 抢占机制 | 无 | 强 | Kueue 优 |
| 与 K8s 集成 | 无 | 原生 | Kueue 优 |
| 部署复杂度 | 低 | 中 | 当前方案优 |

**结论**: 
- K8s 模式下建议集成 Kueue
- 非 K8s 模式保留自研队列
- 提供 "Kueue Mode" 可选开关

#### 2.3 Prometheus 集成

**目标**: 集成 Prometheus 作为标准监控方案。

**任务分解**:

| 序号 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| 2.3.1 | Gateway 添加 Prometheus metrics | 4h | - |
| 2.3.2 | Worker 添加 Prometheus metrics | 4h | - |
| 2.3.3 | docker-compose 集成 Prometheus | 2h | 2.3.1+2.3.2 |
| 2.3.4 | Grafana Dashboard 集成 | 2h | 2.3.3 |

### 5.3 Phase 3: P2 - 弹性与国产化 (2-3 月)

#### 3.1 Karpenter 弹性伸缩集成

**目标**: 集成 Karpenter 实现 GPU 节点弹性伸缩。

**任务分解**:

| 序号 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| 3.1.1 | K8s 部署环境搭建 | 2d | - |
| 3.1.2 | Karpenter NodePool 配置 | 1d | 3.1.1 |
| 3.1.3 | GPU 节点自动伸缩测试 | 2d | 3.1.2 |
| 3.1.4 | ComputeHub 文档更新 | 1d | 3.1.3 |

**预期效果**:
- GPU 节点从 0 到 N 秒级伸缩
- 任务量下降时自动缩容降低成本
- 多实例类型智能选择

#### 3.2 昇腾 CANN 适配

**目标**: 支持华为昇腾 GPU（Ascend 910B/310P）。

**任务分解**:

| 序号 | 任务 | 预计时间 | 依赖 |
|------|------|---------|------|
| 3.2.1 | 昇腾环境准备（硬件/驱动） | 1w | - |
| 3.2.2 | CANN 驱动集成评估 | 3d | 3.2.1 |
| 3.2.3 | Node Register 适配 | 3d | 3.2.2 |
| 3.2.4 | Worker Agent 适配 | 1w | 3.2.2 |
| 3.2.5 | 测试验证 | 3d | 3.2.4 |

**适配要点**:
```go
// 统一 GPU 抽象接口
type GPUProvider interface {
    // 设备信息
    GetDeviceCount() int
    GetDeviceNames() []string
    
    // 资源管理
    AllocateDevice(deviceName string) (Device, error)
    ReleaseDevice(device Device) error
    
    // 监控
    GetDeviceMetrics(device Device) (DeviceMetrics, error)
}

// NVIDIA 实现
type NVIDIAProvider struct { ... }

// 昇腾实现
type AscendProvider struct { ... }
```

### 5.4 Phase 4: P3 - 长期演进 (3-6 月)

#### 4.1 国产多芯片适配

| 芯片 | 状态 | 适配难度 | 预估时间 |
|------|------|---------|---------|
| 寒武纪 MLU | 量产 | 中 | 1 月 |
| 天数智芯 BCI | 量产 | 高 | 1-2 月 |
| 海光 DCU | 量产 | 中 | 1 月 |
| 摩尔线程 MTT | 量产 | 高 | 1-2 月 |

#### 4.2 Web Dashboard

**目标**: 提供 Web 界面，替代/补充 TUI。

**技术选型**:

| 方案 | 前端 | 后端 | 集成方式 | 建议 |
|------|------|------|---------|------|
| 方案 A | Vue 3 + Element Plus | Go (内嵌) | 单二进制 | ✅ 推荐 |
| 方案 B | React | Go (内嵌) | 单二进制 | 备选 |
| 方案 C | 独立前端 | Go (API) | 多组件 | 长期 |

**推荐方案 A**: 单二进制部署，Go 内嵌前端，维护简单。

---

## 6. 技术选型决策

### 6.1 语言栈

| 组件 | 语言 | 理由 |
|------|------|------|
| Gateway | Go | 高并发、低延迟、单二进制 |
| Worker Agent | Go | 与 Gateway 同语言，部署简单 |
| Dashboard | Go + 内嵌 | 单二进制，维护简单 |
| 适配层 | Go | 统一接口，易于扩展 |

### 6.2 数据持久化

| 数据 | 存储 | 理由 |
|------|------|------|
| 节点信息 | SQLite | 轻量，单文件 |
| Task 记录 | SQLite | 轻量 |
| 监控数据 | TSDB / 文件 | 时序数据 |
| 成本数据 | SQLite | 轻量 |

### 6.3 通信协议

| 组件间 | 协议 | 理由 |
|--------|------|------|
| TUI ↔ Gateway | gRPC | 高效，强类型 |
| Gateway ↔ Worker | gRPC | 双向流，心跳 |
| Worker ↔ 本地 | POSIX | 同机通信 |

### 6.4 容器化

```dockerfile
# ComputeHub 单镜像
FROM golang:1.23-alpine AS builder
COPY . /app
RUN cd /app && go build -o computehub .

FROM alpine:3.19
COPY --from=builder /app/computehub /usr/local/bin/
ENTRYPOINT ["computehub"]
```

---

## 7. 集成规范

### 7.1 集成原则

1. **核心自研**: GPU 调度核心不外包
2. **接口抽象**: 所有外部依赖通过接口隔离
3. **可选开关**: 每个集成都是可选的（feature flag）
4. **向后兼容**: 新功能不破坏旧版本

### 7.2 扩展点定义

```go
// 1. GPU Provider 扩展点
type GPUProvider interface {
    Init(config *ProviderConfig) error
    AllocateGPU(deviceName string, spec *GPUSpec) (GPUInstance, error)
    ReleaseGPU(instance GPUInstance) error
    GetMetrics(deviceName string) (*GPUMetrics, error)
}

// 2. Task Scheduler 扩展点
type TaskScheduler interface {
    Submit(task *Task) error
    GetPendingTasks() ([]*Task, error)
    Execute(task *Task) (*TaskResult, error)
    Cancel(taskID string) error
}

// 3. Monitor 扩展点
type Monitor interface {
    CollectMetrics() (*ClusterMetrics, error)
    RegisterAlertRule(rule AlertRule) error
    GetAlertHistory() ([]*Alert, error)
}

// 4. Billing 扩展点
type Billing interface {
    CalculateCost(task *Task) (*CostReport, error)
    GetBillingHistory(nodeID string) ([]*BillingRecord, error)
    SetPricing(pricing *PricingConfig) error
}
```

### 7.3 配置管理

```yaml
# computehub-config.yaml
server:
  host: 0.0.0.0
  port: 8080
  tls:
    enabled: false

storage:
  type: sqlite  # sqlite | postgres
  path: ./data/computehub.db

gpu:
  provider: nvidia  # nvidia | ascend | cambricon | hYGON
  device_plugin: auto  # auto | nvidia | ascend | manual

monitor:
  prometheus:
    enabled: false  # 可选启用
    endpoint: http://prometheus:9090
  grafana:
    enabled: false  # 可选启用
    endpoint: http://grafana:3000

scheduler:
  mode: standalone  # standalone | kueue | volcano
  priority_enabled: true  # 优先级开关
  preemption_enabled: true  # 抢占开关
  max_parallel_tasks: 100

billing:
  enabled: true
  currency: CNY
  pricing:
    nvidia-a100: 10.0  # 元/小时
    nvidia-rtx-4090: 3.0
    ascend-910b: 8.0
```

---

## 8. 风险与应对

### 8.1 技术风险

| 风险 | 影响 | 概率 | 应对策略 |
|------|------|------|---------|
| 国产芯片驱动不成熟 | 适配困难 | 中 | 先做昇腾（文档最全） |
| K8s 集成复杂度高 | 延期 | 中 | 分阶段，先评估再实施 |
| 性能瓶颈 | 用户体验差 | 低 | 压测 + 性能调优 |
| 安全漏洞 | 数据泄露 | 低 | 定期安全审计 |

### 8.2 市场风险

| 风险 | 影响 | 概率 | 应对策略 |
|------|------|------|---------|
| NVIDIA 降价 | 价格优势丧失 | 低 | 强调开源+轻量优势 |
| 大厂入场 | 竞争加剧 | 中 | 专注中小企业市场 |
| 开源替代出现 | 用户流失 | 低 | 持续迭代，保持领先 |

### 8.3 团队风险

| 风险 | 影响 | 概率 | 应对策略 |
|------|------|------|---------|
| 单人维护 | 开发慢 | 中 | 写文档，降低维护成本 |
| 技术债务 | 维护难 | 高 | 定期重构，代码审查 |

---

## 9. 里程碑检查点

### 9.1 Phase 1 里程碑

```
里程碑: P0-Core-Complete
日期: 2026-05-18

检查清单:
[ ] Task 优先级系统上线
[ ] 细粒度 GPU 监控上线
[ ] Prometheus 集成上线
[ ] 压测通过 (100 并发 Task)
[ ] 文档更新
```

### 9.2 Phase 2 里程碑

```
里程碑: P1-K8s-Evaluation-Complete
日期: 2026-06-04

检查清单:
[ ] GPU Operator 集成评估报告
[ ] Kueue 集成评估报告
[ ] K8s 部署指南
[ ] 决策: 是否集成 K8s
```

### 9.3 Phase 3 里程碑

```
里程碑: P2-Elasticity-Complete
日期: 2026-07-04

检查清单:
[ ] Karpenter 弹性伸缩上线
[ ] 昇腾 CANN 适配上线
[ ] 多芯片支持验证
```

### 9.4 Phase 4 里程碑

```
里程碑: P3-MultiChip-Complete
日期: 2026-11-04

检查清单:
[ ] 昇腾支持
[ ] 寒武纪支持
[ ] 天数智芯支持
[ ] Web Dashboard 上线
```

---

## 附录 A: 技术栈清单

```
语言:     Go 1.23+
数据库:   SQLite (轻量) | PostgreSQL (企业)
监控:     Prometheus + Grafana
调度:     自研 | Kueue (K8s 模式)
容器:     Docker | Podman
CI/CD:    GitHub Actions
部署:     单二进制 | Docker | K8s Helm
```

## 附录 B: 参考项目

| 项目 | 用途 | 链接 |
|------|------|------|
| NVIDIA GPU Operator | GPU 设备插件 | github.com/NVIDIA/gpu-operator |
| Kueue | K8s 作业队列 | github.com/kubernetes-sigs/kueue |
| Volcano | K8s 批处理调度 | github.com/volcano-sh/volcano |
| Karpenter | K8s 弹性伸缩 | github.com/kubernetes-sigs/karpenter |
| Ray | 分布式 AI | github.com/ray-project/ray |

---

*文档版本: v1.0*  
*最后更新: 2026-05-04*  
*维护者: 小智 (AI Assistant)*
