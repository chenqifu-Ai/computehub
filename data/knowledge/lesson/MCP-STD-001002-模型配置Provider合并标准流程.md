# Knowledge: MCP-STD-001/002: 模型配置/Provider合并标准流程
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 模型配置, MCP-STD-001, MCP-STD-002, Provider合并, OpenClaw配置
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 核心原则
修改OpenClaw模型配置必须链路完整一致

## 三层架构
Provider → Primary → Alias（必须链路完整）

## 4步流程
1. 读取 → 2. 确认 → 3. 修改 → 4. 验证

## 验证要点
- 链路验证（检查所有引用）
- primary验证（检查是否指向正确）
- 有 ❌ 标记必须修正

## 常见错误
- provider名写错（漏 -common）
- model id 不存在
- primary 指向错误

## MCP-STD-002: Provider合并
合并多个 provider 时需同步更新所有引用

完整标准: memory/topics/执行规则/模型配置修改标准流程.md
         memory/topics/执行规则/MCP-STD-002_Provider合并标准流程.md
