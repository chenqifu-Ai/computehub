# Qwen 3.6 35B 适配层

## 概述

qwen3.6-35b API 统一适配层，解决 vLLM 部署的非标准 OpenAI 兼容 API 问题。

**核心发现**: 该模型的 `content` 字段始终为 null，所有输出在 `reasoning` 字段。

**解决方案**: 创建适配层，自动处理字段提取、格式清洗、错误处理。

## 版本

- **当前版本**: 2.0.0
- **发布日期**: 2026-04-29

## 快速开始

```python
from ai_agent.config.qwen36_adapter import ask, ask_detailed, ask_code

# 简洁问答
answer = ask("北京的首都是哪？")

# 带推理的回答
result = ask_detailed("1/2 + 1/3 = ?")
print(result["answer"])   # "5/6"
print(result["thinking"]) # 推理过程

# 代码生成
code = ask_code("写快速排序")
```

## 配置

### 环境变量（推荐）

```bash
export QWEN36_API_KEY=sk-your-api-key-here
export QWEN36_API_URL=https://ai.zhangtuokeji.top:9090/v1/chat/completions
export QWEN36_MODEL=qwen3.6-35b-common
export QWEN36_TIMEOUT=120
export QWEN36_MAX_TOKENS=4096
export QWEN36_TEMPERATURE=0.7
export QWEN36_LOG_LEVEL=INFO
```

### .env 文件

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

## API 文档

### Qwen36Adapter

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `ask()` | prompt, system, max_tokens, temperature | `str` | 简洁问答 |
| `ask_reasoned()` | prompt, system | `dict` | 带推理的回答 |
| `ask_code()` | prompt, language, max_tokens | `str` | 代码生成 |
| `health_check()` | 无 | `bool` | 健康检查 |
| `get_stats()` | 无 | `dict` | 性能统计 |

### 便捷函数

| 函数 | 说明 |
|------|------|
| `ask()` | 简洁问答 |
| `ask_detailed()` | 带推理的回答 |
| `ask_code()` | 代码生成 |
| `get_stats()` | 性能统计 |
| `health_check()` | 健康检查 |

## 自定义异常

- `ConfigurationError` - 配置错误
- `AdapterTimeout` - API 超时
- `AdapterHTTPError` - HTTP 错误
- `AdapterRateLimitError` - 速率限制
- `AdapterResponseError` - 响应格式错误

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)
