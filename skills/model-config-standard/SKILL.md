---
name: model-config-standard
description: OpenClaw 模型配置修改标准流程 (MCP-STD-001)。用于创建、修改、验证 OpenClaw 模型 provider/别名/默认模型配置。适用于：添加新模型供应商、修改 primary 模型、设置别名映射、验证三层链路完整性、修复断链。触发词：模型配置、provider 添加、别名设置、链路验证、模型适配、MCP-STD-001。
---

# OpenClaw 模型配置修改标准流程 (MCP-STD-001)

**版本**: v1.1 | **制定日期**: 2026-04-28

## 🚫 核心规则

- **当前 primary = `ollama-cloud-2/deepseek-v4-flash`**
- AI 禁止主动修改 primary，老大没吩咐不动
- AI 禁止擅自切换 session 模型（测试可临时切，测完恢复）
- 老大随时可自由切换

## 一、三层架构

修改任何模型配置前，必须保证三层链路完整一致：

```
Layer 1: models.providers       ← 物理连接（URL + API Key + 模型定义）
         ↓
Layer 2: agents.defaults.model.primary   ← 默认模型指向
         ↓
Layer 3: agents.defaults.models           ← 别名映射（alias）
```

### Provider 层标准模板

```json
{
  "baseUrl": "https://...",
  "apiKey": "sk-xxx",
  "api": "openai-completions",
  "models": [{
    "id": "model-id",
    "name": "Model Name",
    "api": "openai-completions",
    "reasoning": false,
    "input": ["text"],
    "contextWindow": 256000,
    "maxTokens": 8192
  }]
}
```

### Agent 层标准模板

```json
{
  "model": {
    "primary": "provider_name/model_id"
  },
  "models": {
    "provider_name/model_id": {
      "alias": "快捷别名"
    }
  }
}
```

## 二、完整流程（6 步）

### 第 0 步：读取当前配置

执行 `scripts/read_config.sh` 查看所有 provider 和 alias。

### 第 1 步：确认目标

明确：① 哪个 provider ② 哪个 model id ③ 别名是什么 ④ 是否改 primary

### 第 2 步：执行修改

- Provider 层：在 `models.providers` 中新增/修改 provider 定义
- Agent 层：在 `agents.defaults.models` 中添加别名映射
- 如需改 primary：修改 `agents.defaults.model.primary`

**规则**：
- provider_name 必须与 `models.providers` 中的 key 逐字匹配
- model_id 必须存在于对应 provider 的 `models` 列表
- 推理模型设 `reasoning: true`，Gateway 自动从 reasoning 字段读 output
- **不要手动加** `output: {field: ...}`，让 Gateway 处理
- 必须包含 `contextWindow` 和 `maxTokens`

### 第 3 步：验证链路（必须！）

执行 `scripts/verify_links.sh`。所有别名必须显示 ✅，无 ❌。

### 第 4 步：验证 primary

执行 `scripts/verify_primary.sh`。确认 primary 指向有效 provider+model。

### 第 5 步：实际调用测试（可选但推荐）

对新增 provider 做实际 API 调用测试，确认响应正常。

## 三、常见错误

| 错误 | 表现 | 修正 |
|------|------|------|
| provider 名写错 | ❌ provider NOT FOUND | 检查 models.providers 中的 key |
| model id 不在列表中 | ❌ model NOT in provider | 确认 id 完全匹配 |
| primary 指向不存在 | ❌ primary 验证失败 | 修正指向 |
| 手动加 output 字段 | 可能冲突 | 移除，让 Gateway 自动处理 |
| 缺 contextWindow/maxTokens | 非标准配置 | 补上 |

## 四、完整技能目录结构

```
model-config-standard/
├── SKILL.md              ← 本文件
├── scripts/
│   ├── read_config.sh    ← 读取当前配置
│   ├── verify_links.sh   ← 验证别名链路
│   ├── verify_primary.sh ← 验证 primary
│   └── add_provider.sh   ← 标准化添加 provider（含验证）
└── references/
    └── examples.md       ← 常见配置示例
```
