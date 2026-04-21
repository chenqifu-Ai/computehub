# 🚀 ComputeHub 灵魂同步执行计划 (Soul-Synced Roadmap v1.1)

## 1. 核心目标
将 ComputeHub 从一个 "文档原型" 升级为基于 **OpenClaw 工程灵魂** 的工业级分布式算力系统。

## 2. 研发路线图 (Soul-Infused Roadmap)

### 第一阶段：确定性基础架构 (Deterministic Infra)
- [ ] **绝对边界 API 网关** (`api/rest_api.py`): 
    - 实现基于状态机的请求处理。
    - 建立严格的权限校验层，确保请求边界绝对清晰。
- [ ] **物理心跳监控系统** (`node/monitor.py`): 
    - 放弃简单的 "I'm alive" 响应。
    - 实现包含 GPU 真实温度、显存利用率、网络延迟的物理状态报告。
- [ ] **确定性资源原数据库**: 存储节点的物理硬件指纹，而非简单的配置描述。

### 第二阶段：鲁棒性调度引擎 (Robust Scheduling)
- [ ] **防御性调度逻辑** (`scheduler/scheduler.py`): 
    - 实现“区域熔断”机制，当某个地理区域节点失效率 > 30% 时自动切断路由。
    - 实现基于物理延迟的 $\text{L3}$ 级最优节点匹配。
- [ ] **任务状态机** (`scheduler/state_machine.py`): 
    - 严格定义任务在全局网络中的转移路径 $\text{Pending} \rightarrow \text{Executing} \rightarrow \text{Verifying} \rightarrow \text{Completed}$。

### 第三阶段：物理真实验证层 (Physical Truth Verification)
- [ ] **双节点冗余校验** (`validation/verifier.py`): 
    - 关键任务必须在两个独立物理节点上运行，结果一致才判定为 $\text{True}$。
- [ ] **真实算力度量计费** (`blockchain/settlement.py`): 
    - 基于 `node.log` 中的物理 GPU 利用率进行扣费，剔除空转时间。
- [ ] **物理交付凭证**: 每个任务必须附带硬件执行快照作为物理凭证。

### 第四阶段：极致性能链路 (Ruthless Efficiency)
- [ ] **gRPC 高速通道**: 替换部分 REST API，实现 $\text{Gateway} \leftrightarrow \text{Node}$ 的极速通信。
- [ ] **零拷贝上下文传递**: 优化任务参数分发，减少内存拷贝开销。
- [ ] **可视化物理地图** (`web/dashboard.html`): 实时展示全球算力的物理分布与流量流动热力图。

---

## 3. 优先级执行顺序 (Immediate Soul-Sync Steps)

1. **构建确定性 API 层** $\rightarrow$ 确保每一个请求都有绝对的边界和可预测的响应。
2. **构建物理心跳节点** $\rightarrow$ 让节点开始汇报真实的物理资源状态。
3. **实现状态机调度** $\rightarrow$ 消除任务处理中的模糊状态。
4. **建立物理验证机制** $\rightarrow$ 确保交付结果是真实的物理产出。
