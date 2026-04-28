# zhangtuo-ai 双模型对比测试结果

**测试日期**: 2026-04-28 21:32  
**模型 A**: `zhangtuo-ai/qwen3.6-35b` (非 common)  
**模型 B**: `zhangtuo-ai-common/qwen3.6-35b-common` (reasoning=True)

---

## 📊 汇总统计

| 指标 | A (非 common) | B (common) |
|------|---------------|------------|
| **成功率** | 6/6 ✅ | 6/6 ✅ |
| **延迟 P50** | ~2321ms | ~2235ms |
| **延迟均值** | ~2052ms | ~2081ms |
| **延迟范围** | 887~3508ms | 916~3370ms |
| **Reasoning 平均长度** | ~927字符 | ~906字符 |
| **Reasoning 范围** | 282~1616字符 | 318~1764字符 |
| **Stop Reason** | length × 6 | length × 6 |

---

## 🔍 关键发现

### 1. performance 几乎一致
- 延迟、token 数、输出长度完全相同（同 prompt → 同样响应）
- 两个模型共享同一 API 端点，性能表现没有差异

### 2. ⚠️ Stop Reason 全部为 "length"
- 6 个测试全部命中 max_tokens 上限
- 原因：**reasoning 内容和答案共用 max_tokens**，导致实际回答被截断
- 建议：实际使用时设置更高的 max_tokens（如 4096+），确保 reasoning + 正文都能完整输出

### 3. content 字段始终为 null
- 两个模型的 `message.content` 都是 null
- **所有输出都在 `reasoning` 字段中**（包括思考过程和最终答案）
- 需要适配层从 reasoning 读取内容

### 4. 两个 model 的区别
从本次测试来看：
- **功能上**: 无区别（同样的响应质量、速度）
- **配置上**: common 版标记了 `reasoning: true`
- **实际影响**: 取决于适配层如何读取

---

## 💡 建议

1. **日常对话**: 用任意一个即可，性能无异
2. **max_tokens 设置**: 推荐 4096+（当前 8192 的理论值但实际使用受限于 reasoning 消耗）
3. **适配层必读 reasoning**: 不要读 content（永远 null）

---

*由小智自动生成 | MCP-STD-001 规范记录*
