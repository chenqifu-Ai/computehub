# 🚀 ComputeHub: Gemma-4-31B 专项执行计划 (Detailed Implementation Plan)

## 1. 计划愿景
在 `gemma-4-31b-plan` 分支中，将 ComputeHub 的工程灵魂（绝对确定性、物理真实）具象化。本计划旨在构建一个能够承载像 Gemma-4-31B 这种量级模型的高可靠分布式算力调度闭环，确保从任务提交到物理交付的每一个环节都可审计、可验证。

---

## 2. 详细执行分解 (Work Breakdown Structure)

### 🏗️ 第一阶段：确定性基础设施 (The Deterministic Base)
**目标**：消除所有模糊接口，建立物理级的节点感知。

#### 2.1 绝对边界 API 网关 (`api/rest_api.py`)
- [ ] **状态机请求处理器**：实现一个 `RequestStateMachine` 类，所有 API 请求必须经过 $\text{Received} \to \text{Validated} \to \text{Dispatched} \to \text{Acked}$ 流程。
- [ ] **严格权限校验层**：实现基于 JWT + 硬件指纹的双重认证，确保请求来源绝对可信。
- [ ] **确定性响应格式**：定义统一的 `StandardResponse` 协议，禁止返回模糊的错误信息。

#### 2.2 物理心跳监控系统 (`node/monitor.py`)
- [ ] **深层硬件采集**：集成 `nvidia-smi` 和 `psutil`，采集：
    - GPU 核心温度 $\to$ 预测硬件失效风险。
    - 显存实时碎片率 $\to$ 决定是否能加载 31B 模型。
    - 物理网络抖动 (Jitter) $\to$ 评估分布式训练同步延迟。
- [ ] **物理状态快照**：每 50ms 生成一次硬件状态哈希，作为计费的物理凭证。

---

### 🧠 第二阶段：鲁棒性调度引擎 (The Robust Scheduler)
**目标**：实现针对大模型（如 31B）的精准算力匹配与防御性调度。

#### 2.1 31B 模型适配调度 (`scheduler/scheduler.py`)
- [ ] **显存拓扑感知**：实现 $\text{VRAM-Aware}$ 调度，自动计算 31B 模型（FP16/INT8/INT4）所需的物理显存，匹配最优节点组合。
- [ ] **L3 物理延迟匹配**：通过测算 $\text{Gateway} \leftrightarrow \text{Node}$ 的真实 RTT，优先选择低延迟集群以降低推理时延。

#### 2.2 防御性调度逻辑 (`scheduler/defense.py`)
- [ ] **区域熔断机制**：当某个数据中心节点失效率 $\ge 30\%$ 时，自动将该区域标记为 $\text{Degraded}$ 并切断新任务路由。
- [ ] **任务状态转移机** (`state_machine.py`)：
    - $\text{Pending} \to \text{Allocated} \to \text{Executing} \to \text{Verifying} \to \text{Completed}$。
    - 任何非预期转移直接触发 $\text{Sentry}$ 警报并执行任务回滚。

---

### 🛡️ 第三阶段：物理真实验证层 (Physical Truth Verification)
**目标**：确保交付的结果不是“伪造”的，而是真实物理计算的产出。

#### 3.1 双节点冗余校验 (`validation/verifier.py`)
- [ ] **交叉验证机制**：关键推理任务在两个独立物理节点并行运行，对比输出 Token 的 $\text{Cosine Similarity}$。
- [ ] **不一致处理**：若结果不一致，自动触发第三节点仲裁或标记该节点为 $\text{Untrusted}$。

#### 3.2 真实算力计费 (`blockchain/settlement.py`)
- [ ] **利用率扣费模型**：基于 `node.log` 中的 $\text{GPU-Util}$ 曲线积分计算实际功耗，剔除加载模型和等待 I/O 的空转时间。
- [ ] **物理交付凭证 (Proof of Compute)**：任务完成时，节点必须提交 $\text{Hardware Snapshot} + \text{Task Hash}$ 作为结算凭证。

---

### ⚡ 第四阶段：极致性能链路 (Ruthless Efficiency)
**目标**：消除所有中间冗余，追求端到端极速响应。

#### 4.1 gRPC 高速通道 (`api/grpc_server.py`)
- [ ] **双向流通信**：实现 $\text{Gateway} \leftrightarrow \text{Node}$ 的双向流，将心跳和状态更新延迟压低至 $\le 50\text{ms}$。
- [ ] **Protobuf 定义**：定义极致精简的二进制传输协议，减少序列化开销。

#### 4.2 可视化物理地图 (`web/dashboard.html`)
- [ ] **实时流量热力图**：基于物理经纬度展示全球算力分布、任务流动方向及当前负载压力。

---

## 3. 关键里程碑 (Milestones)

| 阶段 | 交付物 | 核心指标 | 预计状态 |
| :--- | :--- | :--- | :--- |
| **M1** | 确定性 API + 物理心跳 | 心跳响应 $\le 100\text{ms}$ | 待启动 |
| **M2** | 31B 适配调度 + 状态机 | 状态转移准确率 $100\%$ | 待启动 |
| **M3** | 冗余验证 + 物理计费 | 验证覆盖率 $\ge 90\%$ | 待启动 |
| **M4** | gRPC 通道 + 物理地图 | 端到端延迟降低 $40\%$ | 待启动 |

---

## 4. 风险预警
- **硬件异构性**：不同品牌的 GPU 采集接口不统一 $\to$ 需建立 $\text{Hardware-Abstraction-Layer (HAL)}$。
- **网络分区**：全球部署易出现网络分区 $\to$ 需实现 $\text{Eventual Consistency}$ 状态同步。
