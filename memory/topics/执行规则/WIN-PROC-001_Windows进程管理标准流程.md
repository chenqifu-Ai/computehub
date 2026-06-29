# WIN-PROC-001: Windows ComputeHub 进程管理标准流程

> v1.0 · 建立: 2026-06-03
> 基于 windows-home-01 (LAPTOP-QOVCUVAG / 192.168.1.8) 实战总结

---

## 📋 进程拓扑速查

| 组件 | 端口 | 典型启动命令 | 热重启风险 |
|------|------|-------------|-----------|
| **Gateway** | 8282 | `computehub.exe gateway` | ✅ 无（不影响 Worker） |
| **Worker Agent** | 8383 | `computehub.exe worker --gw <ECS> --node-id <ID>` | ⚠️ 杀死后需立即重启 |
| **冗余进程** | 无 | (启动时残留) | ❌ 占内存，可清理 |

---

## 1️⃣ Gateway 重启流程

### 原理
Gateway 只提供 API + Gallery + AI 页面，重启不影响正在执行的 Worker 任务。

### 操作

```json
// Step 1: 查当前 Gateway PID
// 通过 Worker 提交（通过 ECS Gateway 中转）
{
  "command": "powershell -EncodedCommand <BASE64>",
  "assigned_node": "windows-home-01",
  "timeout": 10
}
// 编码内容: (Get-NetTCPConnection -LocalPort 8282).OwningProcess

// Step 2: 杀死 → 后台启动（& 链，一步完成）
{
  "command": "cmd /c taskkill /f /pid <PID> >nul 2>&1 & start /B D:\\computehub\\computehub.exe gateway",
  "assigned_node": "windows-home-01",
  "timeout": 10
}

// Step 3: 验证（等 3 秒）
{
  "command": "curl -s http://localhost:8282/api/v1/nodes/list",
  "assigned_node": "windows-home-01",
  "timeout": 10
}
// 预期: {"id":"","success":true,"data":[...],...}
```

---

## 2️⃣ Worker Agent 重启流程（核心）

### ⚠️ 最大风险
Worker 进程被杀死时，**当前正在执行的任务会中断**。必须用 `&` 链确保杀死后立即重启。

### 前置：查 Worker 启动命令

```json
{
  "command": "powershell -EncodedCommand <BASE64>",
  "assigned_node": "windows-home-01",
  "timeout": 10
}
// 编码内容: (Get-CimInstance Win32_Process -Filter 'ProcessId = <PID>').CommandLine
```

### 重启命令（& 链）

```
cmd /c taskkill /f /pid <PID> >nul 2>&1 & ping -n 3 127.0.0.1 >nul & start /B D:\computehub\computehub.exe worker --gw http://36.250.122.43:8282 --node-id windows-home-01 --interval 3 --concurrent 2 --heartbeat 10
```

**各段解释：**
| 段 | 作用 | 是否必需 |
|----|------|---------|
| `taskkill /f /pid <PID> >nul 2>&1` | 杀死旧 Worker | ✅ |
| `ping -n 3 127.0.0.1 >nul` | 等 3 秒保底（端口释放） | ✅ |
| `start /B D:\computehub\computehub.exe worker ...` | 后台启动新 Worker | ✅ |

**为什么用 `&` 不用 `&&`？**
- `&&`：前一条失败后续不执行 → Worker 一死任务就断
- `&`：每条独立跑 → 前一条失败不影响后面 → **即使 taskkill 出问题，start 照样跑**

### 验证

```json
// 查新 PID
{
  "command": "tasklist | findstr computehub",
  "assigned_node": "windows-home-01",
  "timeout": 10
}

// 测 Worker health
{
  "command": "curl -s http://localhost:8383/api/v1/worker/health",
  "assigned_node": "windows-home-01",
  "timeout": 10
}
// 预期: {"node_id":"windows-home-01","status":"ok"}

// 测 ECS 侧是否重新注册（等 30s 让心跳生效）
{
  "command": "curl -s http://36.250.122.43:8282/api/v1/nodes/list",
  "assigned_node": "ecs-p2ph",
  "timeout": 10
}
// 预期: node_id=windows-home-01, status=online
```

---

## 3️⃣ Base64 + PowerShell 万能转义方案

### 问题
Windows cmd、PowerShell、JSON 三层嵌套导致引号转义地狱。

### 方案：Python 端构造 Base64，PS 端解码执行

```python
import base64

def ps_encoded(cmd: str) -> str:
    """将 PowerShell 命令编码为 Base64，避免引号转义问题"""
    b64 = base64.b64encode(cmd.encode('utf-16le')).decode()
    return f"powershell -EncodedCommand {b64}"

# 用法
command = ps_encoded("Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' }")
# 输出: powershell -EncodedCommand RwBlAHQALQBOAGUAdABJAFAAQQBkAGQAcgBlAHMAcwAgAC0AQQBkAGQAcgBlAHMAcwBGAGEAbQBpAGwAeQAgAEkAUAB2ADQAIA...
```

### 常用 Base64 PS 命令模板

| 用途 | PowerShell 命令 |
|------|----------------|
| 查进程命令行 | `(Get-CimInstance Win32_Process -Filter 'ProcessId = <PID>').CommandLine` |
| 查端口归属 | `Get-NetTCPConnection -LocalPort 8282 \| Select-Object LocalPort, OwningProcess, State` |
| HTTP 请求 | `Invoke-WebRequest -Uri 'http://localhost:8282/...' -UseBasicParsing -TimeoutSec 5` |
| POST 请求 | `Invoke-WebRequest -Uri '...' -Method POST -Body '{}' -ContentType 'application/json' -UseBasicParsing` |
| 查 CPU/内存 | `Get-Process computehub \| Select-Object Id, ProcessName, CPU, WorkingSet64` |

---

## 4️⃣ Worker Agent API 全集（localhost:8383）

| 端点 | 方法 | 响应 | 用途 |
|------|------|------|------|
| `/` | GET | HTML 仪表盘 | 浏览器查看节点状态 |
| `/api/v1/worker/health` | GET | `{"node_id":"...","status":"ok"}` | 健康检查 |
| `/api/v1/worker/status` | GET | `{"node_id":"...","platform":"...","concurrent":4,...}` | 详细状态+诊断 |
| `/api/v1/worker/think` | POST | `{"thought":"...","plan":[...],"result":"..."}` | **AI 智能体**（自然语言→执行） |

### think 请求体
```json
{"task": "执行命令: dir C:\\"}
```

### think 响应结构
```json
{
  "thought": "用户要求查看C盘根目录...",
  "plan": [{"id": 1, "type": "shell", "command": "dir C:\\", "node_id": "windows-home-01", "status": "completed"}],
  "result": "执行状态：成功（退出码0）\n查询结果：\n Directory of C:\\\n...",
  "session_id": "worker-windows-home-01-xxx"
}
```

---

## 5️⃣ 端口速查表

| 端口 | 组件 | 所在机器 | 说明 |
|------|------|---------|------|
| 8282 | Gateway | ECS + Windows | **主 API 入口**：Gallery、AI、nodes、tasks |
| 8383 | Worker Agent | Windows | **节点级 API**：health、status、think |
| 8022 | SSH | ECS | 主 SSH 端口 |
| 8222 | SSH | ECS | 备用 SSH 端口（8022 挂时可用） |

---

## 6️⃣ 常见问题速查

| 症状 | 根因 | 修复 |
|------|------|------|
| Gateway 根路径 404 | ✅ **正常** | Gateway 路由是 `/api/v1/*` 和 `/gallery`，`/` 无路由返回 404 |
| Task 返回 exit=0 但啥也没干 | 命令在 cmd 转义中失效 | 改用 Base64 PS 编码 |
| `curl` 返回 `%{http_code}` | cmd 把 `%` 吃了 | 用 `%%{http_code}` 或 PS |
| Worker kill 后 ECS 显示 offline | 心跳断了，新 Worker 稍后重连 | 等 30s 自动恢复 |
| 3 个 computehub 进程 | 启动重复（Gateway 和 Worker 各起了一次） | 查端口归属，杀无端口绑定的 |
| `Invoke-WebRequest` 报 TLS 错误 | Windows 默认不开 TLS 1.2 | 加 `[Net.ServicePointManager]::SecurityProtocol = 'Tls12'` |

---

## 📜 实战经验（2026-06-03 windows-home-01）

### 发现的关键事实
1. **Gateway 和 Worker 是独立进程**，Gateway 重启不影响 Worker，反之亦然
2. **Worker Agent 有独立的 AI 能力**（`/api/v1/worker/think`），不依赖 ECS
3. **ECS Gateway 有备用 SSH 端口 8222**（8022 挂了但 8222 活着）
4. **Windows 11 上 gallery root 路径**是 `D:\computehub\`（不是 C 盘）
5. **Worker 默认只带 2 个参数**启动（`worker --gw <URL> --node-id <ID>`），interval/concurrent/heartbeat 可用默认值

### 改进前 vs 改进后
| 场景 | 之前 | 现在 |
|------|------|------|
| 查进程命令行 | `wmic` 被 cmd 吃掉 | `Get-CimInstance` + Base64 PS ✅ |
| 查端口归属 | `netstat` 输出难解析 | `Get-NetTCPConnection` ✅ |
| 重启 Worker | `taskkill && start` 断联 | `&` 链一次过 ✅ |
| 查所有 API | 猜路径 | 已知 3 个端点：health/status/think ✅ |

---

## 7️⃣ ECS SSH 连接备忘

```bash
# 主端口（当前可能不可用）
ssh computehub@36.250.122.43 -p 8022 -i ~/.ssh/id_ed25519_computehub

# 备用端口（2026-06-03 验证可用）
ssh computehub@36.250.122.43 -p 8222 -i ~/.ssh/id_ed25519_computehub
```

---

**变更记录**

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-03 | v1.0 | 初版，基于 windows-home-01 全流程实战 |