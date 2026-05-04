# Ollama服务器自动切换方案

## 一、背景

### 问题描述
用户在外出时，局域网会断开，导致无法访问本地Ollama服务器（192.168.1.7:11434），需要自动切换到云端备用服务器（ollama.com）。

### 解决目标
- 本地服务器可用时：使用本地服务器（速度快、免费）
- 本地服务器不可用时：自动切换到云端服务器（保证可用性）
- 无需人工干预

---

## 二、系统架构

### 当前配置

```
┌─────────────────────────────────────────────────────────────┐
│                     OpenClaw Gateway                         │
│                     (端口: 18789)                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐        ┌─────────────────┐           │
│   │  主服务器        │        │  备用服务器      │           │
│   │  (本地)         │        │  (云端)         │           │
│   │                 │        │                 │           │
│   │ 192.168.1.7     │        │ ollama.com      │           │
│   │ :11434          │        │ (API Key认证)   │           │
│   │                 │        │                 │           │
│   │ 可用模型:       │        │ 可用模型:       │           │
│   │ - llama3       │        │ - glm-5         │           │
│   │ - phi3         │        │ - kimi-k2.5     │           │
│   │ - deepseek-    │        │ - deepseek-v3.1 │           │
│   │   coder        │        │ - 等34个模型    │           │
│   └─────────────────┘        └─────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 配置文件位置
- 主配置：`~/.openclaw/openclaw.json`
- 切换脚本：`~/.openclaw/workspace/scripts/`

---

## 三、配置修改过程

### 3.1 初始配置（有问题）

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://192.168.1.7:11434",
      "models": [...]
    },
    "ollama-cloud": {
      "baseUrl": "https://ollama.com",
      "apiKey": "8e6253b418564cd4b4a3428f927ee6f0...",
      "models": [...]
    }
  },
  "defaults": {
    "primary": "ollama/glm-5:cloud"  // ❌ 用的是本地provider
  }
}
```

**问题**：默认模型用的是 `ollama/glm-5:cloud`，走的是本地provider，局域网断了就无法访问。

### 3.2 修改后配置

```json
{
  "defaults": {
    "primary": "ollama-cloud/glm-5"  // ✅ 改成云端provider
  }
}
```

**效果**：默认走云端服务器，局域网断开也能使用。

---

## 四、自动切换方案

### 4.1 手动切换（当前状态）

Gateway配置热重载，修改配置文件后自动生效，无需重启。

```bash
# 查看当前Gateway状态
ps aux | grep "openclaw-gateway"

# 重启Gateway（如需要）
pkill -f "openclaw-gateway"
nohup openclaw gateway > /tmp/gateway.log 2>&1 &
```

### 4.2 自动切换脚本

已创建脚本：`~/.openclaw/workspace/scripts/ollama-auto-switch.sh`

```bash
#!/bin/bash
# Ollama 自动切换脚本
# 每30秒检测本地服务器状态，自动切换本地/云端

CONFIG_FILE="$HOME/.openclaw/openclaw.json"
LOCAL_URL="http://192.168.1.7:11434/api/tags"
CLOUD_URL="https://ollama.com/api/tags"
CLOUD_KEY="8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

# 检测本地服务器
check_local() {
    curl -s --connect-timeout 3 "$LOCAL_URL" > /dev/null 2>&1
    return $?
}

# 切换到本地
switch_to_local() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 切换到本地服务器"
    sed -i 's/"primary": "ollama-cloud\/glm-5"/"primary": "ollama\/glm-5:cloud"/' "$CONFIG_FILE"
    pkill -f "openclaw-gateway" 2>/dev/null
    sleep 2
    nohup openclaw gateway > /tmp/gateway.log 2>&1 &
}

# 切换到云端
switch_to_cloud() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 切换到云端服务器"
    sed -i 's/"primary": "ollama\/glm-5:cloud"/"primary": "ollama-cloud\/glm-5"/' "$CONFIG_FILE"
    pkill -f "openclaw-gateway" 2>/dev/null
    sleep 2
    nohup openclaw gateway > /tmp/gateway.log 2>&1 &
}

# 主循环
while true; do
    if check_local; then
        # 本地可用，检查当前配置
        if grep -q '"primary": "ollama-cloud/glm-5"' "$CONFIG_FILE" 2>/dev/null; then
            switch_to_local
        fi
    else
        # 本地不可用，切换到云端
        if grep -q '"primary": "ollama/glm-5:cloud"' "$CONFIG_FILE" 2>/dev/null; then
            switch_to_cloud
        fi
    fi
    sleep 30  # 每30秒检测一次
done
```

### 4.3 启动自动切换

```bash
# 启动自动切换（后台运行）
nohup ~/.openclaw/workspace/scripts/ollama-auto-switch.sh > /tmp/ollama-switch.log 2>&1 &

# 查看运行日志
tail -f /tmp/ollama-switch.log

# 停止自动切换
pkill -f ollama-auto-switch
```

---

## 五、当前状态

### 服务器状态
| 服务器 | 地址 | 状态 | 可用模型 |
|--------|------|------|----------|
| 本地 | http://192.168.1.7:11434 | ✅ 可用 | llama3, phi3, deepseek-coder |
| 云端 | https://ollama.com | ✅ 可用 | 34个模型（glm-5, kimi-k2.5等） |

### Gateway状态
- PID: 26077
- 端口: 18789
- 默认模型: `ollama-cloud/glm-5`（云端）

### 自动切换脚本
- 位置: `~/.openclaw/workspace/scripts/ollama-auto-switch.sh`
- 状态: 已创建，待启动

---

## 六、使用建议

### 场景一：在家办公
本地服务器可用，建议使用本地模型（速度快、免费）。

```bash
# 手动切换到本地
sed -i 's/"primary": "ollama-cloud\/glm-5"/"primary": "ollama\/glm-5:cloud"/' ~/.openclaw/openclaw.json
```

### 场景二：外出办公
局域网可能断开，建议使用云端模型或启动自动切换脚本。

```bash
# 方法一：手动切换到云端（已配置）
# 当前默认就是云端

# 方法二：启动自动切换
nohup ~/.openclaw/workspace/scripts/ollama-auto-switch.sh > /tmp/ollama-switch.log 2>&1 &
```

### 场景三：混合使用
启动自动切换脚本，系统自动根据网络状态选择最优服务器。

```bash
nohup ~/.openclaw/workspace/scripts/ollama-auto-switch.sh > /tmp/ollama-switch.log 2>&1 &
```

---

## 七、注意事项

1. **API Key保密**：云端API Key已配置在配置文件中，注意保密
2. **云端计费**：云端模型可能有使用限制，注意用量
3. **切换延迟**：自动切换有30秒检测间隔，切换后需等待Gateway重启
4. **日志监控**：可查看 `/tmp/ollama-switch.log` 监控切换状态

---

## 八、相关文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 主配置 | ~/.openclaw/openclaw.json | Gateway配置文件 |
| 自动切换脚本 | ~/.openclaw/workspace/scripts/ollama-auto-switch.sh | 自动检测并切换 |
| 切换日志 | /tmp/ollama-switch.log | 自动切换运行日志 |
| Gateway日志 | /tmp/gateway.log | Gateway运行日志 |

---

*文档创建时间：2026-03-21*
*最后更新：2026-03-21 07:13*