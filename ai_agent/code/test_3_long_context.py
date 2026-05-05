#!/usr/bin/env python3
"""
第三阶段：长上下文测试
目标：测试 GPU 处理不同长度上下文的能力
"""
import requests, json, time, os

URL_8000 = "http://58.23.129.98:8000/v1"
URL_8001 = "http://58.23.129.98:8001/v1"
API_KEY = "sk-78sadn09bjawde123e"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def make_long_text(token_approx):
    """生成近似 token 数量的中文文本（1 中文字≈1 token）"""
    return "人工智能正在改变世界 " * token_approx

def test_context_length(url, label, context_tokens, output_tokens=256):
    """测试指定上下文长度的响应"""
    prompt = make_long_text(context_tokens)
    
    log(f"\n📊 {label}: {context_tokens:,} tokens 输入 → {output_tokens} tokens 输出")
    
    t0 = time.time()
    try:
        r = requests.post(url + "/chat/completions", json={
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": f"请总结以下文字主题（一句话）：{prompt}"}],
            "max_tokens": output_tokens,
            "temperature": 0.7
        }, headers=HEADERS, timeout=600)
        
        elapsed = time.time() - t0
        d = r.json()
        
        if "choices" not in d:
            log(f"  ❌ API 错误: {d.get('error', {}).get('message', 'Unknown')[:200]}")
            return {"error": d.get("error", "Unknown")}
        
        msg = d["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning", "")
        u = d.get("usage", {})
        tokens_in = u.get("prompt_tokens", 0)
        tokens_out = u.get("completion_tokens", 0)
        
        report = {
            "port": label,
            "input_tokens_approx": context_tokens,
            "actual_tokens_in": tokens_in,
            "output_tokens": tokens_out,
            "time": f"{elapsed:.2f}s",
            "tps": f"{tokens_out/elapsed:.1f} t/s" if elapsed > 0 else "0",
            "success": True
        }
        
        log(f"  ✅ 实际输入: {tokens_in:,} tokens | 输出: {tokens_out} tokens | {elapsed:.2f}s | {tokens_out/elapsed:.1f} t/s")
        if len(content) > 100:
            log(f"  输出: \"{content[:100]}...\"")
        
        return report
    except Exception as e:
        elapsed = time.time() - t0
        log(f"  ❌ 异常 ({elapsed:.2f}s): {type(e).__name__}: {str(e)[:200]}")
        return {"error": str(e)[:200], "time": f"{elapsed:.2f}s", "success": False}

def log(msg):
    print(msg, flush=True)

log("=" * 60)
log("📊 第三阶段：长上下文测试")
log("=" * 60)

test_results = []

# 不同上下文长度
for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    log(f"\n{'='*50}")
    log(f"🔧 端口: {label}")
    log(f"{'='*50}")
    
    context_lengths = [4096, 16384, 32768, 65536, 131072]
    
    for ctx_tokens in context_lengths:
        time.sleep(2)  # 间隔
        r = test_context_length(url, label, ctx_tokens, output_tokens=256)
        if "success" in r:
            test_results.append(r)

# 保存
os.makedirs("/root/.openclaw/workspace/ai_agent/results", exist_ok=True)
with open("/root/.openclaw/workspace/ai_agent/results/test_3_long_context.json", "w") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False)

log("\n" + "=" * 60)
log(f"✅ 第三阶段完成 | 共 {len(test_results)} 项")
log("📌 结果已保存: ai_agent/results/test_3_long_context.json")
log("📌 等待第四阶段：持续压力测试")
