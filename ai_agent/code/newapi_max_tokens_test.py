#!/usr/bin/env/python3
"""NewAPI max_tokens 对比测试"""

import requests
import json
import time
from datetime import datetime

KEY = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"
BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
MODEL = "qwen3.6-35b-common"

PROMPTS = [
    ("数学推理", "鸡兔同笼，35头94脚，鸡兔各多少？"),
    ("代码生成", "Python写快速排序，含类型注解和单元测试。"),
    ("创意写作", "200字AI觉醒故事，要有反转。"),
    ("逻辑分析", "所有猫会爬树，汤姆是猫，汤姆能爬树？分析。"),
    ("数据分析", "Q1-Q4营收100/150/130/200万，算增长率并分析。"),
    ("伦理判断", "自动驾驶撞行人还是撞墙？伦理学分析。"),
    ("知识问答", "500字解释量子计算，含原理和应用。"),
    ("总结概括", "300字总结《三体》核心思想并评价。"),
]

MAX_TOKENS_LIST = [2048, 4096, 8192, 16384]
RESULTS = {}

print(f"\n{'='*120}")
print(f"  🔥 NewAPI max_tokens 对比测试")
print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*120}\n")

for max_tok in MAX_TOKENS_LIST:
    print(f"{'─'*120}")
    print(f"  max_tokens = {max_tok}")
    print(f"{'─'*120}")
    
    task_results = []
    all_lats = []
    content_empty_count = 0
    total_content = 0
    total_reasoning = 0
    
    for name, prompt in PROMPTS:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {KEY}"
        }
        body = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tok,
            "temperature": 0.7
        }
        start = time.perf_counter()
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=300)
            lat = (time.perf_counter() - start) * 1000
            
            if r.status_code != 200:
                print(f"    ❌ {name}: HTTP {r.status_code} ({lat:.0f}ms)")
                task_results.append({"name": name, "success": False, "lat": lat})
                continue
            
            data = r.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""
            finish = data["choices"][0].get("finish_reason", "?")
            usage = data.get("usage", {})
            
            # 判断 finish 原因
            if finish == "length":
                if len(reasoning) > max_tok * 0.8:
                    finish_note = "reasoning占满"
                else:
                    finish_note = "内容截断"
            else:
                finish_note = "正常停止"
            
            icon = "⚡" if lat < 10000 else ("🔵" if lat < 20000 else ("🟠" if lat < 30000 else "🐌"))
            status_str = f"{icon} ⏱{lat:.0f}ms | 📏{len(content)}字 🧠{len(reasoning)}字 | {finish_note}"
            print(f"    {name}: {status_str}")
            
            task_results.append({
                "name": name,
                "success": True,
                "lat": lat,
                "content_len": len(content),
                "reasoning_len": len(reasoning),
                "finish": finish,
                "finish_note": finish_note,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            })
            
            all_lats.append(lat)
            total_content += len(content)
            total_reasoning += len(reasoning)
            if len(content) == 0:
                content_empty_count += 1
                
        except Exception as e:
            lat = (time.perf_counter() - start) * 1000
            print(f"    ❌ {name}: {str(e)[:50]} ({lat:.0f}ms)")
            task_results.append({"name": name, "success": False, "lat": lat})
    
    # 统计
    successes = sum(1 for t in task_results if t["success"])
    avg_lat = sum(all_lats) / len(all_lats) if all_lats else 0
    min_lat = min(all_lats) if all_lats else 0
    max_lat = max(all_lats) if all_lats else 0
    avg_content = total_content / max(successes, 1)
    avg_reasoning = total_reasoning / max(successes, 1)
    avg_content_tokens = sum(t.get("completion_tokens", 0) for t in task_results if t["success"]) / max(successes, 1)
    
    RESULTS[max_tok] = {
        "successes": successes,
        "total": len(PROMPTS),
        "avg_latency": avg_lat,
        "min_latency": min_lat,
        "max_latency": max_lat,
        "content_empty": content_empty_count,
        "avg_content": avg_content,
        "avg_reasoning": avg_reasoning,
        "avg_completion_tokens": avg_content_tokens,
        "tasks": task_results,
    }
    
    print(f"\n  📊 统计: {successes}/{len(PROMPTS)} 成功 | 平均 {avg_lat:.0f}ms | 范围 {min_lat:.0f}-{max_lat:.0f}ms")
    print(f"       content: 平均{avg_content:.0f}字 (空{content_empty_count}次) | reasoning: 平均{avg_reasoning:.0f}字 | 平均{avg_content_tokens:.0f} token")

# 汇总对比
print(f"\n\n{'='*120}")
print(f"  📋 max_tokens 对比汇总")
print(f"{'='*120}")
print(f"{'max_tok':>8s} | {'成功':>6s} | {'平均延迟':>10s} | {'延迟范围':>18s} | {'content空':>8s} | {'avg_content':>12s} | {'avg_reasoning':>14s} | {'avg_tokens':>10s}")
print(f"{'─'*120}")
for max_tok in MAX_TOKENS_LIST:
    r = RESULTS[max_tok]
    print(f"{max_tok:>8d} | {r['successes']:>6d}/{r['total']} | {r['avg_latency']:>9.0f}ms | {r['min_latency']:>9.0f}-{r['max_latency']:>9.0f}ms | {r['content_empty']:>8d} | {r['avg_content']:>11.0f}字 | {r['avg_reasoning']:>13.0f}字 | {r['avg_completion_tokens']:>9.1f}")

# 详细 per-task 对比
print(f"\n{'='*120}")
print(f"  📊 每个任务的详细对比")
print(f"{'='*120}")
print(f"{'任务':>10s} | {'2048-lat':>10s} {'2048-content':>14s} | {'4096-lat':>10s} {'4096-content':>14s} | {'8192-lat':>10s} {'8192-content':>14s} | {'16384-lat':>12s} {'16384-content':>16s}")
print(f"{'─'*120}")

for prompt_name, _ in PROMPTS:
    row = f"{prompt_name:>10s}"
    for max_tok in MAX_TOKENS_LIST:
        task_data = next((t for t in RESULTS[max_tok]["tasks"] if t.get("name") == prompt_name), None)
        if task_data and task_data["success"]:
            lat_str = f"{task_data['lat']/1000:.1f}s"
            content_str = f"{task_data['content_len']}字"
            row += f" | {lat_str:>10s} {content_str:>14s}"
        else:
            row += f" | {'❌':>10s} {'N/A':>14s}"
    print(row)

print(f"{'='*120}")

# 结论
print(f"\n  📝 关键发现:")
best_content_tok = max(RESULTS.items(), key=lambda x: x[1]['avg_content'])
fastest = min(RESULTS.items(), key=lambda x: x[1]['avg_latency'] if x[1]['successes'] > 0 else 999999)
cleanest = min(RESULTS.items(), key=lambda x: x[1]['content_empty'])
print(f"    - 输出最多: max_tokens={best_content_tok[0]} (平均{best_content_tok[1]['avg_content']:.0f}字)")
print(f"    - 速度最快: max_tokens={fastest[0]} (平均{fastest[1]['avg_latency']/1000:.1f}s)")
print(f"    - content最稳: max_tokens={cleanest[0]} (仅{cleanest[1]['content_empty']}次为空)")
print(f"{'='*120}\n")
