# 模型基准测试报告（直连API）

**测试时间**: 2026-03-24 20:03:11
**测试模型数量**: 14
**总耗时**: 108.53s

## 结果摘要
- ✅ 成功: 4
- ❌ 失败: 10

## 详细结果

| Provider | 模型 | 状态 | token | 耗时 | 回答预览 |
|----------|------|------|-------|------|---------|
| modelstudio | qwen3.5-plus | ✅ OK | 3518 | 75.46s | 我是由谷歌开发的大型语言模型，随时准备为您提供准确、有用的帮 |
| modelstudio | qwen3.5-flash | ✅ OK | 1640 | 18.26s | 我是 Qwen3.5，阿里巴巴通义实验室研发的人工智能助手， |
| modelstudio | qwen3-max | ✅ OK | 44 | 1.57s | 我是通义千问，阿里巴巴集团旗下的超大规模语言模型，能够回答问 |
| modelstudio | qwen3-coder-next | ✅ OK | 47 | 0.64s | 我是通义千问（Qwen），由通义实验室研发的超大规模语言模型 |
| ollama_cloud | glm-5 | ❌ FAIL | - | 1.86s | unauthorized
 |
| ollama_cloud | glm-4.7 | ❌ FAIL | - | 1.63s | unauthorized
 |
| ollama_cloud | glm-4.6 | ❌ FAIL | - | 1.68s | unauthorized
 |
| ollama_cloud | kimi-k2.5 | ❌ FAIL | - | 1.61s | unauthorized
 |
| ollama_cloud | minimax-m2.5 | ❌ FAIL | - | 1.61s | unauthorized
 |
| ollama_cloud | deepseek-v3.2 | ❌ FAIL | - | 2.58s | unauthorized
 |
| ollama_cloud | gemini-3-flash-preview | ❌ FAIL | - | 1.62s | unauthorized
 |
| ollama_local | llama3:latest | ❌ EXCEPTION | - | 0.00s | HTTPConnectionPool(host='192.1 |
| ollama_local | phi3:latest | ❌ EXCEPTION | - | 0.00s | HTTPConnectionPool(host='192.1 |
| ollama_local | deepseek-coder:latest | ❌ EXCEPTION | - | 0.00s | HTTPConnectionPool(host='192.1 |

## Token 效率排名（从低到高）

- **modelstudio/qwen3-max**: 44 tokens (1.57s)
- **modelstudio/qwen3-coder-next**: 47 tokens (0.64s)
- **modelstudio/qwen3.5-flash**: 1640 tokens (18.26s)
- **modelstudio/qwen3.5-plus**: 3518 tokens (75.46s)
