#!/usr/bin/env python3
"""
zhangtuo-ai 完整对比测试
- zhangtuo-ai/qwen3.6-35b      (非 common)
- zhangtuo-ai-common/qwen3.6-35b-common  (common, reasoning=True)
"""

import requests
import json
import time
import statistics

BASE = "https://ai.zhangtuokeji.top:9090/v1"
KEY_NOCOMMON = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"
KEY_COMMON   = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"

TEST_CASES = [
    {"name": "基础问候", "msgs": [{"role": "user", "content": "你好，简单介绍一下自己"}], "max_tokens": 200},
    {"name": "数学计算", "msgs": [{"role": "user", "content": "请计算 1357 * 8291 + 456 = ? 直接给出答案，不用过程"}], "max_tokens": 100},
    {"name": "代码生成", "msgs": [{"role": "user", "content": "用Python写一个快速排序函数，带类型注解"}], "max_tokens": 400},
    {"name": "知识问答", "msgs": [{"role": "user", "content": "什么是量子纠缠？用一句话解释"}], "max_tokens": 150},
    {"name": "长回复测试", "msgs": [{"role": "user", "content": "列出中国五大名著的书名、作者和朝代/年代，用JSON格式"}], "max_tokens": 500},
    {"name": "边界问题", "msgs": [{"role": "user", "content": "请用Markdown代码块包裹你的回答，内容是：Hello World"}], "max_tokens": 200},
]

def call_api(model_id, api_key, msgs, max_tokens):
    url = f"{BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    t0 = time.time()
    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        elapsed = time.time() - t0
        if r.status_code != 200:
            return {
                "error": True, "status": r.status_code,
                "body": r.text[:500], "latency_ms": round(elapsed*1000, 1),
                "has_reasoning": False, "reasoning_chars": 0, "content_chars": 0,
                "total_tokens": "?", "stop_reason": None
            }
        resp = r.json()
        choice = resp.get("choices", [{}])[0]
        msg = choice.get("message", {})
        
        # ⚠️ NewAPI 所有输出都在 reasoning 字段，content 永远为 null
        reasoning = msg.get("reasoning") or "" or ""
        content = msg.get("content") or "" or ""
        
        usage = resp.get("usage", {})
        stop = choice.get("finish_reason", "") or None
        
        return {
            "error": False,
            "reasoning": reasoning,
            "content": content,
            "has_reasoning": len(reasoning) > 0,
            "reasoning_chars": len(reasoning),
            "content_chars": len(content),
            "stop_reason": stop,
            "total_tokens": usage.get("total_tokens", "?"),
            "latency_ms": round(elapsed * 1000, 1),
        }
    except Exception as e:
        return {
            "error": True, "exception": str(e),
            "latency_ms": round((time.time()-t0)*1000, 1),
            "has_reasoning": False, "reasoning_chars": 0, "content_chars": 0,
            "total_tokens": "?", "stop_reason": None
        }

def run_single_test(model_name, model_id, api_key, case):
    result = call_api(model_id, api_key, case["msgs"], case["max_tokens"])
    result["case"] = case["name"]
    return result

print("=" * 90)
print("📊 zhangtuo-ai 双模型完整对比测试")
print(f"   A: qwen3.6-35b       vs   B: qwen3.6-35b-common (reasoning)")
print(f"   基准版                    reasoning增强版")
print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 90)

results_nc = []
results_c = []

for i, case in enumerate(TEST_CASES, 1):
    print(f"\n{'─'*90}")
    print(f"测试 {i}/{len(TEST_CASES)}: 【{case['name']}】")
    
    # A: non-common
    r_nc = run_single_test("qwen3.6-35b", "qwen3.6-35b", KEY_NOCOMMON, case)
    results_nc.append(r_nc)
    
    # B: common
    r_c = run_single_test("qwen3.6-35b-common", "qwen3.6-35b-common", KEY_COMMON, case)
    results_c.append(r_c)
    
    # Print side by side
    for label, r in [("A (非 common)", r_nc), ("B (common)", r_c)]:
        print(f"  [{label}]")
        if r["error"]:
            status = r.get("status", "")
            exc = r.get("exception", "")
            print(f"     ❌ 错误: {status} / {exc}")
        else:
            output_text = r["reasoning"] if r["has_reasoning"] else r["content"]
            preview = (output_text[:100].replace("\n", " ").replace("\r", "") or "(empty)")
            print(f"     ✅ 输出: \"{preview}...\"")
            print(f"     reasoning: {'✅有 ({r[\"reasoning_chars\"]}字)' if r['has_reasoning'] else '❌无'}")
            print(f"     latency: {r['latency_ms']}ms | tokens: {r['total_tokens']} | stop: {r['stop_reason']}")

# Summary
print(f"\n{'='*90}")
print("📈 汇总统计")
print(f"{'='*90}")

def calc_stats(results_list, label):
    ok_results = [r for r in results_list if not r["error"]]
    n_ok = len(ok_results)
    n_total = len(results_list)
    
    latencies = [r["latency_ms"] for r in ok_results]
    reasoning_lens = [r["reasoning_chars"] for r in ok_results if r["has_reasoning"]]
    stop_reasons = {}
    for r in ok_results:
        sr = r.get("stop_reason") or "unknown"
        stop_reasons[sr] = stop_reasons.get(sr, 0) + 1
    
    print(f"\n  {label}:")
    print(f"    成功率:           {n_ok}/{n_total}")
    if latencies:
        med = sorted(latencies)[len(latencies)//2]
        avg = statistics.mean(latencies)
        mn, mx = min(latencies), max(latencies)
        print(f"    延迟 P50:         ~{med:.0f}ms")
        print(f"    延迟均值:         ~{avg:.0f}ms")
        print(f"    延迟范围:         {mn:.0f}~{mx:.0f}ms")
    if reasoning_lens:
        print(f"    Reasoning 长度:   ~{statistics.mean(reasoning_lens):.0f}字符 (平均)")
        print(f"    Reasoning 范围:   {min(reasoning_lens)}~{max(reasoning_lens)}字符")
    else:
        print(f"    Reasoning:        无有效输出")
    if stop_reasons:
        top_stop = max(stop_reasons.items(), key=lambda x: x[1])
        print(f"    Stop原因分布:     {dict(stop_reasons)}")
        print(f"    最大Stop:         {top_stop[0]} ({top_stop[1]}次)")

calc_stats(results_nc, "A — qwen3.6-35b (非 common)")
calc_stats(results_c, "B — qwen3.6-35b-common (reasoning)")

print(f"\n{'='*90}")
print("✅ 测试完成")
print(f"{'='*90}")
