# DeepSeek 接入 ComputeHub Gateway 指南

## 🎯 接入方式

ComputeHub 使用统一的 LLMClient 接口，支持任何 OpenAI-compatible API，包括 DeepSeek。

## 📋 配置示例

### 方案一：修改 config.json（推荐）

```json
{
  "composer": {
    "api_url": "https://api.deepseek.com/v1",
    "api_key": "your-deepseek-api-key-here",
    "model": "deepseek-chat",
    "execute_models": ["deepseek-chat", "deepseek-coder"],
    "max_concurrency": 8,
    "timeout_seconds": 120
  }
}
```

### 方案二：环境变量覆盖

```bash
export COMPOSEHUB_COMPOSER_API_URL="https://api.deepseek.com/v1"
export COMPOSEHUB_COMPOSER_API_KEY="your-deepseek-api-key"
export COMPOSEHUB_COMPOSER_MODEL="deepseek-chat"
```

### 方案三：代码中直接创建客户端

```go
import "github.com/computehub/opc/src/composer"

// 创建 DeepSeek 客户端
client := composer.NewLLMClient(
    "https://api.deepseek.com/v1",
    "your-api-key",
    "deepseek-chat",
)

// 使用客户端
result, err := client.ChatWithPrompt("系统提示", "用户输入", 1024)
```

## 🔧 支持的 DeepSeek 模型

- `deepseek-chat` - 通用对话模型
- `deepseek-coder` - 代码专用模型  
- `deepseek-reasoner` - 推理模型
- 其他 DeepSeek 提供的模型

## 🌐 API 端点要求

DeepSeek API 必须支持 OpenAI-compatible 格式：
- `POST /v1/chat/completions`
- 相同的请求/响应格式
- Bearer Token 认证

## 🚀 验证连接

```bash
# 测试 DeepSeek 连接
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

## 📊 监控和调试

接入后，可以通过 Gateway 的以下功能监控：
- **任务分解日志**: 查看大模型拆分效果
- **并行执行统计**: 监控各模型节点性能
- **结果汇总质量**: 评估最终输出质量

## ⚠️ 注意事项

1. **API Key 安全**: 不要将 API Key 提交到版本控制
2. **速率限制**: 注意 DeepSeek 的 API 调用限制
3. **模型兼容性**: 确保模型支持所需的上下文长度
4. **错误处理**: 配置合理的超时和重试机制

## 🔗 相关文件

- `src/composer/client.go` - LLM 客户端实现
- `config.json` - 主配置文件
- `src/composer/composer.go` - 任务编排核心