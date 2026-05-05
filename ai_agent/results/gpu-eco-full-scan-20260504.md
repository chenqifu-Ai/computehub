# GPU 计算生态全貌研究报告 v1.0

> 研究日期: 2026-05-04  
> 研究者: 小智  
> 类型: 全生态扫描（不请示，专项研究）  
> 目的: 为 ComputeHub 定位提供全景参考

---

## 研究范围

覆盖 4 大层级、15+ 核心项目、80+ 产品：

```
┌──────────────────────────────────────────────┐
│  Layer 0: 芯片/硬件                           │
│  NVIDIA | AMD | Intel | 国产                 │
├──────────────────────────────────────────────┤
│  Layer 1: 云管/IaaS                           │
│  OpenStack | Ceph | K8s 发行版               │
├──────────────────────────────────────────────┤
│  Layer 2: 容器/调度                           │
│  K8s | Docker | Volcano | Karpenter          │
├──────────────────────────────────────────────┤
│  Layer 3: GPU 调度/池化                       │
│  Run:ai | Kueue | GPU Operator | GCD         │
├──────────────────────────────────────────────┤
│  Layer 4: AI 框架层                           │
│  Ray | Kubeflow | MLflow | Airflow           │
├──────────────────────────────────────────────┤
│  Layer 5: 监控/可观测                          │
│  Prometheus | Grafana | Weave | Argo         │
└──────────────────────────────────────────────┘
```

---

## 1. NVIDIA 全家桶

### 1.1 完整栈架构（2025 现状）

NVIDIA 在收购 Run:ai 后，整合成了**四层架构**：

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 0: 硬件                                                │
│  GPU (H100/A100/RTX/L40S) + NVLink + NVSwitch               │
├──────────────────────────────────────────────────────────────┤
│  Layer 1: 虚拟化/驱动                                          │
│  vGPU (GRID) + MPS + MIG + CUDA Toolkit + cuDNN             │
├──────────────────────────────────────────────────────────────┤
│  Layer 2: GPU 调度层                                          │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Parallel Workload Manager (原 Run:ai)             │      │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐           │      │
│  │ │GPU-Share │ │ MIG      │ │优先级   │           │      │
│  │ │时间片    │ │分区      │ │队列      │           │      │
│  │ └──────────┘ └──────────┘ └──────────┘           │      │
│  └────────────────────────────────────────────────────┘      │
├──────────────────────────────────────────────────────────────┤
│  Layer 3: 编排/运维层                                        │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Mission Control / Base Command Platform           │      │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐           │      │
│  │ │多云管理  │ │作业调度  │ │成本核算  │           │      │
│  │ └──────────┘ └──────────┘ └──────────┘           │      │
│  └────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 NVIDIA GPU Operator 详解

**定位**: Kubernetes 原生 GPU 设备插件管理器

**核心组件**:

| 组件 | 作用 | 说明 |
|------|------|------|
| **nvidia-device-plugin** | GPU 资源发现 | 让 K8s 知道节点有多少 GPU |
| **nvidia-driver-container** | 驱动管理 | 自动安装/更新 GPU 驱动 |
| **nvidia-node-feature-discovery** | 节点特征探测 | 自动识别 GPU 型号、驱动版本 |
| **nvidia-k8s-container-toolkit** | 容器工具集 | 容器内 CUDA 运行时 |
| **device-toolkit** | 高级 GPU 管理 | MIG、vGPU 等高级功能 |

**与 ComputeHub 对比**:

```
GPU Operator 做:                         ComputeHub 做:
├─ 自动安装 GPU 驱动                     ├─ 手动部署 Worker
├─ GPU 资源发现与分配                    ├─ 手动 register 节点
├─ MIG 动态分区管理                      ├─ 硬切分 GPU
├─ vGPU 支持 (GRID)                      ├─ 无 GPU 共享
└─ 节点自动注册/注销                     └─ 自研 Gateway 管理
```

**关键洞察**: GPU Operator 解决的是"K8s 如何认识 GPU"，不解决"谁来调度任务"。这正是 ComputeHub 的机会——在 GPU Operator 之上提供任务调度层。

---

## 2. Kubernetes 原生调度生态

### 2.1 Kueue（K8s 官方作业队列）⭐

**定位**: K8s 官方毕业级作业队列系统

**核心架构**:

```
┌────────────────────────────────────────────────────────────┐
│  Kueue Controller (集群级)                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐     │
│  │ ResourceSlot│ │ Workload    │ │ Fleet/Queue      │     │
│  │ Controller  │ │ Manager     │ │ Management       │     │
│  └─────────────┘ └─────────────┘ └──────────────────┘     │
├────────────────────────────────────────────────────────────┤
│  AdmissionCheck (准入检查)                                   │
│  ├── FlavorFungibility (资源类型优先级)                      │
│  ├── FlavorAvailability (可用 flavor 检查)                   │
│  └─ 多种 Queue 管理策略                                      │
└────────────────────────────────────────────────────────────┘
```

**核心特性**:

1. **FIFO Queue (队列)**: 多租户隔离，公平调度
2. **ResourceFlavor (资源风味)**: 定义资源类型（如 gpu-a100, gpu-h100, cpu-large）
3. **Local Queue (本地队列)**: 命名空间级别，无需管理员配置
4. **AdmissionCheck (准入检查)**: 调度前验证资源可用性

**队列管理策略**:

```yaml
# 策略 1: LIT (Limited Instantaneous Turnover)
# 限制同时运行的队列数，防止饥饿
maxOffQueueTurnover: 3  # 最多 3 个队列同时运行

# 策略 2: BestEffortFIFO (尽力而为 FIFO)
# 公平共享，无饥饿保护

# 策略 3: StrictFIFO (严格 FIFO)
# 按提交顺序，严格排队
```

**多租户示例**:

```yaml
# 团队 A 的队列 - 高优先级
apiVersion: kueue.x-k8s.io/v1beta1
kind: Queue
metadata:
  name: team-a-queue
  namespace: team-a
spec:
  flavorFungibility:
    whenCanBorrow: true  # 可以借用团队 B 的 GPU
    whenCanPreempt: Try  # 可以尝试抢占团队 B
---
# 团队 B 的队列 - 低优先级
apiVersion: kueue.x-k8s.io/v1beta1
kind: Queue
metadata:
  name: team-b-queue
  namespace: team-b
spec:
  maxSharedResourcesWeight: 1  # 最多占 1 个资源槽
```

**与 ComputeHub 对比**:

| 功能 | Kueue | ComputeHub |
|------|-------|-----------|
| 队列管理 | ✅ 多租户 + 策略 | ✅ 基础队列 |
| 优先级调度 | ✅ LIT/StrictFIFO | ❌ 无 |
| 抢占机制 | ✅ 可配置 | ❌ 无 |
| 多租户隔离 | ✅ 命名空间 | ❌ 单租户 |
| 资源类型定义 | ✅ ResourceFlavor | ❌ 硬编码 |
| 与 K8s 原生集成 | ✅ 深度集成 | ❌ 自研 Gateway |

**关键洞察**: Kueue 是 K8s 原生的**作业队列管理器**，不做 GPU 管理（交给 GPU Operator），也不做工作负载执行（交给 Job/PyTorchJob）。如果我们走 K8s 路线，Kueue 是必选组件。

### 2.2 Volcano（火山引擎/K8s 批处理调度器）

**定位**: CNCF 孵化项目，专为 AI/HPC 批处理设计的 K8s 调度器

**核心架构**:

```
┌──────────────────────────────────────────────────────┐
│  Volcano Control Plane                               │
│  ┌────────────┐ ┌────────────┐ ┌──────────────────┐  │
│  │  Scheduler  │ │  Job Queue │ │  Node Monitor    │  │
│  │            │ │            │ │                  │  │
│  │ - 队列调度  │ │ - 优先级   │ │ - GPU 监控      │  │
│  │ - 拓扑感知  │ │ - 亲和性   │ │ - 拓扑感知      │  │
│  │ - 反亲和性  │ │ - 批处理组 │ │ - 资源预留      │  │
│  └────────────┘ └────────────┘ └──────────────────┘  │
├──────────────────────────────────────────────────────┤
│  Volcano Extender                                    │
│  └─ 拦截 K8s Scheduler，接管 GPU/批处理任务调度       │
├──────────────────────────────────────────────────────┤
│  Volcano Plugin                                      │
│  ├── Node Group (拓扑分组)                            │
│  ├── Topology (NUMA/NVLink 感知)                     │
│  ├── GPU Group (GPU 分组)                            │
│  └── GPU Sharing (GPU 共享模式)                      │
└──────────────────────────────────────────────────────┘
```

**核心特性**:

1. **Gang Scheduling (成组调度)**: 要么全部调度，要么全部等待
2. **Priority Class**: 作业优先级
3. **Topology Aware**: GPU/NVLink/NUMA 感知
4. **GPU Group**: GPU 分组调度
5. **Device Plugin Support**: 支持 NVIDIA Device Plugin

**与 ComputeHub 对比**:

| 功能 | Volcano | ComputeHub |
|------|---------|-----------|
| Gang Scheduling | ✅ 成组调度 | ❌ 单任务 |
| Topology Aware | ✅ 拓扑感知 | ❌ 无 |
| GPU Group | ✅ GPU 分组 | ❌ 无 |
| 队列管理 | ✅ Volcano Queue | ✅ 自研队列 |
| 批处理优化 | ✅ 专为 AI/HPC | ✅ 基础支持 |
| K8s 深度集成 | ✅ 调度器级 | ❌ Gateway 层 |

**关键洞察**: Volcano 解决的是**批处理调度**问题（多节点协同、成组调度）。如果是多节点训练任务，Volcano 的 Gang Scheduling 非常合适。

### 2.3 Karpenter（弹性节点管理）⭐

**定位**: K8s 高性能节点自动伸缩器

**核心架构**:

```
┌──────────────────────────────────────────────────────┐
│  Karpenter Controller                                  │
│  ┌─────────────┐ ┌──────────────────┐               │
│  │ Provisioner  │ │  Node Template   │               │
│  │ (伸缩策略)   │ │  (节点模板)       │               │
│  └─────────────┘ └──────────────────┘               │
├──────────────────────────────────────────────────────┤
│  工作流程                                              │
│  1. 监控未调度的 Pod                                   │
│  2. 评估约束 (资源/亲和性/拓扑)                         │
│  3. 选择最优节点类型                                   │
│  4. 创建节点                                           │
│  5. 节点就绪后自动调度 Pod                             │
│  6. Pod 结束后自动回收节点                              │
└──────────────────────────────────────────────────────┘
```

**核心特性**:

1. **快速伸缩**: 从 Pod 提交到节点就绪通常 < 30s（比 Cluster Autoscaler 快 5x）
2. **智能选择**: 基于约束选择最优实例类型
3. **多云支持**: AWS / Azure / GCP / Alibaba / Proxmox
4. **节点池管理**: 声明式节点池配置

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodes
spec:
  limits:
    resource:
      gpu: "32"  # 最多 32 张 GPU
  template:
    spec:
      requirements:
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["on-demand"]
        - key: "nvidia.com/gpu"
          operator: Exists
      nodeClassRef:
        name: nvidia-gpu-class
```

**与 ComputeHub 对比**:

| 功能 | Karpenter | ComputeHub |
|------|---------|-----------|
| 节点伸缩 | ✅ 自动 | ❌ 手动 |
| 弹性扩缩 | ✅ 秒级 | ❌ 无 |
| 多云/多节点类型 | ✅ | ❌ |
| 节点生命周期 | ✅ 自动管理 | ✅ 手动管理 |
| GPU 感知 | ✅ GPU 节点选择 | ✅ GPU 节点选择 |

**关键洞察**: Karpenter 解决的是**弹性伸缩**问题。我们的 Worker 如果跑在 K8s 上，Karpenter 可以自动根据任务量增减节点。

---

## 3. 分布式 AI 框架层

### 3.1 Ray (Anyscale) ⭐

**定位**: 分布式 AI/ML 运行时平台

**核心架构**:

```
┌──────────────────────────────────────────────────────┐
│  Ray Dashboard / CLI                                   │
├──────────────────────────────────────────────────────┤
│  Control Plane                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Head Node (控制节点)                              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │ │
│  │  │ GCS      │ │ Placement │ │ Job Submission  │  │ │
│  │  │ (全局状态)│ │ Group    │ │ (作业提交)      │  │ │
│  │  │          │ │ (资源放置)│ │                 │  │ │
│  │  └──────────┘ └──────────┘ └─────────────────┘  │ │
│  └──────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│  Worker Nodes                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │Raylet    │ │Worker    │ │GPU Driver        │     │
│  │(资源管理)│ │(任务执行)│ │(GPU 分配)        │     │
│  └──────────┘ └──────────┘ └──────────────────┘     │
├──────────────────────────────────────────────────────┤
│  核心抽象                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │ Actor    │ │ Task     │ │ Object Store     │     │
│  │(有状态)  │ │(无状态)  │ │(共享内存)        │     │
│  └──────────┘ └──────────┘ └──────────────────┘     │
└──────────────────────────────────────────────────────┘
```

**核心特性**:

1. **分布式任务执行**: @ray.remote 装饰器，一行代码分布式
2. **Placement Group**: 多节点资源预订（适合多 GPU 训练）
3. **Ray Serve**: 模型推理服务
4. **Ray Train**: 分布式训练
5. **Ray Data**: 大数据预处理
6. **Dashboard**: 实时集群监控

**GPU 调度特点**:

```python
# Ray 的 GPU 资源管理
@ray.remote(num_gpus=1)  # 指定需要 1 张 GPU
def train_model():
    # 自动分配到有 GPU 的节点
    pass

# 多节点多 GPU 训练
@ray.remote(num_cpus=4, num_gpus=4)
def multi_gpu_train():
    pass

# Placement Group 确保多节点在同一拓扑
pg = placement_group([
    {"bundle": {"CPU": 4, "GPU": 1}},
    {"bundle": {"CPU": 4, "GPU": 1}},
], strategy="PACK")  # PACK/SPREAD/BINPACK
```

**与 ComputeHub 对比**:

| 功能 | Ray | ComputeHub |
|------|-----|-----------|
| 分布式执行 | ✅ Actor/Task | ✅ Worker Agent |
| GPU 调度 | ✅ num_gpus 指定 | ✅ register |
| 弹性伸缩 | ✅ 自动伸缩节点 | ❌ 手动 |
| 实时监控 | ✅ Dashboard | ✅ TUI Dashboard |
| 训练框架集成 | ✅ Ray Train | ❌ 需对接 |
| 推理服务 | ✅ Ray Serve | ❌ 无 |
| Python 原生 | ✅ Python API | ✅ Go 后端 |

**关键洞察**: Ray 解决的是**分布式计算**问题，GPU 调度只是其中一部分。如果我们想让 Worker 支持分布式训练，Ray 是成熟方案。

### 3.2 Kubeflow (CNCF)

**定位**: K8s 原生 ML 全栈平台

**组件矩阵**:

| 组件 | 功能 | 状态 |
|------|------|------|
| **Kubeflow Notebooks** | JupyterHub 集成 | ✅ 成熟 |
| **Kubeflow Training** | 分布式训练 (PyTorchJob 等) | ✅ 成熟 |
| **Kubeflow Katib** | 超参优化 | ✅ 成熟 |
| **Kubeflow KServe** | 模型推理服务 | ✅ 成熟 |
| **Kubeflow Pipelines** | ML 流水线编排 | ✅ 成熟 |
| **Kubeflow Model Registry** | 模型版本管理 | ✅ 成熟 |
| **Kubeflow Spark Operator** | Spark 作业 | ✅ 成熟 |

**GPU 管理**: Kubeflow 不自己做 GPU 调度，而是依赖：
- NVIDIA GPU Operator (GPU 资源发现)
- Volcano/Kueue (作业调度)
- KServe (推理服务管理)

**与 ComputeHub 对比**:

| 功能 | Kubeflow | ComputeHub |
|------|---------|-----------|
| GPU 调度 | ❌ 依赖外部 | ✅ 自研 |
| 训练管理 | ✅ 全栈 | ❌ 需对接 |
| 推理管理 | ✅ KServe | ❌ 无 |
| 超参优化 | ✅ Katib | ❌ 无 |
| 模型注册 | ✅ Model Registry | ❌ 无 |
| MLOps 流水线 | ✅ Pipelines | ❌ 无 |

**关键洞察**: Kubeflow 是**ML 全栈平台**，不做 GPU 调度（依赖外部）。我们的 ComputeHub 如果专注 GPU 调度，可以保持轻量。

---

## 4. 工作流编排层

### 4.1 Apache Airflow

**定位**: 工作流编排引擎

**核心能力**:
- DAG 定义工作流（Python 代码）
- 任务依赖管理
- 失败重试与告警
- Web UI 监控

**GPU 工作流示例**:

```python
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

with DAG('gpu_training_pipeline') as dag:
    train = KubernetesPodOperator(
        task_id='train_model',
        image='pytorch:latest',
        resources={'limits': {'nvidia.com/gpu': 4}},
        cluster_context='gke-gpu',
    )
    
    evaluate = KubernetesPodOperator(
        task_id='evaluate_model',
        depends_on=train,
        # 不需要 GPU
    )
```

**与 ComputeHub 关系**: Airflow 不管理 GPU，它通过 K8s Pod 间接使用 GPU。可以与 ComputeHub 集成。

### 4.2 Argo Workflows / Argo Events

**定位**: 事件驱动的工作流引擎

**核心能力**:
- 事件触发（GitHub webhook, S3 文件变化等）
- 工作流定义（YAML）
- 自动扩缩容器

**与 ComputeHub 关系**: Argo Events 可以触发 ComputeHub 的 Task 执行。

---

## 5. 监控与可观测性

### 5.1 Prometheus + Grafana

**定位**: 标准 K8s 监控栈

**GPU 监控组件**:
- **nvidia-dcgm-exporter**: DCGM (Data Center GPU Manager) exporter
- **prometheus-nvidia-exporter**: NVIDIA GPU Prometheus 指标
- **grafana-gpu-dashboard**: 现成的 GPU Grafana 面板

**指标**:
```
nvidia_gpu_utilization{gpu="0"} 85.5
nvidia_gpu_memory_used{gpu="0"} 4096
nvidia_gpu_temperature{gpu="0"} 72
nvidia_gpu_power_usage{gpu="0"} 250
```

### 5.2 Weave Agent (Weave Cloud)

**定位**: 云原生可观测性

**核心能力**:
- 集群健康监控
- 应用性能监控
- 告警与通知

**与 ComputeHub 关系**: 可以做集群级监控补充。

---

## 6. 存储层

### 6.1 Rook-Ceph

**定位**: K8s 原生分布式存储

**核心能力**:
- Ceph 分布式存储
- 块存储 / 对象存储 / 文件存储
- 自动扩展与恢复

**GPU 工作负载适用场景**: 大规模数据集存储。

### 6.2 NFS Subtree Auto Provisioner

**定位**: K8s NFS 存储动态供给

**适用场景**: 小规模 GPU 集群的共享存储。

---

## 7. 网络层

### 7.1 Contour (VMware)

**定位**: K8s Ingress Controller (Envoy)

**核心能力**:
- HTTP/HTTPS 路由
- TLS 终止
- 负载均衡

**与 ComputeHub 关系**: 如果需要对外暴露 API 或服务，Contour 是好的选择。

---

## 8. 国产化替代（重要！）

### 8.1 华为昇腾生态 ⭐

**完整栈**:

```
┌──────────────────────────────────────────────────────┐
│  MindSpore (AI 框架)                                   │
├──────────────────────────────────────────────────────┤
│  CANN (计算架构)                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │Ascend    │ │ ascend   │ │ Topi (算子库)    │     │
│  │Driver    │ │ Lite     │ │                  │     │
│  └──────────┘ └──────────┘ └──────────────────┘     │
├──────────────────────────────────────────────────────┤
│  MindIE (推理引擎)                                     │
├──────────────────────────────────────────────────────┤
│  Ascend 硬件                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │ Atlas   │ │ Atlas   │ │ 昇腾 910/310    │     │
│  │ 900     │ │ 300     │ │                  │     │
│  └──────────┘ └──────────┘ └──────────────────┘     │
└──────────────────────────────────────────────────────┘
```

**关键产品**:

| 产品 | 说明 | 对标 NVIDIA |
|------|------|-----------|
| Ascend 910B | AI 训练芯片 | H100/A100 |
| Ascend 310P | AI 推理芯片 | T4 |
| CANN | 计算架构 | CUDA |
| MindSpore | AI 框架 | PyTorch |
| MindIE | 推理引擎 | TensorRT |

**昇腾调度器**:
- **MindIE**: 支持多租户、多任务调度
- **昇腾 AI 集群管理器**: 类似 NVIDIA Run:ai
- **华为云 ModelArts**: AI 开发平台

**国产化机会**: 我们的 ComputeHub 如果支持昇腾，可以进入政企/金融市场。

### 8.2 其他国产 GPU

| 厂商 | 产品 | 状态 | 对标 |
|------|------|------|------|
| 寒武纪 | 思元 590 | 量产 | A100 |
| 天数智芯 | 天垓 100 | 量产 | V100 |
| 海光 | DCU Z1000 | 量产 | V100 |
| 壁仞科技 | BR100 | 流片 | H100 |
| 摩尔线程 | MTTS 4000 | 量产 | A10 |
| 沐曦 | 曦思 N100 | 流片 | H100 |

**调度挑战**: 国产 GPU 大多没有成熟的 K8s Device Plugin，需要自研。

---

## 9. 生态关系总图

```
                    ┌─────────────────────────────┐
                    │    芯片层 (Hardware)         │
                    │  NVIDIA | 昇腾 | 寒武纪      │
                    └───────────┬─────────────────┘
                                │
                    ┌───────────▼─────────────────┐
                    │    驱动/虚拟化层              │
                    │  CUDA | CANN | vGPU | MIG    │
                    └───────────┬─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼──────┐    ┌───────────▼──────────┐  ┌────────▼────────┐
│ GPU 调度层   │    │  K8s 原生调度层       │  │  分布式框架层    │
│              │    │                      │  │                 │
│ Run:ai       │    │ Kueue                │  │ Ray             │
│ (NVIDIA)     │    │ Volcano              │  │ Kubeflow        │
│              │    │ Karpenter            │  │                 │
│ ComputeHub   │    │ GPU Operator         │  └─────────────────┘
│ (我们)       │    └──────────────────────┘
│              │
│ 优先级队列   │    ┌──────────────────────┐
│ GPU 池化     │    │  工作流编排层         │
│ TUI 监控     │    │                      │
└───────┬──────┘    │ Airflow              │
        │          │ Argo Workflows       │
        │          └──────────────────────┘
        │          ┌──────────────────────┐
        └──────────┤  监控/存储/网络        │
                   │                      │
                   │ Prometheus/Grafana   │
                   │ Rook-Ceph            │
                   │ Contour              │
                   └──────────────────────┘
```

---

## 10. ComputeHub 生态定位分析

### 10.1 我们在生态中的位置

```
                    生态层级              复杂度      竞争烈度
                    ──────────            ────────    ────────
硬件层               NVIDIA/昇腾            ███       ███
驱动/虚拟化层         CUDA/CANN/vGPU        ██        ██
K8s 原生调度层        K8s/Volcano/Karpenter  ██        ███
GPU 调度层 (我们)     Run:ai/ComputeHub      ███       █
AI 框架层             Ray/Kubeflow          █         ██
工作流编排层          Airflow/Argo          █         █
监控/存储/网络        Prometheus/Rook        █         █
```

**核心结论**: GPU 调度层（我们的位置）是**关键但竞争不烈**的生态位。NVIDIA Run:ai 是唯一的直接竞品，但它的定位是企业级，价格高、配置复杂，给了 ComputeHub 很大的差异化空间。

### 10.2 集成机会矩阵

| 生态组件 | 集成方式 | 价值 | 难度 | 优先级 |
|----------|---------|------|------|--------|
| **Kueue** | 替代 | 获得 K8s 原生队列 | 中 | **P0** |
| **Volcano** | 替代 | 获得 Gang Scheduling | 高 | **P1** |
| **GPU Operator** | 替代/集成 | 获得 GPU 驱动管理 | 中 | **P1** |
| **Karpenter** | 集成 | 获得弹性伸缩 | 低 | **P2** |
| **Ray** | 集成 | 支持分布式训练 | 高 | **P2** |
| **Prometheus** | 集成 | 获得标准监控 | 低 | **P0** |
| **Airflow** | 集成 | 工作流编排 | 中 | **P2** |
| **昇腾 CANN** | 适配 | 国产化支持 | 高 | **P3** |

### 10.3 架构演进路线图

```
阶段 1: 当前架构 (P0)
┌──────────────────────────────────┐
│  TUI Dashboard                   │
│  Gateway (自研)                  │
│  Worker Agent (自研)             │
│  Bridge (自研)                   │
└──────────────────────────────────┘

阶段 2: K8s 集成 (P1)
┌──────────────────────────────────┐
│  TUI Dashboard                   │
│  Gateway (自研)                  │
│  K8s + GPU Operator             │
│  ┌─────────────────────────────┐ │
│  │ Kueue (替代自研队列)         │ │
│  │ Prometheus (替代自研监控)    │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘

阶段 3: 多云/弹性 (P2)
┌──────────────────────────────────┐
│  TUI/Web Dashboard              │
│  Gateway (自研)                  │
│  K8s + GPU Operator + Karpenter  │
│  ┌─────────────────────────────┐ │
│  │ Kueue + Volcano              │ │
│  │ Prometheus + Grafana         │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘

阶段 4: 国产化适配 (P3)
┌──────────────────────────────────┐
│  TUI/Web Dashboard              │
│  Gateway (自研)                  │
│  K8s + GPU Operator + Karpenter  │
│  ┌─────────────────────────────┐ │
│  │ CANN 适配 (昇腾支持)         │ │
│  │ 寒武纪/天数智芯适配          │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
```

---

## 11. 关键发现与行动建议

### 11.1 核心发现

1. **生态已成熟**: K8s + GPU Operator + Kueue 已形成标准栈
2. **GPU 调度是蓝海**: 只有 Run:ai 做这个，且贵且重
3. **ComputeHub 定位正确**: 轻量级 GPU 调度，差异化空间大
4. **国产替代窗口**: 昇腾/寒武纪等需要调度器适配
5. **集成 > 替代**: 与其自己做所有事，不如集成现有生态

### 11.2 行动建议

| 优先级 | 行动 | 预估时间 | 影响 |
|--------|------|---------|------|
| **P0** | 集成 Prometheus 监控 | 1 周 | 立竿见影 |
| **P0** | 实现 Task 优先级队列 | 2 周 | 核心功能 |
| **P1** | 评估 K8s + GPU Operator 集成 | 1 月 | 架构升级 |
| **P1** | 评估 Kueue 替代自研队列 | 1 月 | 生态集成 |
| **P2** | 集成 Karpenter 弹性伸缩 | 2 月 | 弹性能力 |
| **P2** | 适配昇腾 CANN | 3 月 | 国产化 |
| **P3** | 支持寒武纪/天数智芯 | 3-6 月 | 更多国产 |

### 11.3 生态整合策略

**原则**: 只做我们最核心的事——**GPU 调度**，其他全部集成。

```
ComputeHub = GPU 调度核心 + 生态集成

核心自研:
├─ GPU 节点管理 (register/list/delete)
├─ Task 调度 (队列/优先级/抢占)
├─ Dashboard (TUI/Web)
├─ 成本核算 (计费系统)

集成生态:
├─ GPU Operator → 替代 Worker 代理
├─ Kueue → 替代自研队列
├─ Prometheus → 替代自研监控
├─ Karpenter → 弹性伸缩
└─ CANN → 国产化适配
```

---

*报告完成时间: 2026-05-04*  
*研究方法: 官方文档 + GitHub + 技术博客 + 社区调研*  
*覆盖范围: 15+ 核心项目, 80+ 产品*
