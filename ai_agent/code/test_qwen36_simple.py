#!/usr/bin/env python3
"""qwen3.6-35b 模型简单测试"""
import urllib.request, json, time

URL = "http://58.23.129.98:8000/v1/chat/completions"
KEY = "sk-78sadn09bjawde123e"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def ask(prompt, tokens=2000, temp=0.7, label=""):
    payload = json.dumps({
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": tokens,
        "temperature": temp
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers=H, method="POST")
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    elapsed = time.time() - start
    choice = data["choices"][0]
    content = choice["message"].get("content", "") or ""
    reasoning = choice["message"].get("reasoning", "") or ""
    finish = choice.get("finish_reason", "?")
    usage = data.get("usage", {})
    print(f"--- {label} ---")
    print(f"  ⏱️  耗时: {elapsed:.1f}s  🏁 完成: {finish}")
    print(f"  📊 tokens: 总={usage.get('total_tokens')} 补={usage.get('completion_tokens')} prompt={usage.get('prompt_tokens')}")
    if reasoning:
        r_len = len(reasoning)
        print(f"  🧠 reasoning: {r_len} 字符")
        if r_len > 300:
            print(f"     前300字: {reasoning[:300]}...")
        else:
            print(f"     {reasoning}")
    if content:
        if len(content) > 400:
            print(f"  💬 回复: {content[:400]}...")
        else:
            print(f"  💬 回复: {content}")
    else:
        print("  💬 回复: (空)")
    print()
    return content, reasoning, elapsed

print("=" * 60)
print("🧪 qwen3.6-35b 简单测试")
print("=" * 60)
print()

# 测试1: 中文自我介绍
c, r, t = ask("请用三句话介绍你自己。", tokens=500, label="1. 中文自我介绍")

# 测试2: 代码生成 - 快速排序
c, r, t = ask("用Python写一个快速排序函数，带类型注解和文档字符串。", tokens=2000, temp=0.3, label="2. Python 快速排序")

# 测试3: 数学推理
c, r, t = ask("一个数除以3余2，除以5余3，除以7余2。最小是多少？请逐步推理。", tokens=2000, label="3. 数学推理 (孙子算经)")

# 测试4: 中文写作
c, r, t = ask("用200字总结量子计算的基本原理。", tokens=2000, label="4. 中文写作 (量子计算)")

# 测试5: 知识问答
c, r, t = ask("Go 语言中 goroutine 和 channel 是什么？各用50字解释。", tokens=1000, label="5. 编程知识 (Go 语言)")

# 测试6: 创意写作
c, r, t = ask("用50字写一首关于星空的短诗。", tokens=500, label="6. 创意写作 (短诗)")

print("=" * 60)
print("✅ 测试完成")
print("=" * 60)
