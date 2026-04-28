#!/usr/bin/env python3
"""qwen3.6-35b-common 全面测试"""
import time, json, urllib.request, urllib.error

BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
API_KEY = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"

def call_model(prompt, max_tokens=1024, timeout=60):
    url = f"{BASE_URL}/chat/completions"
    data = json.dumps({
        "model": "qwen3.6-35b-common",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    })
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - start
            body = json.loads(resp.read().decode("utf-8"))
            
            content = ""
            reasoning = ""
            if "choices" in body and len(body["choices"]) > 0:
                choice = body["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "") or ""
                reasoning = message.get("reasoning_content", "") or ""
            
            usage = body.get("usage", {})
            
            return {
                "elapsed": round(elapsed, 2),
                "content": content,
                "reasoning": reasoning[:300],
                "content_len": len(content),
                "usage": usage
            }
    except Exception as e:
        return {"error": str(e), "elapsed": round(time.time()-start, 2)}

tests = [
    ("用一句话解释什么是量子纠缠", "知识问答"),
    ("写一个 Python 快速排序函数", "代码生成"),
    ("北京和上海哪个城市人口更多？", "事实推理"),
    ("解释深度学习中的过拟合", "技术解释"),
    ("今天适合买比特币吗？", "建议类"),
    ("用 Python 写一个斐波那契数列", "代码生成"),
]

print("=" * 60)
print("qwen3.6-35b-common 全面测试")
print("=" * 60)

total = len(tests)
passed = 0
total_latency = 0

for i, (prompt, category) in enumerate(tests):
    print(f"\n[{i+1}/{total}] {category}: {prompt}")
    result = call_model(prompt, max_tokens=512)
    
    if "error" in result:
        print(f"  ❌ 错误: {result['error']}")
        continue
    
    print(f"  耗时: {result['elapsed']}s")
    print(f"  回复长度: {result['content_len']} chars")
    print(f"  reasoning: {'✅' if result['reasoning'] else '❌ 空'}")
    print(f"  内容: {result['content'][:120]}")
    
    total_latency += result["elapsed"]
    
    if result["content_len"] > 20:
        passed += 1
    else:
        print(f"  ⚠️  内容为空或太短")

print(f"\n{'=' * 60}")
print(f"结果: {passed}/{total} 通过")
print(f"平均耗时: {round(total_latency/total, 1)}s")
print(f"{'=' * 60}")
