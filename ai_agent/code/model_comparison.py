#!/usr/bin/env python3
"""
模型比对测试: NewAPI qwen3.6-35b-common vs 旧版 qwen3.6-35b
使用 requests 直接调用 OpenAI 兼容 API
"""

import requests
import json
import time
from datetime import datetime

# ============ 配置 ============
ENDPOINTS = {}

# NewAPI - 当前主力
NEWAPI_URL = "https://ai.zhangtuokeji.top:9090/v1/chat/completions"
NEWAPI_KEY = "sk-08XEevM6SdeMbvh273pmAiOZ9cZWJ3vKJELhpEMCNb7aMX6F"
ENDPOINTS["NewAPI (主力)"] = {
    "url": NEWAPI_URL,
    "api_key": NEWAPI_KEY,
    "model": "qwen3.6-35b-common",
}

# 旧版 58.23
OLD_URL = "http://58.23.129.98:8000/v1/chat/completions"
OLD_KEY = "sk-78sadn09bjawde123e"
ENDPOINTS["旧版 58.23"] = {
    "url": OLD_URL,
    "api_key": OLD_KEY,
    "model": "qwen3.6-35b",
}

# 测试题目
TEST_PROMPTS = [
    {
        "name": "🧮 数学推理",
        "prompt": "鸡兔同笼，共35个头，94只脚。问鸡和兔各有多少只？请给出详细解题步骤。",
    },
    {
        "name": "💻 代码生成",
        "prompt": "用Python写一个快速排序算法，要求：1) 有类型注解 2) 有单元测试 3) 处理边界情况",
    },
    {
        "name": "📝 创意写作",
        "prompt": "用200字以内写一个关于AI觉醒的微型科幻故事，要求有反转。",
    },
    {
        "name": "🔍 逻辑分析",
        "prompt": "以下论证是否成立？请分析：因为所有猫都会爬树，汤姆是一只猫，所以汤姆一定能爬树。",
    },
    {
        "name": "📊 数据分析",
        "prompt": "某公司2025年Q1-Q4营收分别为100万、150万、130万、200万。请计算季度环比增长率、年度增长率并分析趋势。",
    },
    {
        "name": "⚖️ 伦理判断",
        "prompt": "自动驾驶汽车面临困境：要么撞行人，要么转向撞墙导致乘客死亡。如何决策？从伦理学角度分析。",
    },
    {
        "name": "📖 知识问答",
        "prompt": "请用500字左右解释什么是量子计算，包括基本原理、应用场景和当前发展水平。",
    },
    {
        "name": "🎯 总结概括",
        "prompt": "请用300字总结《三体》的核心思想，并评价其科学价值。",
    },
]

def call_api(label, cfg, prompt, max_tokens=2048):
    """调用API，返回 (content, latency_ms, token_usage, error)"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    }
    body = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    try:
        start = time.perf_counter()
        resp = requests.post(cfg["url"], headers=headers, json=body, timeout=120)
        latency = (time.perf_counter() - start) * 1000
        if resp.status_code != 200:
            err_text = resp.text[:300]
            return None, latency, None, f"HTTP {resp.status_code}: {err_text}"
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        if not content:
            return "(content为null)", latency, data.get("usage", {}), None
        usage = data.get("usage", {})
        return content, latency, usage, None
    except requests.Timeout:
        elapsed = (time.perf_counter() - start) * 1000
        return None, elapsed, None, "超时 (>120s)"
    except requests.ConnectionError as e:
        return None, 0, None, f"连接失败: {e}"
    except Exception as e:
        return None, 0, None, f"异常: {type(e).__name__}: {e}"


def quality_score(text, prompt_name):
    """简单启发式评分"""
    if not text or len(text) < 10:
        return 0
    score = 0
    # 长度分
    if len(text) > 100: score += 15
    if len(text) > 300: score += 10
    # 结构化
    if any(c in text for c in ["1.", "2.", "3.", "- ", "•", "首先", "其次"]): score += 15
    # 分析深度
    if any(w in text for w in ["分析", "原因", "因为", "结论", "总结", "因此"]): score += 15
    # 格式
    if "```" in text: score += 15
    # 特殊
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
    print(f"\n{'='*75}")
    print(f"  🤖 模型比对测试: NewAPI qwen3.6-35b-common vs 旧版 qwen3.6-35b")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*75}")

    # 连通性测试
    print(f"\n  🔌 连通性测试:")
    for label, cfg in ENDPOINTS.items():
        content, latency, usage, error = call_api(label, cfg, "回复:OK", max_tokens=10)
        if not error:
            status = "✅"
            msg = f"ok ({content.strip()})"
        else:
            status = "❌"
            msg = f"{error[:80]}"
        print(f"    {status} {label}: {msg} ({latency:.0f}ms)")

    # 运行测试
    results = {label: [] for label in ENDPOINTS}

    for i, test in enumerate(TEST_PROMPTS, 1):
        print(f"\n  {'─'*75}")
        print(f"  测试 {i}/{len(TEST_PROMPTS)}: {test['name']}")
        print(f"    提示: {test['prompt'][:70]}...")

        for label in ENDPOINTS:
            cfg = ENDPOINTS[label]
            content, latency, usage, error = call_api(label, cfg, test["prompt"])

            if error:
                print(f"    ❌ {label}: {error[:80]}")
                results[label].append({
                    "prompt": test["name"], "success": False,
                    "error": error, "latency": latency,
                    "tokens": 0, "score": 0, "text": ""
                })
            else:
                text_len = len(content) if content else 0
                score = quality_score(content, test["name"])
                tokens = usage.get("total_tokens", 0) if usage else 0
                status_icon = "🐌" if latency > 10000 else ("⚡" if latency < 2000 else "🔵")
                print(f"    {status_icon} {label}: ⏱{latency:.0f}ms | 📏{text_len}字 | 🏆{score}分 | 🔤{tokens}tokens")
                results[label].append({
                    "prompt": test["name"], "success": True,
                    "latency": latency, "tokens": tokens,
                    "score": score, "text": content[:300]
                })

    # 汇总
    print(f"\n{'='*75}")
    print("  📊 综合评分")
    print(f"{'='*75}")
    print(f"\n  {'模型':<16} {'成功率':>8} {'平均响应':>12} {'平均分':>8} {'总token':>10}")
    print(f"  {'─'*58}")

    summary = {}
    for label in ENDPOINTS:
        successes = [r for r in results[label] if r["success"]]
        total = len(TEST_PROMPTS)
        if not successes:
            summary[label] = {"avg_latency": 0, "avg_score": 0, "success_rate": 0, "total_tokens": 0, "success_count": 0}
            print(f"  {label:<16} {0:>6.0f}% {'--':>10} {0:>7.1f}分 {0:>8}")
            continue
        avg_lat = sum(r["latency"] for r in successes) / len(successes)
        avg_score = sum(r["score"] for r in successes) / len(successes)
        total_tok = sum(r["tokens"] for r in successes)
        summary[label] = {
            "avg_latency": avg_lat, "avg_score": avg_score,
            "success_rate": len(successes)/total*100, "total_tokens": total_tok,
            "success_count": len(successes)
        }
        print(f"  {label:<16} {len(successes)/total*100:>6.0f}% {avg_lat:>10.0f}ms {avg_score:>7.1f}分 {total_tok:>8}")

    # 逐题对比
    print(f"\n  {'测试项':<18} {'NewAPI':>30} {'旧版 58.23':>30}")
    print(f"  {'─'*78}")
    for i, test in enumerate(TEST_PROMPTS):
        print(f"  {test['name']:<16}", end="")
        for model_key in ENDPOINTS:
            r = results[model_key][i]
            if r["success"]:
                print(f" ⏱{r['latency']:.0f}ms 🏆{r['score']} |{r['text'][:25]}...", end="")
            else:
                err = r.get('error', 'error')[:20] if isinstance(r.get('error'), str) else 'error'
                print(f" ❌{err}", end="")
        print()

    # 结论
    print(f"\n{'='*75}")
    print("  📝 结论")
    print(f"{'='*75}")

    active = {k: v for k, v in summary.items() if v["success_count"] > 0}
    if active:
        if len(active) >= 2:
            labels = list(active.keys())
            a, b = active[labels[0]], active[labels[1]]
            if a["avg_latency"] > 0 and b["avg_latency"] > 0:
                if a["avg_latency"] < b["avg_latency"]:
                    fastest, slowest = labels[0], labels[1]
                    ratio = b["avg_latency"] / a["avg_latency"]
                else:
                    fastest, slowest = labels[1], labels[0]
                    ratio = a["avg_latency"] / b["avg_latency"]
                print(f"\n  ⚡ {fastest} 比 {slowest} 快 {ratio:.2f}x")

            if summary["NewAPI (主力)"]["avg_score"] > summary["旧版 58.23"]["avg_score"]:
                diff = summary["NewAPI (主力)"]["avg_score"] - summary["旧版 58.23"]["avg_score"]
                print(f"  🏆 NewAPI 质量评分更高 (+{diff:.1f}分)")
            elif summary["旧版 58.23"]["avg_score"] > summary["NewAPI (主力)"]["avg_score"]:
                diff = summary["旧版 58.23"]["avg_score"] - summary["NewAPI (主力)"]["avg_score"]
                print(f"  🏆 旧版 质量评分更高 (+{diff:.1f}分)")

    if summary.get("NewAPI (主力)", {}).get("success_count", 0) == 0:
        print(f"\n  ⚠️  NewAPI 返回 401 错误，API Key 可能已过期")
        print(f"     请更新 AI 配置中的 NewAPI Key")

    print(f"\n{'='*75}\n")

    # 保存详细结果
    output = {
        "time": datetime.now().isoformat(),
        "summary": {k: {**v, "avg_latency": round(v["avg_latency"], 2)} for k, v in summary.items()},
        "details": results,
    }
    result_path = "/root/.openclaw/workspace/ai_agent/results/model_comparison.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  📄 详细结果已保存: {result_path}\n")


if __name__ == "__main__":
    main()
