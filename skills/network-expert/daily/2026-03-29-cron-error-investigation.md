# 🔍 码神技术调查报告：Cron Delivery Config Error

**调查时间**: 2026-03-29 09:13  
**调查专家**: 码神 (网络专家)  
**问题级别**: 🟡 中等  

---

## 📋 问题描述

**错误信息**:
```
08:45:18 [gateway] request handler failed: Error: cron channel delivery config is only supported for sessionTarget="isolated"
```

**发生时间**: 2026-03-29 08:45:18  
**错误来源**: OpenClaw Gateway  

---

## 🔍 原因分析

### 1. 根本原因

**sessionTarget 与 delivery.mode 的兼容性问题**

| sessionTarget | 支持的 delivery.mode | 说明 |
|--------------|-------------------|------|
| `"isolated"` | `announce`, `webhook`, `none` | ✅ 完整支持 |
| `"main"` | `none` only | ❌ 不支持 webhook/announce |

### 2. 技术原理

**为什么会报错？**

```
sessionTarget="main" 的工作原理:
- 任务直接在当前 main session 中执行
- 通过 systemEvent 直接注入到当前会话
- 本身就是主会话的一部分，不需要外部 delivery
- 因此不支持 webhook/announce delivery

sessionTarget="isolated" 的工作原理:
- 创建新的独立会话运行任务
- 任务完成后需要通过 delivery 机制将结果传回
- 支持 webhook/announce/none 三种 delivery 模式
```

### 3. 错误配置分析

**问题配置**:
```json
{
  "sessionTarget": "main",
  "delivery": { "mode": "webhook" }  // ❌ 不兼容！
}
```

**问题所在**:
- sessionTarget="main" 表示在主会话中执行
- 但同时配置了 webhook delivery，这是矛盾的
- main session 不需要 delivery，任务直接注入主会话

---

## ✅ 解决方案

### 方案A：改为 isolated session（推荐用于监控任务）

```json
{
  "name": "公司脉搏监控",
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行公司脉搏检查..."
  },
  "delivery": {
    "mode": "announce"
  },
  "schedule": {
    "kind": "every",
    "everyMs": 600000
  }
}
```

**优点**:
- 独立执行，不影响主会话
- 支持完整 delivery 功能
- 适合定期监控任务

**缺点**:
- 需要额外创建会话
- 可能有轻微延迟

### 方案B：保持 main session，移除 delivery

```json
{
  "name": "公司脉搏监控",
  "sessionTarget": "main",
  "payload": {
    "kind": "systemEvent",
    "text": "💓 脉搏检查 - 请运行监控脚本"
  },
  // 移除 delivery 配置
  "schedule": {
    "kind": "every",
    "everyMs": 600000
  }
}
```

**优点**:
- 直接在主会话执行
- 无额外开销

**缺点**:
- 无法配置 delivery 输出
- 任务直接注入到当前会话

---

## 🎯 码神建议

**推荐方案**: **方案A (isolated session)**

理由：
1. 公司脉搏监控任务应该独立运行
2. 支持 delivery 可以灵活输出结果
3. 避免阻塞主会话
4. 更好的错误隔离

**立即修复步骤**:

```bash
# 1. 删除旧任务（如果使用 main session）
openclaw cron remove --name "小智影业-公司脉搏检查"

# 2. 创建新任务（使用 isolated session）
# 参考方案A的配置
```

---

## 🔧 修复代码示例

```python
import json

# 正确的配置（isolated session）
job = {
    "name": "小智影业-公司脉搏检查-v2",
    "sessionTarget": "isolated",  # ✅ 改为 isolated
    "payload": {
        "kind": "agentTurn",
        "message": """💓 CEO命令：执行公司脉搏检查！

请立即：
1. 检查各部门专家工作状态
2. 检查系统健康状态  
3. 检查股票监控状态
4. 生成脉搏报告并汇报CEO

执行：python3 /root/.openclaw/workspace/ai_agent/code/company_pulse.py""",
        "model": "deepseek-v3.1:671b",
        "thinking": "off",
        "timeoutSeconds": 120
    },
    "delivery": {
        "mode": "announce"  # ✅ isolated 支持 announce
    },
    "schedule": {
        "kind": "every",
        "everyMs": 600000  # 10分钟
    }
}

print(json.dumps(job, indent=2, ensure_ascii=False))
```

---

## 📊 总结

| 项目 | 内容 |
|------|------|
| **问题** | sessionTarget="main" 与 delivery="webhook" 不兼容 |
| **原因** | main session 直接注入事件，不需要 delivery 机制 |
| **解决** | 改为 isolated session 或移除 delivery 配置 |
| **推荐** | 使用 isolated session + agentTurn payload |
| **影响** | 中等，导致定时任务无法创建 |

---

**调查完成**: ✅  
**报告时间**: 2026-03-29 09:13  
**码神**: 网络专家

---

**CEO备注**: 此问题导致公司脉搏定时任务创建失败，建议立即修复！
