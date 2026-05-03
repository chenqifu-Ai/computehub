#!/usr/bin/env python3
"""
qwen3.6-35b 全方位压力 & 性能测试
目标: 58.23.129.98:8000 (vLLM)
"""

import requests
import json
import time
import concurrent.futures
import statistics
import sys

BASE_URL = "http://58.23.129.98:8000/v1"
API_KEY = "sk-78sadn09bjawde123e"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# ========== 测试套件 ==========

results = []

def report(name, status, detail, time_s=None):
    icon = "✅" if status == "OK" else "❌"
    t_str = f" [{time_s:.2f}s]" if time_s else ""
    print(f"  {icon} {name}{t_str}: {detail}")
    results.append({"name": name, "status": status, "detail": detail, "time_s": time_s})

def chat(prompt, max_tokens=256, temperature=0.7):
    """发送单次对话请求"""
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }
    start = time.time()
    resp = requests.post(f"{BASE_URL}/chat/completions", json=payload, headers=HEADERS, timeout=120)
    elapsed = time.time() - start
    data = resp.json()
    msg = data["choices"][0]["message"] if "choices" in data else {}
    content = msg.get("content") or msg.get("reasoning") or str(data)
    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    return content, elapsed, tokens_in, tokens_out

def chat_stream(prompt, max_tokens=256):
    """流式对话测试"""
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": True
    }
    start = time.time()
    resp = requests.post(f"{BASE_URL}/chat/completions", json=payload, headers=HEADERS, timeout=120, stream=True)
    text = ""
    first_token_time = None
    for line in resp.iter_lines():
        if line:
            line = line.decode("utf-8").strip()
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    # vLLM may put output in reasoning field
                    content_piece = delta.get("content") or delta.get("reasoning") or ""
                    if content_piece:
                        if first_token_time is None:
                            first_token_time = time.time()
                        text += content_piece
                except:
                    pass
    elapsed = time.time() - start
    ttft = (first_token_time - start) if first_token_time else None
    return text, elapsed, ttft

# ========== 测试 1: 基础推理 ==========
print("\n📦 [1/6] 基础推理测试")
print("-" * 50)

t1_start = time.time()
content, elapsed, tin, tout = chat("请用一句话介绍杭州这座城市。")
report("单次对话", "OK", f"{tin}→{tout} tokens, 输出: \"{content[:50]}...\"", elapsed)

# 中文翻译
content, elapsed, tin, tout = chat("Translate to English: 人工智能正在改变世界，深度学习模型的发展尤其迅速。", max_tokens=100)
report("中译英", "OK", f"{tin}→{tout} tokens, \"{content[:60]}...\"", elapsed)

# 英文回复
content, elapsed, tin, tout = chat("What is the capital of France? Answer in one word.", max_tokens=20, temperature=0.1)
report("英文问答", "OK", f"{tin}→{tout} tokens, 输出: \"{content.strip()}\"", elapsed)

# ========== 测试 2: 流式 & TTFT ==========
print("\n📦 [2/6] 流式 & 首Token延迟(TTFT)")
print("-" * 50)

text, elapsed, ttft = chat_stream("写一首关于春天的五言绝句。")
report("流式生成", "OK", f"总耗时 {elapsed:.2f}s, 首Token延迟 {ttft:.2f}s", elapsed)
report("首Token延迟(TTFT)", "OK" if ttft and ttft < 5 else "慢", f"{ttft:.2f}s (目标 <5s)")

# ========== 测试 3: 长上下文 ==========
print("\n📦 [3/6] 长上下文处理")
print("-" * 50)

long_text = "人工智能" * 5000  # ~15000字/15000 tokens
content, elapsed, tin, tout = chat(f"请总结以下文字的核心主题（用一句话）：{long_text[:5000]}", max_tokens=100)
report("长输入(5k tokens)", "OK" if elapsed < 120 else "慢", f"{tin} tokens 输入, {tout} tokens 输出", elapsed)

# ========== 测试 4: 复杂推理 ==========
print("\n📦 [4/6] 复杂推理能力")
print("-" * 50)

reasoning_prompt = """有一个3升的水壶和一个5升的水壶，如何准确量出4升水？请逐步推理。"""
content, elapsed, tin, tout = chat(reasoning_prompt, max_tokens=512, temperature=0.3)
has_step = "步骤" in content or "step" in content.lower() or "1." in content or "首先" in content
report("逻辑推理(水壶问题)", "OK" if has_step else "一般", f"{tin}→{tout} tokens, 含步骤推理", elapsed)

math_prompt = """一个等差数列的首项为3，公差为4，前n项和为255。求n的值。请写出计算过程。"""
content, elapsed, tin, tout = chat(math_prompt, max_tokens=512, temperature=0.3)
report("数学计算(等差数列)", "OK" if "255" in content and ("n" in content or "项" in content) else "检查", f"{tin}→{tout} tokens", elapsed)

# ========== 测试 5: 代码生成 ==========
print("\n📦 [5/6] 代码生成")
print("-" * 50)

code_prompt = """用Python写一个函数，实现快速排序算法。要求包含注释和类型注解。"""
content, elapsed, tin, tout = chat(code_prompt, max_tokens=512, temperature=0.2)
has_function = "def " in content and ("quicksort" in content.lower() or "快速" in content or "quick_sort" in content)
has_type_hint = ":" in content and "List" in content or "int" in content
report("代码生成(快速排序)", "OK" if has_function else "不完整", f"{tin}→{tout} tokens, 含函数定义: {has_function}", elapsed)

# ========== 测试 6: 并发压力 ==========
print("\n📦 [6/6] 并发压力测试")
print("-" * 50)

def concurrent_request(n):
    prompts = [
        "What is 2+2?", "什么是深度学习?", "Write a haiku.", "请介绍上海。", "1+1=?",
        "Python list comprehension example.", "What is the speed of light?", "杜甫最著名的诗?",
        "Explain TCP/IP in simple terms.", "写一句关于月亮的诗。"
    ]
    prompt = prompts[n % len(prompts)]
    try:
        c, t, _, _ = chat(prompt, max_tokens=50, temperature=0.5)
        return "OK", t, len(c)
    except Exception as e:
        return "FAIL", 0, str(e)

for concurrency in [3, 5, 10]:  # 先测3/5/10并发
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(concurrent_request, i) for i in range(concurrency)]
        done = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_time = time.time() - start
    success = sum(1 for d in done if d[0] == "OK")
    avg_time = statistics.mean([d[1] for d in done if d[0] == "OK"])
    status = "OK" if success == concurrency else f"{success}/{concurrency}成功"
    report(f"并发{concurrency}路", status, f"总耗时{total_time:.2f}s, 平均请求{avg_time:.2f}s", total_time)

# ========== 总结 ==========
print("\n" + "=" * 60)
print("📊 测试总结")
print("=" * 60)

total_ok = sum(1 for r in results if r["status"] == "OK")
total_warn = sum(1 for r in results if r["status"] not in ["OK", "❌"])
print(f"\n总测试项: {len(results)}")
print(f"通过: {total_ok} ✅")
print(f"异常/警告: {len(results) - total_ok}")

for r in results:
    icon = "✅" if r["status"] == "OK" else "⚠️" if r["status"] not in ["OK", "❌"] else "❌"
    t = f" [{r['time_s']:.2f}s]" if r['time_s'] else ""
    print(f"{icon} {r['name']}{t}")

print("\n✅ 测试完成")
