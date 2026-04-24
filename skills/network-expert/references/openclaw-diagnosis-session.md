# OpenClaw系统诊断报告

## 会话信息
- 时间：2026-03-21 07:38
- 专家：网络专家
- 任务：检测OpenClaw系统问题
- 环境：Termux on Android (arm64)

---

## 一、系统概述

### 基本信息
| 项目 | 状态 |
|------|------|
| 操作系统 | Linux 6.17.0-PRoot-Distro (arm64) |
| Node版本 | 24.13.0 |
| OpenClaw版本 | 2026.3.13 |
| Gateway端口 | 18789 |
| 运行模式 | 本地模式 (bind=lan) |

### 模型配置
- 主模型：deepseek-coder:latest (本地)
- 备用服务器：192.168.1.7:11434 (本地Ollama)
- 本地可用模型：llama3:latest, phi3:latest, deepseek-coder:latest

---

## 二、发现的问题

### ⚠️ 问题1：安全审计警告（中等风险）

**问题描述：**
```
WARN No auth rate limiting configured
```

**影响：** Gateway绑定在非loopback地址，但没有配置认证速率限制，可能遭受暴力破解攻击。

**解决方案：**
```json
// 在 ~/.openclaw/openclaw.json 中添加：
{
  "gateway": {
    "auth": {
      "rateLimit": {
        "maxAttempts": 10,
        "windowMs": 60000,
        "lockoutMs": 300000
      }
    }
  }
}
```

---

### ⚠️ 问题2：命令拒绝规则无效（中等风险）

**问题描述：**
```
WARN Some gateway.nodes.denyCommands entries are ineffective
```

**影响：** denyCommands使用的是精确匹配，某些条目可能不起作用。

**解决方案：**
- 使用精确命令名称（如 `canvas.present` 而非模糊匹配）
- 如果需要更广泛的限制，调整allowCommands/default工作流

---

### ⚠️ 问题3：插件安全配置未设置（低风险）

**问题描述：**
```
WARN Extensions exist but plugins.allow is not set
```

**影响：** 发现feishu插件，但plugins.allow未设置，任何发现的插件都可能自动加载。

**解决方案：**
```json
// 在 ~/.openclaw/openclaw.json 中添加：
{
  "plugins": {
    "allow": ["feishu"]
  }
}
```

---

### ⚠️ 问题4：systemd服务不可用（环境限制）

**问题描述：**
```
systemd user services unavailable
```

**影响：** 无法使用systemd管理Gateway服务，需要手动启动或使用其他进程管理工具。

**解决方案：**
- 在Termux环境下，使用前台模式运行Gateway
- 或使用Termux的sv服务管理

---

### ⚠️ 问题5：Gateway服务PATH未设置（配置问题）

**问题描述：**
```
Gateway service PATH is not set
```

**影响：** Gateway服务可能无法找到必要的可执行文件。

**解决方案：**
- 运行 `openclaw doctor --repair` 自动修复

---

### ⚠️ 问题6：内存配置未启用

**问题描述：**
```
Memory: 0 files · 0 chunks · sources memory
```

**影响：** 记忆系统未存储任何文件，可能影响长期记忆功能。

**解决方案：**
- 检查MEMORY.md是否存在
- 确认记忆插件配置正确

---

### ⚠️ 问题7：Tailscale未启用（可选）

**问题描述：**
```
Tailscale: off
```

**影响：** 无法通过Tailscale网络远程访问。

**解决方案：**
- 如需远程访问，配置Tailscale：`openclaw tailscale up`

---

### ℹ️ 信息：Session上下文使用率高

**状态：**
```
agent:main:main - Tokens: 100k/127k (78%)
```

**影响：** 当前会话已使用78%的上下文窗口，接近限制。

**解决方案：**
- 定期压缩会话历史
- 或重启会话

---

## 三、网络连通性测试

### 本地Gateway测试
- 地址：http://127.0.0.1:18789
- 状态：运行中
- RPC探测：正常

### Ollama服务器测试
- 地址：http://192.168.1.7:11434
- 状态：正常 ✅
- 可用模型：llama3:latest, phi3:latest, deepseek-coder:latest

### 磁盘空间
- 已用：303GB / 463GB (66%)
- 可用空间充足

---

## 四、修复建议优先级

| 优先级 | 问题 | 建议 |
|--------|------|------|
| 🔴 高 | 认证速率限制 | 配置gateway.auth.rateLimit |
| 🟡 中 | 插件安全配置 | 设置plugins.allow |
| 🟡 中 | denyCommands规则 | 使用精确命令名称 |
| 🟢 低 | systemd服务 | 使用前台模式运行 |
| 🟢 低 | Gateway PATH | 运行openclaw doctor --repair |

---

## 五、修复命令汇总

```bash
# 1. 运行自动修复
openclaw doctor --repair

# 2. 检查安全审计
openclaw security audit --deep

# 3. 查看Gateway状态
openclaw gateway status

# 4. 重启Gateway（如需要）
openclaw gateway restart
```

---

## 六、配置建议

### 安全配置示例
```json
{
  "gateway": {
    "auth": {
      "rateLimit": {
        "maxAttempts": 10,
        "windowMs": 60000,
        "lockoutMs": 300000
      }
    }
  },
  "plugins": {
    "allow": ["feishu"]
  }
}
```

---

**诊断完成时间：** 2026-03-21 07:39
**诊断结果：** 系统基本正常运行，存在3个安全警告需处理
