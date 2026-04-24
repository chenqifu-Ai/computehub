# 模型 Token 浪费问题分析报告

## 测试结果汇总

| Provider | 模型 | 问题 | 总 tokens | 思考 tokens | 浪费比例 | 可禁用 |
|----------|------|------|----------|------------|---------|--------|
| **阿里百炼** | qwen3.5-plus | "hi" | 235 | 210 | 89% | ❌ 参数不生效 |
| **阿里百炼** | qwen3.5-flash | "hi" | 493 | 458 | 93% | ❌ 参数不生效 |
| **阿里百炼** | qwen3-max | "hi" | 20 | 0 | 0% | ✅ 无需禁用 |
| **阿里百炼** | qwen3-coder-next | - | - | - | - | 未测试 |
| **ollama-cloud** | glm-5:cloud | "hi" | 204 | 193 | 95% | ❌ 参数不生效 |
| **ollama-cloud** | kimi-k2.5:cloud | "hi" | 94 | 92 | 98% | ❌ 参数不生效 |
| **ollama-cloud** | minimax-m2.5:cloud | "hi" | 45 | 25 | 56% | ❌ 参数不生效 |
| **本地 ollama** | llama3:latest | "hi" | - | 0 | 0% | ✅ 无需禁用 |
| **本地 ollama** | phi3:latest | "hi" | 3 | 0 | 0% | ✅ 无需禁用 |
| **本地 ollama** | deepseek-coder:latest | "hi" | 21 | 0 | 0% | ✅ 无需禁用 |

## 关键发现

### 1. 阿里百炼 Qwen 系列
- **qwen3-max** 模型 **没有 thinking 问题**，可以直接使用
- **qwen3.5-plus/flash** 强制开启 thinking，`{"thinking": {"enabled": false}}` 参数不生效
- 建议：使用 **qwen3-max** 替代 qwen3.5-plus

### 2. ollama-cloud 模型
- 所有模型（glm-5, kimi-k2.5, minimax-m2.5）都有 thinking 输出
- Ollama API 不支持禁用 thinking 参数
- 这是 Ollama 云端平台的限制

### 3. 本地 ollama 模型
- **无 thinking 问题**，可以直接使用
- phi3 和 deepseek-coder 测试通过，浪费为 0%

## 解决方案

### 推荐配置（按 token 效率排序）

| 排名 | 模型 | Token 效率 | 推荐用途 |
|------|------|----------|---------|
| 1️⃣ | 本地 llama3/phi3/deepseek-coder | 100% | 本地快速任务 |
| 2️⃣ | 阿里百炼 qwen3-max | 100% | 复杂推理任务 |
| 3️⃣ | ollama-cloud minimax-m2.5 | 44% | 云端备选 |
| 4️⃣ | ollama-cloud glm-5:cloud | 5% | 不推荐（浪费严重）|
| 5️⃣ | 阿里百炼 qwen3.5-plus/flash | 7-11% | 不推荐（浪费严重）|

### 配置优化

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama-cloud/glm-5:cloud"  // 可改为 modelstudio/qwen3-max
      }
    }
  },
  "models": {
    "providers": {
      "modelstudio": {
        "models": [
          {
            "id": "qwen3-max",
            "name": "qwen3-max",
            "reasoning": false,
            "contextWindow": 262144,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

## 结论

1. **阿里百炼 qwen3-max 是最佳云端选择**，没有 thinking 浪费
2. **本地模型完全无浪费**，适合本地快速任务
3. **ollama-cloud 和 qwen3.5 系列**严重浪费 tokens，不推荐日常使用
4. **thinking 参数在多数模型上不生效**，需要平台级支持

---

*测试时间：2026-03-24*