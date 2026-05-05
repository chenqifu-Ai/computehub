# 模型配置示例

## 示例 1：添加备用 API 端口

添加端口 8000 作为 8001 的备用：

```bash
bash scripts/add_provider.sh qwen-8000 qwen3.6-35b "qwen-8000" "http://58.23.129.98:8000/v1" "sk-xxx"
bash scripts/verify_links.sh
```

## 示例 2：添加 NewAPI 备用

```bash
bash scripts/add_provider.sh newapi-backup qwen3.6-35b "newapi-backup" "https://newapi.example.com/v1" "sk-xxx"
bash scripts/verify_links.sh
```

## 示例 3：推理模型标准配置

```json
{
  "baseUrl": "https://...",
  "apiKey": "sk-xxx",
  "api": "openai-completions",
  "models": [{
    "id": "model-name",
    "name": "Model Name (别名)",
    "api": "openai-completions",
    "reasoning": true,
    "input": ["text"],
    "contextWindow": 256000,
    "maxTokens": 8192
  }]
}
```

**注意**：
- 推理模型 `reasoning: true`，Gateway 自动从 reasoning 字段读取 output
- 不要手动加 `output: {field: reasoning}`
- contextWindow 和 maxTokens 必须提供

## 示例 4：普通模型（非推理）

```json
{
  "baseUrl": "https://...",
  "apiKey": "sk-xxx",
  "api": "openai-completions",
  "models": [{
    "id": "model-name",
    "name": "Model Name",
    "api": "openai-completions",
    "reasoning": false,
    "input": ["text"],
    "contextWindow": 256000,
    "maxTokens": 8192
  }]
}
```

## 常见 provider 端点

| Provider | URL | 模型 | 说明 |
|----------|-----|------|------|
| qwen3.6-35b | http://58.23.129.98:8001/v1 | qwen3.6-35b | 主用 |
| qwen-8000 | http://58.23.129.98:8000/v1 | qwen3.6-35b | 备用 |
| qwen36-backup | http://58.23.129.98:8999/v1 | qwen3.6-35b | 备用 |
| zhangtuo-ai-common | https://ai.zhangtuokeji.top:9090/v1 | qwen3.6-35b-common | 主力 |
