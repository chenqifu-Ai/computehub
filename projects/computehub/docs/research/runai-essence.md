# Run:ai 精华吸收 — ComputeHub 借鉴指南

> 来源: NVIDIA Run:ai Docs (2026-04/05)
> 整理: 小智 | 2026-05-04

---

## 一、架构设计精华

### 1.1 控制面 + 集群分离

```
Control Plane (管理面)            Cluster (执行面)
┌─────────────────┐            ┌──────────────────┐
│ Web UI / API/CLI│◄──心跳──►  │ K8s + Run:ai     │
│ 多集群管理      │  (仅元数据) │ Scheduler        │
│ 用户/权限/配额  │  outbound   │ Workload Manager │
│ 监控/审计       │  only      │ GPU 节点         │
└─────────────────┘            └──────────────────┘
```

**ComputeHub 现状**: Gateway 同时扮演控制面和执行调度 → 分离做得不够清晰
**可吸收**: 虽然咱不走 K8s，但控制面与执行面的"仅同步元数据"原则很好——Gateway 只存节点心跳、任务状态，不传业务数据

### 1.2 插件式 Workload 类型

Run:ai 支持 3 种原生 Workload + N 种第三方框架，通过 **Resource Interface (RI)** 统一管理：
- **Workspaces** — Jupyter/IDE 交互式开发
- **Training** — 分布式训练（PyTorch/TF）
- **Inference** — 推理服务（NIM/HF）
- **第三方** — 通过 API 注册新类型

**ComputeHub 现状**: 目前 Worker 只执行 shell 脚本，任务类型单一
**可吸收**: 定义 Workload Type 接口，让不同任务类型可插拔

---

## 二、调度系统精华

### 2.1 核心概念体系

| 概念 | Run:ai 实现 | ComputeHub 可吸收 |
|------|------------|-------------------|
| **调度队列 (Queue)** | 每个 Project/NodePool 一对 | Worker 按优先级排队 |
| **Quota (配额)** | Project/Department 两层 | 节点级别的 max_tasks |
| **Over Quota** | 用别人不用的资源 | **可借用的空闲资源** |
| **Fairshare** | Quota + Over Quota 公平分配 | 按权重分配 |
| **Gang Scheduling** | 全部资源就绪才启动 | 多 Worker 协同任务 |
| **Bin-Pack / Spread** | 紧凑 vs 分散 | TUI 可切换的调度策略 |

### 2.2 调度优先级链

Run:ai 的调度决策链：

```
1. 部门优先级 (Department Rank)
2. 项目优先级 (Project Rank)
3. 同一 Queue 内的工作负载优先级
4. 公平性平衡 (Fairshare)
```

如果资源不够，按这个顺序尝试：
```
Consolidation (紧凑化)
  → Reclaim (从其他 Queue 回收)
    → Preempt (同一 Queue 内抢占)
```

**ComputeHub 现状**: 任务只是简单 FCFS + 节点权重
**可吸收**: 引入 PriorityClass + 公平调度算法

### 2.3 时间片公平调度

```
每个调度周期 = Plan (e.g., 5s)
  每个 Workload 获得 = Lease (e.g., 250ms × 权重)
  ┌─────────────────────────────────────┐
  │ Workload A: ████████░░░░░░░░ 50%   │
  │ Workload B: ████░░░░░░░░░░░░ 25%   │
  │ Workload C: ████████░░░░░░░░ 50%   │  ← 借用空闲
  └─────────────────────────────────────┘
```

两种模式：
- **Strict**: 精确分配计算时间
- **Fair**: 保证最低，空闲可借用

---

## 三、GPU 资源优化精华

### 3.1 GPU 分片 (Fractions)

核心思想：**不整个 GPU 分配，按需切分内存**

```
┌──────────────────────────────┐
│         GPU (80GB H100)       │
│  ┌────────┬────────┬────────┐ │
│  │Wkld A  │Wkld B  │ 空闲   │ │
│  │ 20GB   │ 30GB   │ 30GB   │ │
│  │ 0.25   │ 0.375  │        │ │
│  └────────┴────────┴────────┘ │
│  ← 时间片轮转 → A→B→空闲→A→B │
└──────────────────────────────┘
```

- **Request** (保证): 最小内存需求
- **Limit** (弹性的): 最高可用内存
- 内核自动 OOM Kill 超限任务

### 3.2 动态分片 (Dynamic Fractions)

更精妙：**Request < Limit**，空闲时借用多余资源

```
Workload A 申请 0.25，Limit 0.80
────────────────────────────────
正常: ████████░░░░░░░░░░░░ 占 0.25
峰值: ████████████████████ 占 0.80
空闲: ░░░░░░░░░░░░░░░░░░░░ 退回给别人
```

### 3.3 时间片 (Time-Slicing)

GPU 计算时间切分，类似 CPU 时间片：

```
Plan (5s)
├── Lease A: 2.5s (gpu-fraction=0.5)
├── Lease B: 1.25s (gpu-fraction=0.25)
└── Lease C: 1.25s (gpu-fraction=0.25)
```

**ComputeHub 现状**: GPU 信息只展示，不分片
**可吸收**: 这是最值得做的 feature — 允许 1 张 GPU 跑多个任务

---

## 四、Workload 管理精华

### 4.1 Workload 生命周期

```
Submit → Queued → Scheduled → Running → Completed/Failed
                         ↓
                  如果资源不够
              Pending → 等待重试
```

### 4.2 Workload 定义

Run:ai 的 Workload = 4 要素：
1. **容器镜像** — 应用 + 依赖 + 环境
2. **计算资源** — CPU/GPU/内存需求
3. **数据存储** — 数据集/模型/存储配置
4. **凭据** — 数据源/外部服务的认证

### 4.3 任务类型

| 类型 | 场景 | 调度特性 |
|------|------|---------|
| Workspace | Jupyter/IDE 开发 | 长运行，可暂停 |
| Training | 分布式训练 | Gang scheduling，自动扩缩 |
| Inference | 模型推理服务 | 多副本，负载均衡 |

---

## 五、权限与多租户精华

### 5.1 层级结构

```
Organization
  └── Department
       └── Project
            └── Workload (提交者)
```

每一层都有：
- **Quota** — 保证的资源
- **Over Quota Weight** — 抢空闲资源的权重
- **Rank** — 优先级（同一层内）

### 5.2 公平分配算法

```python
# 简化版 Fairshare 计算（Run:ai 风格）
project_over_quota = (project_weight / sum_all_weights) * unused_resources
fairshare = project_quota + project_over_quota

# 实际分配 = min(fairshare, workload_request)
effective_allocation = min(fairshare, total_requested)
```

如果 A 请求 15 GPU，B 只请求 5 GPU，而两者 fairshare 都是 10：
→ A 拿到 15（B 不用的也被 A 用了）
→ 下个周期 A 只有 5 的 fairshare

---

## 六、ComputeHub 可以立即吸收的点

### P0 — 最有价值

1. **GPU 分片 (Fraction)** — 让多个任务共享 1 张 GPU
   - 实现: Docker 里限制 `NVIDIA_VISIBLE_DEVICES` + `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE`
   - 或者: 容器级 cgroup 限制

2. **Workload Type 接口** — 解耦"任务执行器"和"调度器"
   - 定义接口: `type WorkloadRunner interface { Run(ctx, spec) -> Result }`
   - 内置: ShellRunner, DockerRunner

### P1 — 重要

3. **优先级 + 抢占** — 高优任务可以抢低优资源
   - 实现: PriorityClass (1-100) + Preempt 布尔
   - Worker 收到新任务时，判断是否需要 kill 低优任务

4. **Bin-Pack / Spread 策略** — TUI 可切换
   - Bin-Pack: 尽量挤在同一节点（省功耗）
   - Spread: 分散到不同节点（容错）

### P2 — 锦上添花

5. **时间片公平调度** — 多任务共享 GPU 时的计算时间分配
   - 不急着做，等有真实多租户场景再上

6. **多租户层级** — Department/Project 的配额管理
   - 等有多个用户再考虑

---

## 七、Run:ai 的弱点（我们的机会）

| Run:ai 的短板 | ComputeHub 的优势 |
|--------------|------------------|
| **K8s 依赖** — 部署复杂，学习曲线陡 | **零依赖** — 单二进制 |
| **重** — 至少 3-5 节点 K8s 集群 | **轻** — 5MB 跑在平板上 |
| **闭源** — 被 NVIDIA 收购后更封闭 | **开源** — 社区驱动 |
| **贵** — 企业授权 | **免费** — 社区版永久免费 |
| **Web 管理** — 必须有浏览器 | **TUI** — SSH 就能管 |
| **不适合小团队** — 为数据中心设计 | **适合个人/小团队** — 5 分钟上手 |

---

## 八、总结

```
Run:ai = 企业级 GPU 基础设施（重、贵、全）
ComputeHub = 轻量级 GPU 集群管理（轻、简、小）

我们的策略：
  做 Run:ai 不做的：
    ✅ 无 K8s
    ✅ TUI 终端体验
    ✅ 超轻部署

  学 Run:ai 做得好的：
    🔄 GPU 分片 (最值钱的功能)
    🔄 公平调度算法
    🔄 优先级/抢占机制

  差异化定位：
    "个人开发者的 GPU 集群"
    "从 1 张卡到 100 张卡的平滑扩展"
    "一个二进制搞定一切"
```

---

*下次功能迭代建议：先做 GPU 分片 + Workload Type 接口，这两个是最能拉开差距的。*
