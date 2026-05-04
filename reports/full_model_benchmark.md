# 完整模型基准测试报告（41个模型）

**测试时间**: 2026-03-24 20:32:47
**测试模型总数**: 38
**总耗时**: 251.82s

## 修复内容
- ✅ Ollama Cloud API 端点修复：`api.ollama.com` → `ollama.com/api`
- ✅ 模型 ID 修复：添加 `-cloud` 后缀
- ✅ 认证方式验证：Bearer token 有效

## 结果摘要
- ✅ 成功: 37
- ❌ 失败: 1

## 详细结果

| Provider | 模型 | 状态 | token | 耗时 | 回答预览 |
|----------|------|------|-------|------|---------|
| modelstudio | qwen3.5-plus | ✅ OK | 2095 | 32.89s | 我是由 Google 开发的大型语言模型，致力于为你提供准确 |
| modelstudio | qwen3.5-flash | ✅ OK | 1521 | 16.05s | 我是通义千问，由阿里巴巴云研发的人工智能助手，致力于为你提供 |
| modelstudio | qwen3-max | ✅ OK | 47 | 1.71s | 我是通义千问，阿里巴巴集团旗下的超大规模语言模型，能够回答问 |
| modelstudio | qwen3-coder-next | ✅ OK | 51 | 0.73s | 我是通义千问（Qwen），阿里巴巴集团研发的超大规模语言模型 |
| ollama_cloud | gemma3:4b-cloud | ✅ OK | 45 | 2.06s | 我是一个大型语言模型，由 Google 训练，可以生成文本、 |
| ollama_cloud | gemma3:12b-cloud | ✅ OK | 48 | 1.82s | 我是一个大型语言模型，可以根据您的提示生成各种文本格式，例如 |
| ollama_cloud | gemma3:27b-cloud | ✅ OK | 43 | 1.79s | 我是一个大型语言模型，由 Google 训练，旨在以信息丰富 |
| ollama_cloud | ministral-3:3b-cloud | ✅ OK | 72 | 1.72s | **我是一名热爱探索与创造的科技与人文结合的思考者，专注于用 |
| ollama_cloud | ministral-3:8b-cloud | ✅ OK | 87 | 1.95s | **我是一个热爱学习、善于思考的AI助手，专注于提供准确、个 |
| ollama_cloud | ministral-3:14b-cloud | ✅ OK | 58 | 1.98s | 我是一款由人工智能驱动的助手，致力于为您提供准确、创新且全面 |
| ollama_cloud | glm-4.6-cloud | ❌ EXCEPTION | - | 0.00s | HTTPSConnectionPool(host='olla |
| ollama_cloud | glm-4.7-cloud | ✅ OK | 140 | 3.60s | 我是GLM，由智谱AI开发的大语言模型，能够通过自然语言处理 |
| ollama_cloud | glm-5-cloud | ✅ OK | 464 | 4.62s | 我是一个由Z.ai训练的大型语言模型，旨在协助你解答疑惑、提 |
| ollama_cloud | minimax-m2-cloud | ✅ OK | 244 | 4.35s | 我是一个乐于助人、友好可靠的 AI 助手，擅长高效沟通与信息 |
| ollama_cloud | minimax-m2.1-cloud | ✅ OK | 245 | 3.92s | 我是MiniMax公司开发的智能助手MiniMax-M2.1 |
| ollama_cloud | minimax-m2.5-cloud | ✅ OK | 84 | 4.53s | 我是一个AI助手，可以帮助你回答问题、提供信息、进行对话以及 |
| ollama_cloud | minimax-m2.7-cloud | ✅ OK | 247 | 15.32s | 我是MiniMax‑M2.7，由MiniMax打造的AI助手 |
| ollama_cloud | kimi-k2.5-cloud | ✅ OK | 285 | 15.76s | 我是 Kimi，一个能够回答问题、协助创作、进行深度对话并帮 |
| ollama_cloud | kimi-k2:1t-cloud | ✅ OK | 42 | 8.01s | 我是由月之暗面科技有限公司训练的大语言模型，知识截止于202 |
| ollama_cloud | kimi-k2-thinking-cloud | ✅ OK | 282 | 25.95s | 我是Kimi，一个由月之暗面科技有限公司开发的AI助手，擅长 |
| ollama_cloud | deepseek-v3.1:671b-cloud | ✅ OK | 36 | 5.33s | 你好！我是DeepSeek，由深度求索公司创造的AI助手，乐 |
| ollama_cloud | deepseek-v3.2-cloud | ✅ OK | 91 | 19.32s | 我是深度求索公司创造的AI助手DeepSeek，专业、安全、 |
| ollama_cloud | qwen3-coder-next-cloud | ✅ OK | 53 | 2.51s | 我是通义千问（Qwen），阿里巴巴集团旗下的超大规模语言模型 |
| ollama_cloud | qwen3-coder:480b-cloud | ✅ OK | 61 | 10.52s | 我是通义千问，阿里巴巴集团旗下的超大规模语言模型，能够回答问 |
| ollama_cloud | qwen3-next:80b-cloud | ✅ OK | 1168 | 8.06s | 

我是通义千问，阿里巴巴集团研发的超大规模语言模型，能够回 |
| ollama_cloud | qwen3.5:397b-cloud | ✅ OK | 1211 | 7.91s | 我是你的智能 AI 助手，随时准备为你解答问题、创作内容并提 |
| ollama_cloud | qwen3-vl:235b-cloud | ✅ OK | 319 | 13.49s | 我是通义千问，阿里巴巴集团旗下的超大规模语言模型，致力于提供 |
| ollama_cloud | qwen3-vl:235b-instruct-cloud | ✅ OK | 59 | 6.62s | 我是通义千问，阿里巴巴集团旗下的通义实验室研发的超大规模语言 |
| ollama_cloud | mistral-large-3:675b-cloud | ✅ OK | 55 | 3.29s | "我是一个善于倾听、乐于助人的AI助手，随时准备用知识和创意 |
| ollama_cloud | cogito-2.1:671b-cloud | ✅ OK | 55 | 3.08s | 我是Cogito，一个由Deep Cogito创造的AI助手 |
| ollama_cloud | devstral-2:123b-cloud | ✅ OK | 53 | 4.06s | 我是一个热爱学习和分享知识的AI助手，随时准备帮助你解决问题 |
| ollama_cloud | devstral-small-2:24b-cloud | ✅ OK | 46 | 2.39s | 我是一个热爱学习和分享知识的AI助手，致力于为用户提供准确、 |
| ollama_cloud | nemotron-3-super-cloud | ✅ OK | 61 | 1.65s | 我是一个能够理解和生成自然语言的AI助手，致力于为用户提供准 |
| ollama_cloud | nemotron-3-nano:30b-cloud | ✅ OK | 61 | 1.64s | 我是训练有素的AI助手，擅长准确快速地回答各类问题，希望能帮 |
| ollama_cloud | gpt-oss:20b-cloud | ✅ OK | 208 | 2.12s | 我是一名由 OpenAI 训练的大型语言模型，随时为您解答问 |
| ollama_cloud | gpt-oss:120b-cloud | ✅ OK | 174 | 3.03s | 我是由OpenAI研发的AI语言模型ChatGPT，能够理解 |
| ollama_cloud | rnj-1:8b-cloud | ✅ OK | 69 | 3.36s | 我是一名人工智能助手，可以帮助您完成各种任务，提供信息解答， |
| ollama_cloud | gemini-3-flash-preview-cloud | ✅ OK | 368 | 4.69s | 我是由 Google 训练的大型语言模型，旨在为你提供信息、 |

## Token 效率排名（从低到高）

- **ollama_cloud/deepseek-v3.1:671b-cloud**: 36 tokens (5.33s)
- **ollama_cloud/kimi-k2:1t-cloud**: 42 tokens (8.01s)
- **ollama_cloud/gemma3:27b-cloud**: 43 tokens (1.79s)
- **ollama_cloud/gemma3:4b-cloud**: 45 tokens (2.06s)
- **ollama_cloud/devstral-small-2:24b-cloud**: 46 tokens (2.39s)
- **modelstudio/qwen3-max**: 47 tokens (1.71s)
- **ollama_cloud/gemma3:12b-cloud**: 48 tokens (1.82s)
- **modelstudio/qwen3-coder-next**: 51 tokens (0.73s)
- **ollama_cloud/qwen3-coder-next-cloud**: 53 tokens (2.51s)
- **ollama_cloud/devstral-2:123b-cloud**: 53 tokens (4.06s)
- **ollama_cloud/mistral-large-3:675b-cloud**: 55 tokens (3.29s)
- **ollama_cloud/cogito-2.1:671b-cloud**: 55 tokens (3.08s)
- **ollama_cloud/ministral-3:14b-cloud**: 58 tokens (1.98s)
- **ollama_cloud/qwen3-vl:235b-instruct-cloud**: 59 tokens (6.62s)
- **ollama_cloud/qwen3-coder:480b-cloud**: 61 tokens (10.52s)
- **ollama_cloud/nemotron-3-super-cloud**: 61 tokens (1.65s)
- **ollama_cloud/nemotron-3-nano:30b-cloud**: 61 tokens (1.64s)
- **ollama_cloud/rnj-1:8b-cloud**: 69 tokens (3.36s)
- **ollama_cloud/ministral-3:3b-cloud**: 72 tokens (1.72s)
- **ollama_cloud/minimax-m2.5-cloud**: 84 tokens (4.53s)
- **ollama_cloud/ministral-3:8b-cloud**: 87 tokens (1.95s)
- **ollama_cloud/deepseek-v3.2-cloud**: 91 tokens (19.32s)
- **ollama_cloud/glm-4.7-cloud**: 140 tokens (3.60s)
- **ollama_cloud/gpt-oss:120b-cloud**: 174 tokens (3.03s)
- **ollama_cloud/gpt-oss:20b-cloud**: 208 tokens (2.12s)
- **ollama_cloud/minimax-m2-cloud**: 244 tokens (4.35s)
- **ollama_cloud/minimax-m2.1-cloud**: 245 tokens (3.92s)
- **ollama_cloud/minimax-m2.7-cloud**: 247 tokens (15.32s)
- **ollama_cloud/kimi-k2-thinking-cloud**: 282 tokens (25.95s)
- **ollama_cloud/kimi-k2.5-cloud**: 285 tokens (15.76s)
- **ollama_cloud/qwen3-vl:235b-cloud**: 319 tokens (13.49s)
- **ollama_cloud/gemini-3-flash-preview-cloud**: 368 tokens (4.69s)
- **ollama_cloud/glm-5-cloud**: 464 tokens (4.62s)
- **ollama_cloud/qwen3-next:80b-cloud**: 1168 tokens (8.06s)
- **ollama_cloud/qwen3.5:397b-cloud**: 1211 tokens (7.91s)
- **modelstudio/qwen3.5-flash**: 1521 tokens (16.05s)
- **modelstudio/qwen3.5-plus**: 2095 tokens (32.89s)
