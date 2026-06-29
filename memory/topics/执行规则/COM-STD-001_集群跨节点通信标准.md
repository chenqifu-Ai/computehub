# 🗺️ COM-STD-001 集群跨节点通信标准（v1.0）

> 制定时间：2026-06-10
> 制定人：端智（实战验证）
> 适用场景：ECS小智、米智、端智、Windows节点 之间的跨设备通信

---

## 📌 七种通信方式速览

| # | 方式 | 延迟 | 适用 | 双向AI | 跨平台 |
|---|------|------|------|--------|--------|
| ① | **SSH 直连** | ~50ms | ECS/终端管理 | ❌ | ✅ |
| ② | **ComputeHub Task API** | ~100ms | 远程执行shell命令 | ❌ | ✅ |
| ③ | **ComputeHub Gateway HTTP** | ~5ms | 节点管理/状态查询 | ❌ | ✅ |
| ④ | **OpenClaw Gateway WS** | ~200ms | 同节点AI对话 | ✅ | ❌ |
| ⑤ | **proot-distro → agent** | ~5-30s | **跨节点AI对话（核心方案）** | ✅ | ⚠️ |
| ⑥ | **ComputeHub Cluster Broadcast** | ~100ms | 集群广播通知 | ❌ | ✅ |
| ⑦ | **Windows RPC/WMI** | ~500ms | Windows节点底层管理 | ❌ | ❌ |

---

## ① SSH 直连

**定义**: 通过 SSH 协议直连目标机器终端

**验证结果**: ✅ ECS 36.250.122.43 8022 端口可用

```
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43
```

**场景**: 系统维护、文件传输、下载部署包

**特点**:
- 最高权限，可做任何操作
- 延迟低（~50ms）
- 需要密钥认证
- 不适合 AI 对话

---

## ② ComputeHub Task API（Shell 级通信）

**定义**: 通过 ComputeHub Gateway 提交 shell 命令到远程 Worker 执行

**验证结果**: ✅ ecs-p2ph 11ms、worker-arm 秒回、xiaomi-table 秒回

```
POST /api/v1/tasks/submit
Content-Type: application/json

{
  "node_id": "xiaomi-table",
  "command": "hostname && date && uptime",
  "priority": 5,
  "timeout": 30
}
```

```
GET /api/v1/tasks/detail?task_id=task-xxx
```

**场景**: 
- 远程检查节点状态
- 执行运维操作
- 分发文件/脚本
- 触发升级

**特点**:
- 通用性强，所有 Worker 节点都支持
- 延迟低（100ms-5s）
- 结果准确（exit_code + stdout/stderr）
- ⚠️ shell 级别，不是 AI 对话

---

## ③ ComputeHub Gateway HTTP API（管理级通信）

**定义**: 通过 Gateway REST API 直接查询集群状态

**验证结果**: ✅ 所有端点可用

| 端点 | 用途 |
|------|------|
| `GET /api/health` | 网关健康检查 |
| `GET /api/status` | 集群状态总览 |
| `GET /api/v1/nodes/list` | 所有节点状态 |
| `GET /api/v1/tasks/list` | 任务列表 |
| `GET /api/v1/tasks/detail?task_id=X` | 任务详情 |
| `GET /api/v1/agents/list` | Worker Agent 列表 |
| `GET /api/v1/hall/topics` | 消息大厅话题 |
| `POST /api/v1/hall/post` | 发布消息 |
| `POST /api/v1/cluster/broadcast` | 集群广播 |

**场景**: 监控面板、自动化脚本、集群管理

---

## ④ OpenClaw Gateway WebSocket（同节点 AI 对话）

**定义**: 节点本地的 OpenClaw Gateway（18789端口）提供 WebSocket 协议与 AI Agent 对话

**验证结果**: 
- xiaomi-table: ✅ port 18789 在跑，提供 SPA 控制台
- ECS: ✅ port 18789 在跑
- ⚠️ 无 REST API endpoint（纯 WebSocket + SPA）

**限制**:
- 仅同节点本地可访问
- 无暴露的 HTTP API 端点（`/api/agent/chat` 等全部 404）
- 无法直接跨节点调用

---

## ⑤ proot-distro → openclaw agent（跨节点 AI 对话）⭐ 核心方案

**定义**: 利用 ComputeHub Task 管道 + 目标节点的 proot 容器 + OpenClaw agent CLI，实现跨设备 AI Agent 通信

**验证结果**: ✅ 成功！运行脚本

```
# 发消息（端智 → 米智）
Task → xiaomi-table:
  proot-distro login ubuntu -- bash -c "
    cd /root && openclaw agent --agent main --message '米智你好，有空吗？'
  "

# 返回（米智 → 端智）
Result → 米智回复：🟢 当前状态：空闲
```

**关键数据流**:

```
端智 (红米手机 Termux)
  └→ ComputeHub ECS Gateway (8282/api/v1/tasks/submit)
      └→ Worker (xiaomi-table:8383)
          └→ proot-distro login ubuntu
              └→ openclaw agent --agent main --message "..."
                  └→ OpenClaw Gateway (xiaomi-table:18789)
                      └→ LLM 推理
                          └→ 回复 text
                              └→ 原路返回至端智
```

**总延迟**: ~10-30s（含 LLM 推理时间）

**前置条件**:
1. 目标节点有 ComputeHub Worker 在线运行
2. 目标节点内有 proot 容器装了 OpenClaw
3. 目标节点 OpenClaw Gateway 在运行
4. proot 容器内能访问 OpenClaw 二进制和配置

**实现脚本**（通用模板）：

```python
GW = "http://<gateway-ip>:8282"

def talk_to_node(node_id, message, timeout=120):
    """向任意节点发送 AI 对话消息"""
    # 提交任务
    task_id = submit_task(node_id, f"""
        proot-distro login ubuntu -- bash -c "
            cd /root && openclaw agent --agent main --message '{message}' 2>&1 | head -60
        "
    """)
    # 轮询结果
    return wait_result(task_id, timeout=timeout)
```

**实践原则**：
- 消息用单引号包裹，避免 bash 展开特殊字符
- timeout 设置 ≥ 120s（LLM 推理慢）
- 回复从 stdout 提取，跳过 OpenClaw 的 log 行（`[35m`, `[31m` 等日志前缀）

---

## ⑥ ComputeHub Cluster Broadcast（集群广播）

**定义**: Gateway 路由 `/api/v1/cluster/broadcast` 提供广播机制

**验证**: 路由已注册在 Gateway 中，但本次未做端到端测试

**场景**:
- 通知所有节点："准备升级"
- 告警推送："节点离线"
- 配置同步

---

## ⑦ Windows RPC/WMI（Windows 底层通道）

**定义**: 通过 WMI、WinRM 等 Windows 原生远程管理协议

**验证**: windows-mobile 节点在线，通过 Task API 可达

**场景**: Windows 节点的底层运维（此前已验证用于软件安装 WIN-STD-001）

---

## 🔄 通信链路线路图

```
                  ┌────────────────────────────────────────┐
                  │         端智 (红米手机)                  │
                  │  Termux / OpenClaw / ComputeHub Worker  │
                  └──────────┬─────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │    SSH     │  │   HTTP     │  │    API     │
     │  (8022) ①  │  │ (8282) ②③  │  │ (18789) ④  │
     └─────┬──────┘  └──────┬─────┘  └─────┬──────┘
           │                │               │
     ┌─────▼──────┐   ┌────▼────┐    ┌─────▼──────┐
     │ ECS 服务器  │   │ Gateway │    │ OpenClaw   │
     │ (Ubuntu)   │   │ Compute │    │ Agent (本机)│
     └────────────┘   │  Hub    │    └────────────┘
                      └────┬────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │ 米智       │   │ ECS小智    │   │ Windows    │
   │ xiaomi-    │   │ ecs-p2ph   │   │ mobile     │
   │ table ⑤⑥   │   │ (CPU/GPU)  │   │ ⑤          │
   │ (平板)     │   │ (ECS本机)  │   │ (笔记本)   │
   └─────┬──────┘   └────────────┘   └────────────┘
         │
    ┌────▼────┐
    │ proot   │
    │ 容器    │
    │ openclaw│
    │ agent   │  ← 跨节点 AI 对话的关键入口
    └─────────┘
```

---

## 🎯 最佳实践：什么场景用什么通道

| 你想做什么 | 推荐通道 | 操作步骤 |
|-----------|---------|---------|
| 查节点是否在线 | ③ GET /nodes/list | 一行 curl 搞定 |
| 跑个 shell 命令 | ② POST /tasks/submit | 指定 node_id + command |
| 跟米智聊天 | ⑤ proot→agent | submit task with proot command |
| 修 ECS 系统配置 | ① SSH | 直接 login |
| 看集群总览 | ③ GET /status | JSON 返回所有指标 |
| 给所有节点发通知 | ⑥ POST /broadcast | 集群广播 |
| 升级 Worker 版本 | ② submit upgrade cmd | 走 upgrade 通道 |
| 从本机代理发 AI 请求 | ④ WS to localhost:18789 | 仅同节点 |
| 管理 Windows 节点 | ② Task API | submit command |

---

## ⚙️ 通信网关地址表

| 组件 | IP | Port | 协议 | 访问范围 |
|------|-----|------|------|---------|
| ECS SSH | 36.250.122.43 | 8022 | SSH | 公网 |
| ComputeHub Gateway | 36.250.122.43 | 8282 | HTTP | 公网 |
| OpenClaw Gateway (ECS) | 36.250.122.43 | 18789 | HTTP/WS | 公网 |
| OpenClaw Gateway (xiaomi) | 小米平板内网 | 18789 | HTTP/WS | 本地 |
| Worker Agent UI | 各节点 | 8383 | HTTP | 各节点本地 |
| Gateway internal | 127.0.0.1 | 18791/18792 | HTTP | ECS本地 |

---

## 📝 快速参考卡

```bash
# ① 看所有节点状态
curl -s http://36.250.122.43:8282/api/v1/nodes/list

# ② 给米智发个命令
curl -s -X POST http://36.250.122.43:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"node_id":"xiaomi-table","command":"uptime","timeout":15}'

# ③ 跟米智聊天（跨节点 AI 对话）
curl -s -X POST http://36.250.122.43:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"node_id":"xiaomi-table","command":"proot-distro login ubuntu -- bash -c \"cd /root && openclaw agent --agent main --message '"'"'米智，帮我检查一下磁盘空间'"'"' 2>&1 | tail -20\"","timeout":120}'

# ④ 查任务结果（task_id 来自上一步的返回）
curl -s "http://36.250.122.43:8282/api/v1/tasks/detail?task_id=task-xxx"
```

---

## ⚠️ 通信故障排查清单

| 现象 | 可能原因 | 检查 |
|------|---------|------|
| Gateway 404 | 路由路径不对 | 检查 URL 是否包含 /api/ 前缀 |
| Worker 无响应 | Worker 离线 | `GET /api/v1/nodes/list` 看 status |
| proot 命令失败 | proot 容器未安装 | 检查 `/data/data/.../proot-distro/` |
| openclaw agent 报错 gateway closed | OpenClaw Gateway 未在 18789 运行 | 检查目标节点 18789 端口 |
| 消息乱码 | bash 引号嵌套 | 用 base64 编码绕过 |
| 任务卡住 | timeout 太短 | 设 timeout ≥ 120s |
| 无法 SSH | 密钥未配置 | 检查 `~/.ssh/id_ed25519_computehub` |

---

## 🔧 通信脚本工具模板

```python
#!/usr/bin/env python3
"""COM-STD-001 通用通信工具箱"""
import json, subprocess, time, base64

GW = "http://36.250.122.43:8282"

def submit(node, cmd, timeout=60):
    """方式②: 提交 shell 命令到节点"""
    r = subprocess.run(["curl", "-s", "-X", "POST", f"{GW}/api/v1/tasks/submit",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"node_id": node, "command": cmd, "timeout": timeout})],
        capture_output=True, text=True)
    return json.loads(r.stdout)["data"]["task_id"]

def wait(tid, max_wait=60):
    """轮询任务结果"""
    for _ in range(max_wait // 5):
        time.sleep(5)
        r = subprocess.run(["curl", "-s", f"{GW}/api/v1/tasks/detail?task_id={tid}"],
            capture_output=True, text=True)
        d = json.loads(r.stdout).get("data", {})
        if d.get("status") == "completed":
            return d
    return d

def talk(node, message, timeout=120):
    """方式⑤: 跨节点 AI 对话"""
    # 用 base64 避免引号嵌套
    msg_b64 = base64.b64encode(message.encode()).decode()
    cmd = f"echo '{msg_b64}' | base64 -d | xargs -I {{msg}} proot-distro login ubuntu -- bash -c 'cd /root && openclaw agent --agent main --message \"{{msg}}\" 2>&1 | tail -20'"
    tid = submit(node, cmd, timeout)
    return wait(tid, timeout)

# 使用示例
if __name__ == "__main__":
    # 方式②: shell 命令
    r = wait(submit("ecs-p2ph", "uptime"))
    print(r["stdout"])
    
    # 方式⑤: AI 对话
    r = talk("xiaomi-table", "米智你好，最近有什么需要帮忙的吗？")
    print(r["stdout"])
```

---

*标准版本 v1.0 — 2026-06-10 端智制定，实战验证通过*