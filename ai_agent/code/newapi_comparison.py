#!/usr/bin/env python3
"""NewAPI 双 key 全面对比测试"""

import requests
import json
import time
from datetime import datetime

KEYS = [
    {
        "name": "Key1 (common)",
        "key": "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl",
        "model": "qwen3.6-35b-common",
    },
    {
        "name": "Key2 (非common)",
        "key": "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe",
        "model": "qwen3.6-35b",
    },
]

BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"

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

def call_api(label, key_cfg, prompt, max_tokens=2048):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key_cfg['key']}"}
    body = {"model": key_cfg["model"], "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.7}
    try:
        start = time.perf_counter()
        resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=180)
        latency = (time.perf_counter() - start) * 1000
        if resp.status_code != 200:
            return None, latency, None, f"HTTP {resp.status_code}: {resp.text[:100]}"
        data = resp.json()
        content = data["choices"][0]["message"].get("content", "")
        reasoning = data["choices"][0]["message"].get("reasoning", "")
        usage = data.get("usage", {})
        finish = data["choices"][0].get("finish_reason", "unknown")
        return {"content": content, "reasoning": reasoning, "finish_reason": finish}, latency, usage, None
    except requests.Timeout:
        return None, (time.perf_counter() - start) * 1000, None, "超时"
    except Exception as e:
        return None, 0, None, f"{type(e).__name__}: {str(e)[:100]}"

def main():
    print(f"\n{'='*85}")
    print(f"  🤖 NewAPI 双 Key 全面对比测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*85}")

    # 连通性
    print(f"\n  🔌 连通性测试:")
    for k in KEYS:
        result, lat, _, err = call_api(k["name"], k, "回复:OK", 10)
        s = "✅" if not err else "❌"
        content = result["content"][:30] if result and result["content"] else "(empty)"
        reasoning = result["reasoning"][:30] if result and result.get("reasoning") else "(empty)"
        print(f"    {s} {k['name']:16s}: {err or content} ({lat:.0f}ms)")
        print(f"       reasoning: {reasoning}")

    # 测试
    results = {k["name"]: [] for k in KEYS}
    for i, test in enumerate(TEST_PROMPTS, 1):
        print(f"\n  {'─'*85}")
        print(f"  测试 {i}/{len(TEST_PROMPTS)}: {test['name']}")

        for k in KEYS:
            result, latency, usage, error = call_api(k["name"], k, test["prompt"])
            if error:
                print(f"    ❌ {k['name']:16s}: {error}")
                results[k["name"]].append({"success": False, "error": error, "latency": latency, "tokens": 0, "score": 0})
            else:
                c = result["content"]
                r = result["reasoning"]
                content_len = len(c) if c else 0
                reasoning_len = len(r) if r else 0
                if not c: c = ""
                if not r: r = ""
                score = quality_score(c, test["name"])
                tokens = usage.get("total_tokens", 0)
                finish = result.get("finish_reason", "?")
                icon = "⚡" if latency < 10000 else ("🔵" if latency < 20000 else "🐌")
                print(f"    {icon} {k['name']:16s}: ⏱{latency:.0f}ms | 📏{content_len}字 | 🏆{score}分 | 🔤{tokens}tok | finish={finish} | reason_len={reasoning_len}")
                results[k["name"]].append({"success": True, "latency": latency, "tokens": tokens, "score": score, "content": c[:500], "reasoning": r[:300]})

    # 汇总
    print(f"\n{'='*85}")
    print(f"  📊 综合评分")
    print(f"{'='*85}")
    print(f"\n  {'项目':<16} {'Key1 (common)':>20} {'Key2 (非common)':>20}")
    print(f"  {'─'*58}")

    summary = {}
    for key_cfg in KEYS:
        label = key_cfg["name"]
        successes = [r for r in results[label] if r["success"]]
        total = len(TEST_PROMPTS)
        if not successes:
            summary[label] = {"avg_latency": 0, "avg_score": 0, "success_rate": 0, "total_tokens": 0}
            continue
        avg_lat = sum(r["latency"] for r in successes) / len(successes)
        avg_score = sum(r["score"] for r in successes) / len(successes)
        total_tok = sum(r["tokens"] for r in successes)
        summary[label] = {"avg_latency": avg_lat, "avg_score": avg_score, "success_rate": len(successes)/total*100, "total_tokens": total_tok, "success_count": len(successes)}
        print(f"  {'平均响应':<16} {avg_lat:>18.0f}ms {avg_lat>0 and max(avg_lat,summary.get('Key2 (非common)',{}).get('avg_latency',0))!=avg_lat and min(avg_lat,summary.get('Key2 (非common)',{}).get('avg_latency',0))==avg_lat and '⚡' or '':>4} {max(avg_lat,summary.get('Key2 (非common)',{}).get('avg_latency',0))-min(avg_lat,summary.get('Key2 (非common)',{}).get('avg_latency',0)) if summary.get('Key2 (非common)',{}).get('avg_latency',0)>0 else 0:>7.0f}ms差 {avg_lat:>12.0f}ms")

    # Better table format
    print(f"\n  {'模型':<16} {'成功率':>8} {'平均响应':>12} {'平均分':>8} {'总token':>10}")
    print(f"  {'─'*60}")
    for key_cfg in KEYS:
        label = key_cfg["name"]
        s = summary.get(label, {})
        if not s:
            print(f"  {label:<16} {'--':>6} {'--':>10} {'--':>7} {0:>8}")
            continue
        print(f"  {label:<16} {s['success_rate']/1*1:>6.0f}% {s['avg_latency']:>10.0f}ms {s['avg_score']:>7.1f}分 {s['total_tokens']:>8}")

    # 逐题对比
    print(f"\n  {'测试项':<14} {'Key1 (common)':>40} {'Key2 (非common)':>40}")
    print(f"  {'─'*96}")
    for i, test in enumerate(TEST_PROMPTS):
        print(f"  {test['name']:<12}", end="")
        for key_cfg in KEYS:
            label = key_cfg["name"]
            r = results[label][i]
            if r["success"]:
                print(f" ⏱{r['latency']:.0f}ms 🏆{r['score']} |📏{len(r.get('content',''))}", end="")
            else:
                print(f" ❌{r.get('error','')[:15]}", end="")
        print()

    # 速度差
    print(f"\n{'='*85}")
    print(f"  📝 结论")
    print(f"{'='*85}")
    labels = list(summary.keys())
    if len(labels) == 2 and summary[labels[0]]['success_count'] > 0 and summary[labels[1]]['success_count'] > 0:
        a, b = summary[labels[0]], summary[labels[1]]
        if a['avg_latency'] > 0 and b['avg_latency'] > 0:
            faster = labels[0] if a['avg_latency'] < b['avg_latency'] else labels[1]
            slower = labels[1] if faster == labels[0] else labels[0]
            ratio = max(a['avg_latency'], b['avg_latency']) / min(a['avg_latency'], b['avg_latency'])
            print(f"\n  ⚡ {faster} 比 {slower} 快 {ratio:.2f}x ({min(a['avg_latency'], b['avg_latency']):.0f}ms vs {max(a['avg_latency'], b['avg_latency']):.0f}ms)")
        if a['avg_score'] > b['avg_score']:
            print(f"  🏆 {labels[0]} 质量评分更高 (+{a['avg_score'] - b['avg_score']:.1f}分)")
        elif b['avg_score'] > a['avg_score']:
            print(f"  🏆 {labels[1]} 质量评分更高 (+{b['avg_score'] - a['avg_score']:.1f}分)")
        else:
            print(f"  🤝 两者质量评分相同")
        print(f"\n  💡 推荐: 速度优先选 {faster}，质量优先选 {labels[0] if a['avg_score'] >= b['avg_score'] else labels[1]}")

    output = {"time": datetime.now().isoformat(), "summary": {k: {**v, "avg_latency": round(v["avg_latency"], 2)} for k, v in summary.items()}, "details": results}
    outpath = "/root/.openclaw/workspace/ai_agent/results/newapi_comparison.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  📄 结果已保存: {outpath}\n")

if __name__ == "__main__":
    main()
