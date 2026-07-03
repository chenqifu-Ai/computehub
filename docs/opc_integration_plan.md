# OpenClaw + OPC 分布式智能体集群方案

**日期**: 2026-05-26
**状态**: 方案设计 + 核心对接已完成
**作者**: 小智 (OpenClaw Agent)

---

## 一、现状

### 已有组件

| 组件 | 状态 | 说明 |
|------|------|------|
| OpenClaw Gateway | ✅ 运行中 | port 18789, 本机 ECS |
| OPC Gateway | ✅ 运行中 | port 8282, 36.250.122.43 |
| OPC Worker (ecs-p2ph) | ✅ 已注册 | 本机 Linux 节点 |
| OPC Worker (Windows-mobile-01) | ✅ 已注册 | Windows 10 节点 |
| OPC v1.0.0 | ✅ 编译通过 | 5/5 平台全部通过 |
| OPC Bridge | ✅ 已编写 | scripts/opc_bridge.py |

### 当前集群状态

```
📊 OPC 集群
├── 节点: 2/2 在线
│   ├── ecs-p2ph (Linux, cn-east)
│   └── Windows-mobile-01 (Win10, cn-east)
├── 任务: 27 个历史任务全部完成
├── Gateway: 运行 9h+
└── Pipeline/Kernel: 正常运行
```

---

## 二、目标

构建 **OpenClaw AI 大脑 + OPC 分布式执行** 的混合集群：

```
                    ┌── OpenClaw Agent (zhangtuo-ai/qwen3.6-35b)
                    │     思考 · 拆解 · 决策 · 汇总
OpenClaw TUI ←──────┤
                    │     通过 OPC Bridge 下发任务
                    └── OPC Gateway (8282)
                          │
                          ├── 调度器 (延迟感知 + 负载均衡 + 区域熔断)
                          │
                          ├── ecs-p2ph → GPU 推理 / 视频渲染
                          ├── Windows-mobile-01 → 通用计算
                          └── [未来] 各地新节点 → 自动接入
```

**核心价值**: 1 个 AI 大脑 + N 个异构 Worker = 分布式智能体集群

---

## 三、架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│  L1: 交互层                                          │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ OpenClaw TUI 1 │  │ OpenClaw TUI 2 │ ...            │
│  │ (Master)       │  │ (Worker)       │                │
│  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  L2: AI 决策层 (OpenClaw Agent)                      │
│  ┌──────────────────────────────────────────┐        │
│  │ Task 理解 → 拆解 → 子任务列表             │        │
│  │ Decision → 调度策略 → 节点选择            │        │
│  │ 结果汇总 → 质量验证 → 最终输出            │        │
│  └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
                      │
              OPC Bridge API
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  L3: 调度层 (OPC Gateway)                            │
│  ┌────────┐ ┌────────┐ ┌──────────┐                │
│  │ 节点管理 │ │ 任务队列 │ │ 智能调度 │                │
│  │register  │ │ submit  │ │ latency  │                │
│  │heartbeat│ │ poll    │ │ weight   │                │
│  │unregister│ │ result  │ │ circuit  │                │
│  └────────┘ └────────┘ └──────────┘                │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  L4: 执行层 (各地 Worker)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Linux    │ │ Linux    │ │ Windows  │              │
│  │ 节点 1    │ │ 节点 2    │ │ 节点 3    │              │
│  │ GPU 推理  │ │ 视频渲染  │ │ 通用计算  │              │
│  └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
用户: "帮我生成 10 个视频"
  ↓
OpenClaw Agent:
  1. 理解任务 (10 个视频)
  2. 拆解为 10 个子任务
  3. 检查节点能力 → 分配到 3 个 Worker
  ↓
OPC Gateway:
  4. 提交 10 个任务到队列
  5. 调度器按延迟/负载分配
  ↓
Workers (并行):
  6. Worker1: 执行 4 个视频生成
  7. Worker2: 执行 3 个视频生成
  8. Worker3: 执行 3 个视频生成
  ↓
结果回传 → OpenClaw Agent:
  9. 汇总 10 个结果
  10. 质量验证
  11. 输出最终答案
```

---

## 四、实施步骤

### 阶段 1: 基础对接 (已完成 ✅)

- [x] OPC Gateway 运行 (port 8282)
- [x] 2 个 Worker 注册在线
- [x] 编写 OPC Bridge (opc_bridge.py)
- [x] 测试 API 连通性
- [x] OPC v1.0.0 全平台编译

### 阶段 2: Agent 对接 (进行中)

- [ ] 编写 Agent 专用 OPC SDK (Python)
- [ ] 实现 TaskComposer 集成
- [ ] 实现智能调度策略
- [ ] 实现结果聚合器

### 阶段 3: 多节点扩展

- [ ] 部署更多 Worker 节点 (GPU 服务器)
- [ ] 配置跨区域调度
- [ ] 实现 Worker 自动发现
- [ ] 实现 Worker 自升级机制

### 阶段 4: 生产优化

- [ ] 实时监控面板 (Prometheus + Grafana)
- [ ] 任务超时/重试机制
- [ ] 成本优化 (按需调度)
- [ ] 安全隔离 (Sandbox)

---

## 五、核心代码

### 5.1 OPC Bridge (已完成)

```python
# scripts/opc_bridge.py
from opc_bridge import OPCBridge

bridge = OPCBridge()

# 查看集群状态
bridge.health()          # Gateway 健康检查
bridge.status()          # 系统状态
bridge.get_nodes()       # 节点列表

# 提交任务
bridge.submit_task("python3 train.py", node_id="gpu-01", priority=8)

# 查询结果
bridge.list_tasks()

# 视频生成
bridge.submit_video("image", {"image_path": "/data/photo.jpg"})
```

### 5.2 Agent 集成示例 (待实现)

```python
# agent_opc_plugin.py
import json
from opc_bridge import OPCBridge

class OPCAgentPlugin:
    """OpenClaw 插件: 通过 OPC 调度分布式任务"""
    
    def __init__(self):
        self.bridge = OPCBridge()
    
    def submit_distributed_task(self, original_task: str) -> str:
        """
        智能体执行分布式任务
        
        流程:
        1. LLM 拆解任务 → 子任务列表
        2. 通过 OPC 并行分发
        3. 收集结果 → LLM 汇总
        """
        # Step 1: 拆解任务
        subtasks = self._decompose_task(original_task)
        
        # Step 2: 并行分发到 Worker
        results = self._dispatch_tasks(subtasks)
        
        # Step 3: 汇总结果
        final_answer = self._compose_result(original_task, results)
        
        return final_answer
    
    def _decompose_task(self, task: str) -> list:
        """使用 LLM 将大任务拆解为子任务"""
        # 调用 OpenClaw API 拆解
        prompt = f"拆解任务: {task}"
        # ... LLM call ...
        return parsed_subtasks
    
    def _dispatch_tasks(self, subtasks: list) -> list:
        """通过 OPC 并行分发"""
        results = []
        for subtask in subtasks:
            # 选择最优节点
            node = self._select_best_node(subtask)
            # 提交任务
            result = self.bridge.submit_task(
                command=subtask["command"],
                node_id=node,
                priority=subtask["priority"]
            )
            results.append(result)
        return results
    
    def _compose_result(self, original_task, results):
        """LLM 汇总所有子任务结果"""
        # ... 汇总逻辑 ...
        pass
```

---

## 六、技术选型

| 层级 | 技术 | 选择 |
|------|------|------|
| AI 模型 | zhangtuo-ai/qwen3.6-35b | ✅ 已配置 |
| 调度协议 | OPC REST API | ✅ 已实现 |
| 任务队列 | OPC Gateway 内置 | ✅ 已实现 |
| Worker 通信 | HTTP 轮询 | ✅ 已实现 |
| 结果聚合 | OpenClaw Agent | 待实现 |
| 监控 | Prometheus | ✅ 已集成 |

---

## 七、扩展规划

### 7.1 节点扩展

```bash
# 在新节点上注册到集群
./computehub worker \
  --gw http://36.250.122.43:8282 \
  --node-id gpu-server-01 \
  --gpu-type H100 \
  --region us-west \
  --concurrent 16
```

### 7.2 跨地域调度

```python
# 区域亲和性 + 延迟感知调度
scheduler.select_node(
    affinity="cn-east",    # 优先同区域
    min_gpu_gb=16,         # 最低 GPU 显存
    max_latency_ms=50      # 最高延迟
)
```

### 7.3 自动扩缩容

```python
# 监控 GPU 利用率，自动调度
if gpu_util > 80%:
    # 触发新节点加入
    auto_scale_up()

if gpu_util < 20%:
    # 缩容释放资源
    auto_scale_down()
```

---

## 八、预期收益

| 指标 | 单机 | 集群 |
|------|------|------|
| 并发任务数 | 4 (本机) | 32+ (8 节点) |
| 推理速度 | 1x | 4-8x (并行) |
| 视频产出 | 1 个/小时 | 8 个/小时 |
| 可用性 | 单机故障 | 多节点容错 |
| 成本优化 | 固定 | 按需调度 |

---

## 九、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Worker 离线 | 任务失败 | 自动重试 + 重新调度 |
| 网络延迟 | 性能下降 | 区域亲和性调度 |
| 节点过热 | 硬件损坏 | 温度监控 + 自动降级 |
| 任务泄露 | 数据泄露 | Sandbox 隔离 |

---

## 十、总结

**已完成**: OPC 集群搭建 + API 对接 (100%)
**待做**: Agent 集成 (阶段 2)

**核心优势**:
1. 1 个 AI 大脑控制无限 Worker
2. 异构节点统一调度 (Linux/Windows/GPU/CPU)
3. 延迟感知 + 区域亲和的智能调度
4. 区域熔断 + 自动重试的容错机制

**下一步**: 确认方案 → 开始阶段 2 开发
