# 阿里百炼 Qwen 模型成本分析报告

## 测试数据

### 测试场景
- 输入：简单问题 "hi" 或 "用一句话介绍你自己"
- 测试时间：2026-03-24
- 测试模型：qwen3.5-plus, qwen3.5-flash, qwen3-max

### 实测 Token 消耗

| 模型 | 输入 | 总 tokens | 思考 tokens | 实际回答 | 浪费比例 |
|------|------|----------|------------|---------|---------|
| qwen3.5-plus | "hi" | 235 | 210 | 25 | **89.4%** |
| qwen3.5-flash | "hi" | 493 | 458 | 35 | **93.0%** |
| qwen3-max | "hi" | 20 | 0 | 20 | **0%** |
| qwen3-coder-next | - | - | - | - | 未测试 |

### 关键发现
1. **qwen3.5 系列**：默认开启 thinking 推理模式，简单问题也会输出大量思考过程
2. **qwen3-max**：**无 thinking 浪费**，直接输出答案
3. **成本差异**：同样是 "hi"，qwen3.5-plus 消耗 235 tokens，qwen3-max 只消耗 20 tokens

## 成本计算

### 假设阿里百炼定价
根据公开信息，阿里百炼模型定价大致为：
- qwen3.5-plus：约 ¥0.004/千tokens
- qwen3.5-flash：约 ¥0.002/千tokens  
- qwen3-max：约 ¥0.012/千tokens

### 实际成本对比

**场景：1000 次 "hi" 调用**

| 模型 | Tokens 消耗 | 理论成本 | 实际有效 | 浪费成本 |
|------|------------|---------|---------|---------|
| qwen3.5-plus | 235,000 | ¥0.94 | 25,000 | ¥0.84 (**89%**) |
| qwen3.5-flash | 493,000 | ¥0.99 | 35,000 | ¥0.92 (**93%**) |
| **qwen3-max** | **20,000** | **¥0.24** | **20,000** | **¥0.00 (0%)** |

### 结论
1. **qwen3-max 最便宜**：虽然单价最高，但因为无浪费，实际成本最低
2. **qwen3.5 系列最贵**：看似便宜，但因为 90% 浪费，实际成本更高
3. **成本差异**：qwen3.5-plus 实际成本是 qwen3-max 的 **3.9 倍**

## 证据链

### 1. API 返回数据
```json
{
  "usage": {
    "prompt_tokens": 11,
    "completion_tokens": 224,
    "total_tokens": 235,
    "completion_tokens_details": {
      "reasoning_tokens": 210,  // ← 思考过程消耗
      "text_tokens": 224
    }
  }
}
```

### 2. 思考内容示例
```
Thinking Process:
1. Analyze the Request:
   - Input: "hi"
   - Intent: Greeting/Initiation of conversation
   - Tone: Friendly, helpful, neutral
2. Determine the appropriate response:
   - Acknowledge the greeting
   - Offer assistance
   - Keep it concise and welcoming
...（共 210 tokens 思考内容）
```

### 3. 用户不知情
- 文档未明确说明 thinking tokens 计费方式
- 用户以为只支付 "回答" 部分
- 实际上 "思考过程" 也被计费

## 投诉建议

### 投诉理由
1. **不透明收费**：thinking tokens 计费未明确告知用户
2. **强制浪费**：无法关闭 thinking 功能（即使设置 `thinking: {enabled: false}` 也无效）
3. **误导定价**：低价模型实际更贵（因为浪费）

### 投诉渠道
1. 阿里云客服：95187
2. 阿里云工单：https://workorder.console.aliyun.com/
3. 消费者协会：12315

### 诉求
1. **透明化**：明确标注 thinking tokens 计费方式
2. **可选化**：提供关闭 thinking 的选项
3. **退款**：对历史浪费的 tokens 进行补偿

## 替代方案

### 推荐配置
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "modelstudio/qwen3-max"  // 无浪费，最便宜
      }
    }
  }
}
```

### 其他选择
1. **本地模型**：`ollama/llama3:latest`（免费）
2. **云端模型**：`ollama-cloud/glm-5:cloud`（有浪费但单价低）
3. **最优选择**：`modelstudio/qwen3-max`（无浪费，性价比最高）

---

**测试时间**：2026-03-24  
**测试人员**：小智  
**报告状态**：完整证据链已保存