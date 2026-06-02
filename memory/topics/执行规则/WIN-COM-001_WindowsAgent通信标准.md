# WIN-COM-001 Windows Worker Agent 通信标准

> v1.0 · 2026-06-02 · 基于 Windows-mobile Agent 实战

---

## ⚡ 一句话总结

```
# 三条命：health → status → think
# payload 写入用 certutil base64 解码，别碰 JSON 转义
```

---

## 一、Agent 接口

Worker Agent 监听 `localhost:8383`，三个端点：

| 端点 | 方法 | 作用 | 返回 |
|------|------|------|------|
| `/api/v1/worker/health` | GET | 存活检测 | `{"status":"ok","node_id":"..."}` |
| `/api/v1/worker/status` | GET | 完整状态 | node_id, platform, diagnosis, gpu_type, concurrent |
| `/api/v1/worker/think` | POST | AI 对话 | thought, plan, result, session_id |

---

## 二、标准步骤 (SOP)

### Step 0：存活检测 → 5s

```json
// 提交任务
{ "node_id":"Windows-mobile", "command":"cmd /c curl -s http://127.0.0.1:8383/api/v1/worker/health" }
```

**期望**: `{"node_id":"Windows-mobile","status":"ok"}`

### Step 1：状态查询 → 5s

```json
{ "node_id":"Windows-mobile", "command":"cmd /c curl -s http://127.0.0.1:8383/api/v1/worker/status" }
```

**期望**: 返回 platform, diagnosis, gpu_type 等完整信息

### Step 2：AI 对话 → 60s

核心问题：**POST 请求需要传 JSON body，但 cmd 嵌套在任务 command 里会导致引号转义爆炸。**

解法：**用 certutil base64 写 payload 文件，curl -d @file 读取。**

```bash
# ── 1) 准备 payload（base64 编码） ──
# 原始 JSON:
# {"task":"你好，请汇报状态","session_id":"chat-001"}
# → base64 encode:
echo -n '{"task":"你好，请汇报状态","session_id":"chat-001"}' | base64 -w0
# → eyJ0YXNrIjoi5L2g5aW977yM6K+35o+Q5oKj54mI5oCBIiwic2Vzc2lvbl9pZCI6ImNoYXQtMDAxIn0K

# ── 2) 写入 payload 文件（单任务） ──
{
  "node_id": "Windows-mobile",
  "command": "cmd /c echo <BASE64> > C:\\tmp\\agent.json && certutil -decode C:\\tmp\\agent.json C:\\tmp\\agent_payload.json > nul 2>&1 && echo PAYLOAD_OK",
  "timeout": 30
}

# ── 3) 调用 Agent think ──
{
  "node_id": "Windows-mobile",
  "command": "cmd /c curl -s -X POST http://127.0.0.1:8383/api/v1/worker/think -H \"Content-Type: application/json\" -d @C:\\tmp\\agent_payload.json && echo DONE",
  "timeout": 60
}
```

**注意**:
- curl 的 `-d @file` 语法是 Windows curl 原生支持的，不需要 `type` 或 `Get-Content`
- `-H` 头部的引号用 `\"` 转义即可，因为 -d 走文件不涉及 body 引号问题
- timeout 给够 60s（Agent 内部调用 LLM 可能 30s+）

---

## 三、完整通信示例

```bash
# 三步即可完成一次完整的 Agent 对话：

# Step A: 编码 payload
PAYLOAD_B64=$(echo -n '{"task":"汇报当前平台、版本和运行状态","session_id":"chat-test-001"}' | base64 -w0)

# Step B: 写 payload（发任务到 Windows 节点）
curl -s -X POST http://<GW>:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"payload-write\",
    \"node_id\": \"Windows-mobile\",
    \"command\": \"cmd /c echo $PAYLOAD_B64 > C:\\\\tmp\\\\agent.json && certutil -decode C:\\\\tmp\\\\agent.json C:\\\\tmp\\\\agent_payload.json > nul 2>&1 && echo PAYLOAD_OK\",
    \"timeout\": 30
  }"

# Step C: 调用 think
curl -s -X POST http://<GW>:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"agent-call\",
    \"node_id\": \"Windows-mobile\",
    \"command\": \"cmd /c curl -s -X POST http://127.0.0.1:8383/api/v1/worker/think -H \\\\\"Content-Type: application/json\\\\\" -d @C:\\\\tmp\\\\agent_payload.json && echo DONE\",
    \"timeout\": 60
  }"

# 等 20s 后查结果
curl -s \"http://<GW>:8282/api/v1/tasks/detail?task_id=agent-call&node_id=Windows-mobile\"
```

---

## 四、常见问题

| 症状 | 原因 | 修复 |
|------|------|------|
| `Invalid JSON` | body 中的引号被 cmd 吞了 | 改走 `-d @file` |
| exit=6 (couldn't resolve host) | 网关 URL 拼错了 | 确认 `127.0.0.1:8383` |
| `LLM call failed: timeout` | Agent LLM 调用超时 | 检查 LLM 后端可用性，或加 timeout |
| `PAYLOAD_OK` 但 curl 返回空 | payload JSON 格式不对 | `certutil -decode` 后检查文件内容 |

---

## 五、Payload 编码对照表

```bash
# 常用 payload 的 base64 编码（直接用，不用再编）

# "你好，请汇报平台、版本和状态"
BASE64_COMMON="eyJ0YXNrIjoi5L2g5aW977yM6K+35o+Q5oKj5bmz5Y+w44CB54mI5pys5ZKM54q25oCB5Lit5paH6L+b5a6e576O5bCR44CCIn0="

# "执行 self-diagnose 并返回结果"  
BASE64_DIAG="eyJ0YXNrIjoi5omn6KGM6Ieq6K+dLWRpYWdub3NlIOW5tui/kOWKqOe7k+aehOS4uiIsInNlc3Npb25faWQiOiJkaWFnLWNoZWNrLTAwMSJ9"

# "列出当前运行的任务"
BASE64_TASKS="eyJ0YXNrIjoi5YiX5Ye65b2T5YmN6L+b6KG M55qE5Lu75YqhIiwic2Vzc2lvbl9pZCI6InRhc2stbGlzdC0wMDEifQ=="
```

---

## 六、历史踩坑（为什么这么写）

**直接 JSON 嵌套 → 放弃**:
- `-d "{\"task\":\"...\"}"` → JSON 在 cmd 和 Go 的双重解析下必炸
- `-d @C:\tmp\file.json` → 引号在 echo 写入时被吞

**PowerShell → 放弃**:
- `powershell -Command "..."` → JSON 嵌套的 `\"` 在 cmd→powershell→JSON 三层转义中必定变形

**✅ 最终方案: certutil base64**:
- `echo <B64> > file` → 纯字母数字，无特殊字符
- `certutil -decode` → Windows 原生命令，稳定可靠
- `curl -d @file` → 读文件，body 内容不受转义影响

**核心教训**: Windows 远程传输 JSON = **永远不要嵌套 JSON 字符串**。要么 base64，要么写文件。