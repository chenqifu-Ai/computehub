# 阿里百炼 Qwen 模型 Token 浪费 90% 的坑，我帮你填了

> **TL;DR**: 阿里百炼的 Qwen 系列模型默认开启 thinking 推理模式，简单问题也会输出大量思考过程，浪费约 90% 的 tokens。在配置中禁用 thinking 可大幅节省成本。

---

## 问题发现

今天配置 OpenClaw 的阿里百炼 API 时，发现一个奇怪的现象：

```
用户输入：hi
模型回答：Hello! How can I help you today?
Token 消耗：235 tokens
```

等等，这么简单的对话，怎么可能用掉 235 个 tokens？

## 深入调查

查看 API 返回的详细数据：

```json
{
  "usage": {
    "prompt_tokens": 11,
    "completion_tokens": 224,
    "total_tokens": 235,
    "completion_tokens_details": {
      "reasoning_tokens": 210,  // ← 思考过程占了 210 tokens！
      "text_tokens": 224
    }
  }
}
```

**真相大白**：模型默认开启了 `thinking` 推理模式，即使是最简单的问题，也会先输出一大段思考过程。

## 实测数据

测试了两个模型，结果令人震惊：

| 模型 | 问题 | 总 tokens | 推理 tokens | 浪费比例 |
|------|------|----------|------------|---------|
| qwen3.5-plus | "用一句话介绍你自己" | 235 | 210 | **89%** |
| qwen3.5-flash | "hi" | 417 | 390 | **93%** |

**这意味着：你花的钱，90% 都花在了看不见的思考过程上！**

## 解决方案

在 OpenClaw 配置文件中，为每个模型添加 `defaultParams` 禁用 thinking：

```json
{
  "models": {
    "providers": {
      "modelstudio": {
        "models": [
          {
            "id": "qwen3.5-plus",
            "name": "qwen3.5-plus",
            "reasoning": false,
            "defaultParams": {
              "thinking": {"enabled": false}
            }
          }
        ]
      }
    }
  }
}
```

或者在 API 调用时显式传递参数：

```bash
curl https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [{"role": "user", "content": "hi"}],
    "thinking": {"enabled": false}
  }'
```

## 配置修复清单

今天还修复了其他几个配置问题，一并记录：

### 1. Ollama 本地/云端分离
**问题**：ollama provider 混用了本地和云端模型

**解决**：分离为两个独立 provider
- `ollama` → 本地服务器 `http://192.168.1.7:11434`
- `ollama-cloud` → 云端 API `https://api.ollama.com`

### 2. 阿里百炼 URL 修正
**错误**：`https://coding.dashscope.aliyuncs.com/v1`
**正确**：`https://dashscope.aliyuncs.com/compatible-mode/v1`

### 3. 模型名称清理
删除了配置中不存在的模型，避免切换时崩溃。

## 当前推荐配置

| Provider | 模型 | 用途 | Token 效率 |
|----------|------|------|-----------|
| ollama-cloud | glm-5:cloud | 日常使用 | ⭐⭐⭐⭐⭐ |
| modelstudio | qwen3.5-plus | 复杂任务 | ⭐⭐⭐⭐ (已禁用 thinking) |
| ollama | llama3:latest | 本地快速 | ⭐⭐⭐⭐⭐ |

## 总结

1. **阿里百炼 Qwen 模型默认开启 thinking**，浪费约 90% tokens
2. **配置中禁用 thinking** 可大幅节省成本
3. **日常使用推荐 ollama-cloud/glm-5:cloud**，不浪费 tokens
4. **配置错误会导致崩溃**，确保 URL 和模型名称正确

---

*配置已保存到 `~/.openclaw/openclaw.json`，下次使用阿里百炼模型时会自动禁用 thinking。*

*发现时间：2026-03-24*
