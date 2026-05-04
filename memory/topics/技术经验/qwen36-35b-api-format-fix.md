# qwen3.6-35b API 格式异常修复方案

**创建时间**: 2026-04-24 16:28  
**优先级**: 🔴 重要（所有调用此模型的脚本必须适配）  
**状态**: ✅ 已实现适配层

---

## 问题描述

qwen3.6-35b 通过 vLLM 部署的 API 有**非标准响应格式**：

| 字段 | 标准值 | 实际值 |
|------|--------|--------|
| `message.content` | 回答文本 | `null` |
| `message.reasoning` | 推理过程 | **全部输出**（推理 + 回答） |

### 影响范围
- 所有直接调用 `http://58.23.129.98:8000/v1/chat/completions` 的脚本
- 所有假设 `content` 字段有值的解析逻辑
- `requests.post().json()["choices"][0]["message"]["content"]` 将返回 `None`

---

## 解决方案

### 1. 统一适配层（推荐）

**文件位置**: `/root/.openclaw/workspace/ai_agent/config/qwen36_adapter.py`

提供三个调用接口：

```python
from ai_agent.config.qwen36_adapter import ask, ask_detailed, ask_code, get_adapter

# 简洁回答（自动过滤推理元信息）
answer = ask("北京的首都是哪？")
# 返回: "北京"

# 带推理的答案
result = ask_detailed("1/2 + 1/3 = ?")
print(result["answer"])   # "5/6"
print(result["thinking"]) # 推理过程

# 代码生成
code = ask_code("写快速排序")

# 健康检查
adapter = get_adapter()
if adapter.health_check():
    print("API 正常")
```

### 2. 手动适配方法

如果不想引入适配层，手动修改如下：

```python
# ❌ 错误写法（标准 OpenAI 格式）
answer = resp.json()["choices"][0]["message"]["content"]

# ✅ 正确写法
msg = resp.json()["choices"][0]["message"]
answer = msg.get("reasoning") or msg.get("content") or ""
```

### 3. 调用时 system prompt 优化

由于 reasoning 字段包含大量元信息（"Final Output Generation"等），
system prompt 中应明确禁止推理输出：

```python
system = """你是一个简洁的助手。
规则：
1. 直接回答问题
2. 不要输出 'Thinking Process' 或分析步骤
3. 不要有 'Final Answer' 或 'Final Output' 等元信息
4. 只输出最终答案"""
```

---

## 模型信息

| 项目 | 值 |
|------|-----|
| 模型 | qwen3.6-35b |
| 部署引擎 | vLLM |
| API 地址 | http://58.23.129.98:8000/v1/chat/completions |
| API Key | sk-78sadn09bjawde123e |
| 最大上下文 | 262,144 tokens |
| 环境变量 | QWEN36_URL, QWEN36_KEY |

---

## 性能基准（2026-04-24 实测）

| 指标 | 值 |
|------|-----|
| 平均延迟 | 641ms |
| 中位数延迟 | 556ms |
| 吞吐量 | 1.02 QPS |
| 生成速度 | 115.5 tokens/s |
| 并发能力 | 5并发稳定 |

---

## 关联文件

- 适配层: `ai_agent/config/qwen36_adapter.py`
- 原始测试脚本: `ai_agent/code/qwen36_test.py`
- 全面测试报告: `memory/topics/技术经验/qwen36-35b-test-report.md`

---

*最后更新: 2026-04-24 16:28*
