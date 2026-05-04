# 模型基准测试报告（修复后）

**测试时间**: 2026-03-24 20:15:47
**测试模型数量**: 9
**总耗时**: 63.51s

## 修复内容
- ✅ Ollama Cloud API 端点修复：`api.ollama.com` → `ollama.com/api`
- ✅ 模型 ID 修复：添加 `-cloud` 后缀
- ✅ 认证方式验证：Bearer token 有效

## 结果摘要
- ✅ 成功: 9
- ❌ 失败: 0

## 详细结果

| Provider | 模型 | 状态 | token | 耗时 | 回答预览 |
|----------|------|------|-------|------|---------|
| modelstudio | qwen3.5-plus | ✅ OK | 1438 | 27.55s | 我是由 Google 训练的大型语言模型，致力于为你提供准确 |
| modelstudio | qwen3.5-flash | ✅ OK | 827 | 9.42s | 我是 Qwen3.5，阿里巴巴最新研发的大语言模型，擅长回答 |
| modelstudio | qwen3-max | ✅ OK | 43 | 2.37s | 我是通义千问，阿里巴巴集团旗下的超大规模语言模型，能够回答问 |
| modelstudio | qwen3-coder-next | ✅ OK | 57 | 0.78s | 我是通义千问（Qwen），阿里巴巴集团自主研发的超大规模语言 |
| ollama_cloud_fixed | gemma3:4b-cloud | ✅ OK | 41 | 2.06s | 我是一个大型语言模型，由 Google 训练，可以理解和生成 |
| ollama_cloud_fixed | glm-5-cloud | ✅ OK | 160 | 4.61s | 我是Z.ai训练的大型语言模型，旨在通过自然语言处理技术协助 |
| ollama_cloud_fixed | kimi-k2.5-cloud | ✅ OK | 265 | 8.48s | 我是Claude，一个由Anthropic开发的AI助手，致 |
| ollama_cloud_fixed | minimax-m2.5-cloud | ✅ OK | 103 | 2.55s | 你好！我是MiniMax-M2.1，一个由MiniMax公司 |
| ollama_cloud_fixed | deepseek-v3.2-cloud | ✅ OK | 132 | 5.68s | 我是一款由深度求索公司创造的AI智能助手，专注于知识问答、语 |

## Token 效率排名（从低到高）

- **ollama_cloud_fixed/gemma3:4b-cloud**: 41 tokens (2.06s)
- **modelstudio/qwen3-max**: 43 tokens (2.37s)
- **modelstudio/qwen3-coder-next**: 57 tokens (0.78s)
- **ollama_cloud_fixed/minimax-m2.5-cloud**: 103 tokens (2.55s)
- **ollama_cloud_fixed/deepseek-v3.2-cloud**: 132 tokens (5.68s)
- **ollama_cloud_fixed/glm-5-cloud**: 160 tokens (4.61s)
- **ollama_cloud_fixed/kimi-k2.5-cloud**: 265 tokens (8.48s)
- **modelstudio/qwen3.5-flash**: 827 tokens (9.42s)
- **modelstudio/qwen3.5-plus**: 1438 tokens (27.55s)
