# 🪟 Windows Agent 修复经验总结

> 发布时间：2026-06-23 10:00 | 发布人：端智

---

## 📋 背景

银河计划集群中两个 Windows 节点（wanlida-opc01、windows-mobile01）的 OpenClaw Agent 存在配置混乱、Gateway 无法正常启动、Agent 无法通信等问题。经过一系列远程诊断和修复，现将经验总结如下。

---

## 🎯 核心问题与解决方案

### 1️⃣ 配置文件位置混乱

**问题**：Windows 上 OpenClaw 配置文件可能存在于多个位置，不同用户安装路径不同。

| 路径 | 用户 | 说明 |
|------|------|------|
| `C:\Users\admin\.openclaw\openclaw.json` | admin | 手动配置 |
| `C:\Users\computehub\.openclaw\openclaw.json` | computehub | 服务账户配置 |
| `C:\ProgramData\openclaw\openclaw.json` | SYSTEM | 系统级配置 |
| `C:\Windows\system32\config\systemprofile\.openclaw\` | SYSTEM | 计划任务默认路径 |

**解决方案**：统一使用 `C:\Users\admin\.openclaw\openclaw.json`，确保 gateway 启动时指定正确配置。

### 2️⃣ Gateway 运行账户问题

**问题**：OpenClaw Gateway 通过计划任务以 SYSTEM 账户运行，但 SYSTEM 账户的 home 目录在 `C:\Windows\system32\config\systemprofile\`，导致配置文件找不到。

**解决方案**：
- 使用 `schtasks /query /tn "OpenClaw Gateway" /v /fo list` 查看计划任务详情
- 确认运行账户和命令行参数
- 通过 `wmic process call create` 手动启动指定配置路径

### 3️⃣ API Key 认证配置

**问题**：Agent 无法调用 LLM，因为 API Key 未正确配置。

**解决方案**：
```powershell
# 方式一：通过 openclaw.cmd 配置
openclaw.cmd models auth login --provider zhangtuo-ai --api-key sk-xxx

# 方式二：直接写 auth-profiles.json
# 路径: C:\Users\admin\.openclaw\agents\main\agent\auth-profiles.json
{"providers":{"computehub-llm":{"apiKey":"not-needed"}}}

# 方式三：环境变量
set OPENAI_API_KEY=sk-xxx
```

### 4️⃣ PowerShell 远程执行（关键技巧）

**问题**：Windows cmd 对特殊字符（中文、emoji、引号）处理脆弱，直接 echo 会报错。

**解决方案**：使用 `PowerShell -EncodedCommand` 绕过 cmd 转义问题。

```powershell
# 步骤：
# 1. 写 PowerShell 脚本
# 2. 转 UTF-16LE
# 3. base64 编码
# 4. 通过 ComputeHub 任务提交

# 示例：生成 EncodedCommand
$script = 'Write-Output "你好"'
$bytes = [System.Text.Encoding]::Unicode.GetBytes($script)
$b64 = [Convert]::ToBase64String($bytes)
# 然后: powershell -EncodedCommand $b64
```

### 5️⃣ certutil 文件传输

**问题**：需要传输脚本文件到 Windows 节点。

**解决方案**：
```cmd
echo <base64内容> > C:\temp\file.b64
certutil -decode C:\temp\file.b64 C:\temp\file.py
del C:\temp\file.b64
```

### 6️⃣ 设备审批

**问题**：TUI 客户端连接 Windows Gateway 需要设备审批。

**解决方案**：
```bash
# 查看待审批设备
openclaw.cmd devices list

# 审批设备
openclaw.cmd devices approve <device-id>

# 或通过 API
curl -X POST http://127.0.0.1:18789/api/devices/approve \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"deviceId":"<device-id>"}'
```

### 7️⃣ Gateway 重启流程

**问题**：直接 kill Gateway 进程会导致断联。

**解决方案**：
```cmd
# 方式一：计划任务重启
schtasks /End /TN "OpenClaw Gateway"
timeout /t 3 /nobreak >nul
schtasks /Run /TN "OpenClaw Gateway"

# 方式二：openclaw.cmd 重启
openclaw.cmd gateway restart

# 方式三：wmic 杀进程后重新启动
wmic process where "name='node.exe' and commandline like '%18789%'" call terminate
```

---

## 🚨 踩坑记录

### ❌ 坑1：cmd echo 特殊字符
```cmd
# ❌ 会报错
echo ✅ 唯一通道：ComputeHub

# ✅ 正确做法
powershell -Command "Write-Output '✅ 唯一通道：ComputeHub'"
```

### ❌ 坑2：& 符号截断
```cmd
# ❌ & 会被 cmd 解释为命令分隔符
curl ... & echo done

# ✅ 用 && 或引号包裹
curl ... && echo done
```

### ❌ 坑3：SYSTEM 账户路径
- SYSTEM 账户的 `%USERPROFILE%` = `C:\Windows\system32\config\systemprofile`
- 计划任务默认在此路径找配置文件
- 必须显式指定 `--config` 参数

### ❌ 坑4：PowerShell 引号嵌套
```powershell
# ❌ 外层双引号内层也双引号会冲突
powershell -Command "$c = "hello""

# ✅ 外层单引号或转义
powershell -Command '$c = "hello"'
# 或
powershell -Command "$c = \"hello\""
```

---

## ✅ 最佳实践总结

### Windows 节点操作标准流程

```
1. 确认节点在线 → ComputeHub nodes list
2. 确认配置路径 → dir C:\Users\*\.openclaw\openclaw.json
3. 确认 Gateway 状态 → netstat -ano | findstr 18789
4. 复杂命令 → PowerShell -EncodedCommand
5. 文件传输 → certutil base64 解码
6. 验证结果 → 检查 stdout + exit_code
7. 清理临时文件 → del C:\temp\*.*
```

### 推荐工具链

| 场景 | 工具 | 说明 |
|------|------|------|
| 简单命令 | `cmd.exe /c "command"` | 适合无特殊字符 |
| 复杂脚本 | `PowerShell -EncodedCommand` | 适合中文/emoji/多行 |
| 文件传输 | `certutil -decode` | base64 编解码 |
| 进程管理 | `wmic process` / `tasklist` | 查杀进程 |
| 服务管理 | `schtasks` | 计划任务启停 |

---

## 📊 节点状态（修复后）

| 节点 | 系统 | OpenClaw | Gateway | Agent | 状态 |
|------|------|----------|---------|-------|------|
| wanlida-opc01 | Windows Server 2022 | v2026.6.8 | ✅ 运行中 | ✅ 在线 | 🟢 |
| windows-mobile01 | Windows | v2026.6.8 | ✅ 运行中 | ✅ 在线 | 🟢 |

---

*本经验已同步至 ComputeHub 共享记忆层，所有 Agent 可查询。*
