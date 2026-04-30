# NewAPI qwen3.6-35b-common 使用规则

**最后更新**: 2026-04-28  
**API Key**: sk-08XEevM6SdeMbvh273pmAiOZ9cZWJ3vKJELhpEMCNb7aMX6F  
**Base URL**: https://ai.zhangtuokeji.top:9090/v1  

---

## ⚠️ 核心规则（必读）

### 1. max_tokens 必须 = 4096（最优）
```json
{
  "model": "qwen3.6-35b-common",
  "messages": [...],
  "max_tokens": 4096,  // ✅ 最优 — content 不丢失，速度最快
  // "max_tokens": 2048, // ❌ 不够，reasoning 占满导致 content 丢失
  // "max_tokens": 8192, // 浪费 — content 不增加，延迟涨 3s
  "temperature": 0.7
}
```

**实测对比**：
| max_tokens | avg_content | 为空次数 | 平均延迟 | 评价 |
|-----------|------------|---------|---------|------|
| 2048 | 400 字 | 2/8 | 12.2s | ❌ content 常为空 |
| **4096** | **1026 字** | **0** | 12.3s | ✅ 最优 |
| 8192 | 1022 字 | 0 | 15.8s | 延迟多 3s，无收益 |
| 16384 | 1070 字 | 0 | 15.6s | 边际递减 |

**原因**：reasoning 平均 4000-5000 token，2048 不够分。4096 时 content+reasoning 都能完整输出。

### 2. 并发控制
- **推荐并发度**: 2-4（QPS 0.11-0.17，延迟稳定）
- **超过 8**: 延迟飙升（32s+），不划算
- **16 并发**: QPS 最高 0.21，但延迟波动大

### 3. temperature 设置
- **代码生成**: 0.7-1.0
- **知识问答**: 0.0-0.3
- **默认**: 0.7

### 4. 模型 ID
- ✅ `qwen3.6-35b-common`
- ✅ `qwen3.6-35b`（双 Key 都有，Key2 快 ~1s）

---

## 快速测试

```bash
# 标准对话
curl -X POST https://ai.zhangtuokeji.top:9090/v1/chat/completions \
  -H "Authorization: Bearer sk-08XEevM6SdeMbvh273pmAiOZ9cZWJ3vKJELhpEMCNb7aMX6F" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-35b-common","messages":[{"role":"user","content":"你好"}],"max_tokens":4096,"temperature":0.7}'

# 代码生成
curl -X POST https://ai.zhangtuokeji.top:9090/v1/chat/completions \
  -H "Authorization: Bearer sk-08XEevM6SdeMbvh273pmAiOZ9cZWJ3vKJELhpEMCNb7aMX6F" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-35b-common","messages":[{"role":"user","content":"写Python快速排序"}],"max_tokens":4096,"temperature":0.3}'
```

---

## 与旧版对比

| 特性 | 旧版 (58.23.129.98:8000) | 新版 (ai.zhangtuokeji.top:9090) |
|------|--------------------------|-------------------------------|
| content 字段 | ❌ 始终 null | ✅ 正常 |
| 需要适配层 | ✅ 是 | ❌ 不需要 |
| 响应速度 | ~1.4s | ~12s |
| max_tokens | 2048 | **4096** |

---

*实测结论: max_tokens=4096, 并发 2-4, temperature=0.7*
