# CLU-STM-001: 集群跨 Agent 通信标准流程

> 建立时间: 2026-06-20  
> 版本: v1.0  
> 适用场景: 跨节点 OpenClaw Agent 间自主通信与协作  
> 技术验证: 端智(main, 本机) ↔ 小智(arm, ECS) 双向通信确认  
> 文档作者: 端智

---

## 1. 架构概览

```
┌─────────────────┐         ┌─────────────────────────────────┐
│   端智 (main)    │◄───────►│  小智 (arm) / win / mi         │
│  本机 Termux     │  cross- │  ECS / Windows / 其他节点      │
│  18789 Gateway   │  agent  │  各自 Gateway                  │
│  PID: 15572/15699│  session│   Agent 主 session             │
└──────┬───────────┘         └──────────┬──────────────────────┘
       │                                │
       ▼                                ▼
  ComputeHub Gateway              ComputeHub Gateway
  8282 (本机已停)                 8282 (ECS 运行中)
```

## 2. 前置条件：跨 Agent 通信配置

### 2.1 本机 openclaw.json 配置

向 `~/.openclaw/openclaw.json` 的 `tools` 段添加以下内容：

```json
"tools": {
    "profile": "coding",
    "sessions": {
      "visibility": "all"
    },
    "agentToAgent": {
      "enabled": true
    }
}
```

### 2.2 各节点配置同步

| 节点 | tools.sessions.visibility | tools.agentToAgent.enabled | 状态 |
|------|--------------------------|---------------------------|------|
| main (本机) | `all` | `true` | ✅ 已配 |
| arm (ECS) | `all` | `true` | ✅ 已配 |
| win | 待确认 | 待确认 | ⏳ |
| mi | 待确认 | 待确认 | ⏳ |

### 2.3 修改后必须重启 Gateway

```bash
openclaw gateway restart
# 或用两段式：
openclaw gateway stop && sleep 2 && openclaw gateway start
# 验证旧 PID 消失、新 PID 出现：
pgrep -f "openclaw.gateway"
```

## 3. 通信流程

### 3.1 发现目标 Agent 的 sessionKey

```bash
# 查看所有 agent 列表
ls ~/.openclaw/agents/

# 找到目标 agent 的主 session key
cat ~/.openclaw/agents/<agent_name>/sessions/sessions.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
for s in d:
    info = d[s]
    if info.get('label','') == '<agent_name>:main':
        print(f'sessionKey: agent:<agent_name>:session:{s}')
        print(f'  lastChannel: {info.get(\"lastChannel\")}')
        print(f'  updatedAt: {info.get(\"updatedAt\")}')
"
```

常用 sessionKey 示例：
- arm agent: `agent:arm:session:agent:arm:main`
- win agent: `agent:win:session:agent:win:main`
- mi agent: `agent:mi:session:agent:mi:main`

### 3.2 发送消息（本机→远端）

OpenClaw API 的 `sessions_send` 方法：

```python
sessions_send(
    sessionKey="agent:arm:session:agent:arm:main",
    message="你好，收到请回复",
    timeoutSeconds=30
)
```

返回值：
```json
{
  "status": "ok",
  "reply": "ON_LINE ✅ 收到",
  "sessionKey": "agent:arm:session:agent:arm:main"
}
```

### 3.3 远端 Agent 回复消息

远端 Agent 收到消息后自动处理，通过 OpenClaw Gateway 路由回信。无需额外配置。

### 3.4 双向验证标准

```text
流程：
  ① 本机 → 远端: "收到请回复 ON_LINE"
  ② 远端 ↔ 本机: 回复 ON_LINE ✅
  ③ 远端 → 本机: 发起一条主动消息
  ④ 本机收到: 确认双向通道
```

**通过标准**：双方各自成功收/发至少一条消息。

## 4. 集群健康检查标准

### 4.1 三端检查清单

| 序号 | 检查项 | 方法 | 通过标准 |
|------|--------|------|----------|
| 1 | 本机 Gateway | `curl http://127.0.0.1:18789/` | HTTP 200 |
| 2 | ECS Gateway | SSH → `curl http://127.0.0.1:8282/` | 响应非超时 |
| 3 | ECS systemd | `systemctl is-active computehub-gateway computehub-worker` | active / active |
| 4 | Windows Agent | ComputeHub submit `echo OK` | exit=0 |
| 5 | 磁盘 | `df -h /` | 剩余 ≥ 20% |
| 6 | 负载 | `uptime` | load average 正常区间 |

### 4.2 自动化检查脚本

```bash
# 一键检查脚本路径：
# /root/.openclaw/workspace/scripts/gateway_health.py
# 保存报告到：
# /root/.openclaw/workspace/reports/daily/gateway_health_YYYY-MM-DD.json

python3 /root/.openclaw/workspace/scripts/gateway_health.py
```

### 4.3 节点操作前置检查（WIN-OPC-001）

详见 `memory/topics/执行规则/WIN-OPC-001_Windows远程操作标准流程.md`

核心要点：
1. 先 `echo OK` 确认节点真在线
2. 简单命令直接提交，复杂操作走 WIN-CMD-001 (base64+certutil+node)
3. 通过 `cmd /C` 包裹来执行 cmd.exe 原生命令（防 PowerShell 别名问题）

## 5. 双 Agent 协作开发标准

### 5.1 分工模型

```
端智 (main) → 前端 / UI / 交互层
小智 (arm) → 后端 / 服务层 / 基础设施
win        → Windows 端测试 / GPU 任务
mi         → 调度 / 负载均衡
```

### 5.2 代码同步

```bash
# 前端文件（本机 → ECS）
scp -i ~/.ssh/id_ed25519_computehub -P 8022 \
    /path/to/frontend.html \
    computehub@36.250.122.43:/home/computehub/game_collab/

# 后端文件（ECS → 本机 或 远端编译）
# 优先在 ECS 编译运行，前端通过 SSH 隧道或公网暴露
```

### 5.3 成果产出

| 产出物 | 作者 | 技术栈 | 位置 |
|--------|------|--------|------|
| snake.html | 端智(main) | HTML+CSS+JS | ECS:~/game_collab/ |
| server.go | 小智(arm) | Go + embed | ECS:~/game_collab/ |
| game_server | 编译 | Go binary | ECS:~/game_collab/ |

### 5.4 验证流程

```bash
# HTTP 可达性
curl -s -o /dev/null -w "HTTP %{http_code} (%{size_download} bytes)" http://localhost:8080/

# 进程确认
ps aux | grep game_server | grep -v grep

# 端口确认
ss -tlnp | grep 8080

# 文件完整性
ls -la ~/game_collab/
```

## 6. 故障预案

### ❌ Q1: `sessions_send` 返回 "forbidden"

**根因**: `tools.sessions.visibility` 未设为 `all`  
**修复**:
```json
"tools": {
    "sessions": {
        "visibility": "all"
    }
}
```
**注意**: 修改后必须重启 Gateway

### ❌ Q2: `openclaw agent --message` 卡死超时

**根因**: 目标 agent 不在主动运行状态（cron/心跳任务不处理外部消息）  
**解决**: 使用 `sessions_send` API 直接发到目标 session，不走 CLI CLI

### ❌ Q3: ECS Gateway 响应 503

**根因**: OpenClaw UI assets 未构建  
**影响**: 仅 Dashboard 不可用，跨 agent 通信不受影响  
**修复**: `openclaw gateway:ui:build`（可选，非阻塞）

### ❌ Q4: SSH 执行 nohup 进程随会话退出

**根因**: SSH 父进程退出时 SIGHUP 传播到子进程  
**修复**: 用 `setsid` 启动：
```bash
setsid ./game_server > server.log 2>&1 &
```

---

## 7. 安全与权限

- `sessions.visibility = all` 允许跨 Agent 读取/写入 session
- `agentToAgent.enabled = true` 允许 Agent 间自主路由消息
- 本配置仅在受信任的内网/集群内使用，外网需谨慎
- Gateway 已配置 token 认证和 `gateway.nodes.denyCommands` 限制

---

## 8. 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-20 | v1.0 | 初版：基于端智↔小智双向通信实战建立 |