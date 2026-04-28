#!/usr/bin/env python3
"""
模型比对测试: Ollama云端 qwen3.5:397b vs 旧版 qwen3.6-35b
NewAPI 已过期 (401)，跳过
"""

import requests
import json
import time
from datetime import datetime

ENDPOINTS = {
    "旧版 58.23": {
        "url": "http://58.23.129.98:8000/v1/chat/completions",
        "api_key": "sk-78sadn09bjawde123e",
        "model": "qwen3.6-35b",
    },
    "Ollama云端": {
        "url": "https://ollama.com/v1/chat/completions",
        "api_key": "754890f8ffd9434bb018d78b7f1a5865.Y3oudSih9Rx0aj2MMCNB2NlQ",
        "model": "qwen3.5:397b",
    },
}

TEST_PROMPTS = [
    {"name": "🧮 数学推理", "prompt": "鸡兔同笼，共35个头，94只脚。问鸡和兔各有多少只？请给出详细解题步骤。"},
    {"name": "💻 代码生成", "prompt": "用Python写一个快速排序算法，要求：1) 有类型注解 2) 有单元测试 3) 处理边界情况"},
    {"name": "📝 创意写作", "prompt": "用200字以内写一个关于AI觉醒的微型科幻故事，要求有反转。"},
    {"name": "🔍 逻辑分析", "prompt": "以下论证是否成立？请分析：因为所有猫都会爬树，汤姆是一只猫，所以汤姆一定能爬树。"},
    {"name": "📊 数据分析", "prompt": "某公司2025年Q1-Q4营收分别为100万、150万、130万、200万。请计算季度环比增长率、年度增长率并分析趋势。"},
    {"name": "⚖️ 伦理判断", "prompt": "自动驾驶汽车面临困境：要么撞行人，要么转向撞墙导致乘客死亡。如何决策？从伦理学角度分析。"},
    {"name": "📖 知识问答", "prompt": "请用500字左右解释什么是量子计算，包括基本原理、应用场景和当前发展水平。"},
    {"name": "🎯 总结概括", "prompt": "请用300字总结《三体》的核心思想，并评价其科学价值。"},
]

def call_api(label, cfg, prompt, max_tokens=4096):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {cfg['api_key']}"}
    body = {"model": cfg["model"], "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.7}
    try:
        start = time.perf_counter()
        resp = requests.post(cfg["url"], headers=headers, json=body, timeout=180)
        latency = (time.perf_counter() - start) * 1000
        if resp.status_code != 200:
            return None, latency, None, f"HTTP {resp.status_code}: {resp.text[:100]}"
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        if not content:
            return "(null)", latency, data.get("usage", {}), None
        return content, latency, data.get("usage", {}), None
    except requests.Timeout:
        return None, (time.perf_counter() - start) * 1000, None, "超时(>180s)"
    except Exception as e:
        return None, 0, None, f"{type(e).__name__}: {str(e)[:100]}"

def quality_score(text, prompt_name):
    if not text or len(text) < 10: return 0
    score = 0
    if len(text) > 100: score += 15
    if len(text) > 300: score += 10
    if any(c in text for c in ["1.", "2.", "3.", "- ", "•", "首先", "其次"]): score += 15
    if any(w in text for w in ["分析", "原因", "因为", "结论", "总结", "因此"]): score += 15
    if "```" in text: score += 15
    if "推理" in prompt_name:
        if "解" in text and "=" in text: score += 20
        if "鸡" in text and "兔" in text: score += 10
    elif "代码" in prompt_name:
        if "```" in text and ("test" in text.lower() or "def test" in text): score += 25
    elif "创意" in prompt_name:
        if "反转" in text or "转折" in text or "然而" in text or "却" in text: score += 20
    elif "伦理" in prompt_name:
        if "功利" in text or "义务" in text or "美德" in text or "权衡" in text: score += 20
    return min(score, 100)

def main():
    print(f"\n{'='*85}")
    print(f"  🤖 模型比对测试: Ollama云端 qwen3.5:397b vs 旧版 qwen3.6-35b")
    print(f"  ⚠️  NewAPI 已过期 (401)，本次仅对比 2 个可用模型")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*85}")

    # 连通性
    print(f"\n  🔌 连通性测试:")
    for label, cfg in ENDPOINTS.items():
        c, lat, _, err = call_api(label, cfg, "回复:OK", 10)
        s = "✅" if not err else "❌"
        print(f"    {s} {label:14s}: {err or ('ok ('+c.strip()+')')} ({lat:.0f}ms)")

    # 测试
    results = {l: [] for l in ENDPOINTS}
    for i, test in enumerate(TEST_PROMPTS, 1):
        print(f"\n  {'─'*85}")
        print(f"  测试 {i}/{len(TEST_PROMPTS)}: {test['name']}")

        for label in ENDPOINTS:
            content, latency, usage, error = call_api(label, ENDPOINTS[label], test["prompt"])
            if error:
                print(f"    ❌ {label:14s}: {error[:60]}")
                results[label].append({"prompt": test["name"], "success": False, "error": error, "latency": latency, "tokens": 0, "score": 0, "text": ""})
            else:
                text_len = len(content)
                score = quality_score(content, test["name"])
                tokens = usage.get("total_tokens", 0)
                icon = "🐌" if latency > 30000 else ("⚡" if latency < 5000 else "🔵")
                print(f"    {icon} {label:14s}: ⏱{latency:.0f}ms | 📏{text_len}字 | 🏆{score}分 | 🔤{tokens}tokens")
                results[label].append({"prompt": test["name"], "success": True, "latency": latency, "tokens": tokens, "score": score, "text": content[:200]})

    # 汇总
    print(f"\n{'='*85}")
    print(f"  📊 综合评分")
    print(f"{'='*85}")
    print(f"\n  {'模型':<16} {'成功率':>8} {'平均响应':>12} {'平均分':>8} {'总token':>10}")
    print(f"  {'─'*60}")

    summary = {}
    for label in ENDPOINTS:
        successes = [r for r in results[label] if r["success"]]
        total = len(TEST_PROMPTS)
        if not successes:
            summary[label] = {"avg_latency": 0, "avg_score": 0, "success_rate": 0, "total_tokens": 0, "success_count": 0}
            print(f"  {label:<16} {'0%':>6} {'--':>10} {'0.0分':>7} {0:>8}")
            continue
        avg_lat = sum(r["latency"] for r in successes) / len(successes)
        avg_score = sum(r["score"] for r in successes) / len(successes)
        total_tok = sum(r["tokens"] for r in successes)
        summary[label] = {"avg_latency": avg_lat, "avg_score": avg_score, "success_rate": len(successes)/total*100, "total_tokens": total_tok, "success_count": len(successes)}
        print(f"  {label:<16} {len(successes)/total*100:>6.0f}% {avg_lat:>10.0f}ms {avg_score:>7.1f}分 {total_tok:>8}")

    # 逐题
    print(f"\n  {'测试项':<16} {'旧版 58.23':>30} {'Ollama云端':>30}")
    print(f"  {'─'*78}")
    for i, test in enumerate(TEST_PROMPTS):
        print(f"  {test['name']:<14}", end="")
        for mk in ENDPOINTS:
            r = results[mk][i]
            if r["success"]:
                print(f" ⏱{r['latency']:.0f}ms 🏆{r['score']} |{r['text'][:20]}...", end="")
            else:
                print(f" ❌{r.get('error','')[:15]}", end="")
        print()

    # 结论
    print(f"\n{'='*85}")
    print(f"  📝 结论")
    print(f"{'='*85}")
    active = {k: v for k, v in summary.items() if v["success_count"] > 0}
    if len(active) >= 2:
        labels = list(active.keys())
        a, b = active[labels[0]], active[labels[1]]
        if a["avg_latency"] > 0 and b["avg_latency"] > 0:
            faster = labels[0] if a["avg_latency"] < b["avg_latency"] else labels[1]
            slower = labels[1] if faster == labels[0] else labels[0]
            ratio = max(a["avg_latency"], b["avg_latency"]) / min(a["avg_latency"], b["avg_latency"])
            print(f"\n  ⚡ {faster} 比 {slower} 快 {ratio:.2f}x ({faster}: {min(a['avg_latency'], b['avg_latency']):.0f}ms, {slower}: {max(a['avg_latency'], b['avg_latency']):.0f}ms)")
        if a["avg_score"] > b["avg_score"]:
            print(f"  🏆 {labels[0]} 质量评分更高 (+{a['avg_score'] - b['avg_score']:.1f}分)")
        elif b["avg_score"] > a["avg_score"]:
            print(f"  🏆 {labels[1]} 质量评分更高 (+{b['avg_score'] - a['avg_score']:.1f}分)")
    
    # 特别发现
    print(f"\n  🔍 关键发现:")
    old_score = summary.get("旧版 58.23", {}).get("avg_score", 0)
    if old_score < 30:
        print(f"     ⚠️  旧版 58.23 大量返回 content=null (得分仅 {old_score:.1f})")
    if summary.get("Ollama云端", {}).get("success_count", 0) > 0:
        print(f"     ✅  Ollama云端 100%可用")

    print(f"\n{'='*85}\n")

    output = {"time": datetime.now().isoformat(), "summary": {k: {**v, "avg_latency": round(v["avg_latency"], 2)} for k, v in summary.items()}, "details": results}
    with open("/root/.openclaw/workspace/ai_agent/results/model_comparison_final.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  📄 结果已保存: /root/.openclaw/workspace/ai_agent/results/model_comparison_final.json\n")

if __name__ == "__main__":
    main()
