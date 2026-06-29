# 跨节点 Agent 通讯标准流程

**验证时间**: 2026-06-24 11:20-11:29
**验证者**: 端智 (local-arm) → 达智 (wanlida-ubuntu)
**状态**: ✅ 验证通过，已同步到集群共享记忆

---

## 背景

端智（local-arm，红米手机）通过 ComputeHub Gateway 成功向达智（wanlida-ubuntu，Intel Celeron J6412/4C/15GB）派发任务并获取结果。

## 两种派发方式

### 方式一：Shell 命令任务（直接执行）

- **API**: `POST /api/v1/tasks/submit`
- **参数**: `node_id=wanlida-ubuntu`, `command="uname -a"`, `timeout=30`
- **适用**: 纯 shell 命令，不需要 Agent 思考
- **结果**: 通过 `GET /api/v1/tasks/detail?task_id=xxx` 拉取

### 方式二：Agent Think（自然语言任务）

- **API**: `POST /api/v1/tasks/submit`
- **参数**: `node_id=wanlida-ubuntu`, `command="curl -s -X POST http://localhost:8383/api/v1/worker/think -H 'Content-Type: application/json' -d '{\"task\":\"你的自然语言指令\"}'"`, `timeout=60`
- **适用**: 需要 Agent 理解自然语言、调用工具、返回结构化结果
- **注意**: 引号嵌套需转义，建议用单引号包裹 JSON

## 验证结果

- 任务提交: ✅ success (task_id 返回)
- 任务执行: ✅ completed (exit_code=0)
- Agent 思考: ✅ 达智收到自然语言任务，调用 self_diagnose 工具
- 结果返回: ✅ stdout 包含 Agent 回复

## 关键要点

1. Gateway 的 `/api/v1/agent/think` 只支持本地 Agent（ECS 上的 ecs-p2ph）
2. 远程节点 Agent 需通过 shell 任务中转：提交 curl 到远程节点的 `localhost:8383/api/v1/worker/think`
3. Worker Agent 默认端口 8383，支持自然语言对话
4. 任务超时建议 ≥30s（Agent 思考需要时间）
5. 所有通讯必须通过 ComputeHub Gateway（老大铁律），禁止 SSH/Tailscale/VNC/RDP 等非 ComputeHub 通道

## 集群广播机制

- `POST /api/v1/cluster/broadcast` 可广播消息到所有在线 Worker
- Worker 通过 `/api/v1/worker/think` 接收广播
- 广播格式: `arc_net_broadcast` 信封

## 测试命令（已验证）

```bash
# 提交 shell 任务
curl -X POST http://<gateway>:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{"node_id":"wanlida-ubuntu","command":"hostname","timeout":30}'

# 提交 Agent think 任务
curl -X POST http://<gateway>:8282/api/v1/tasks/submit \
  -H 'Content-Type: application/json' \
  -d '{"node_id":"wanlida-ubuntu","command":"curl -s -X POST http://localhost:8383/api/v1/worker/think -H \"Content-Type: application/json\" -d \"{\\\"task\\\":\\\"你好！请告诉我你的系统状态\\\"}\"","timeout":60}'

# 拉取结果
curl -s 'http://<gateway>:8282/api/v1/tasks/detail?task_id=<task_id>'
```

## 节点信息

- **wanlida-ubuntu**: 112.48.4.56, linux/amd64, v1.3.44, Agent: 达智
- **达智 Agent**: OpenClaw 2026.3.13, 模型 zhangtuo/qwen3.6-35b
- **达智能力**: shell/python/code/research/file
- **达智硬件**: Intel Celeron J6412 / 4核 / 15GB RAM
- **达智状态**: online，已加入银河计划大厅
