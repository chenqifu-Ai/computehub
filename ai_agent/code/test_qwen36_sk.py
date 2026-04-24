#!/usr/bin/env python3
"""测试 qwen3.6-35b 模型 (sk- 前缀)"""
import urllib.request, json

BASE_URL = "http://58.23.129.98:8000/v1"
KEY = "sk-78sadn09bjawde123e"
headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def ask(messages, max_tokens=300):
    payload = json.dumps({"model": "qwen3.6-35b", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}).encode()
    req = urllib.request.Request(f"{BASE_URL}/v1/chat/completions", data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

print("=" * 60)
print("🧪 qwen3.6-35b 模型测试 (sk- 前缀)")
print("=" * 60)

# 测试1: 模型列表
print("\n📋 测试1: 获取模型列表")
req = urllib.request.Request(f"{BASE_URL}/v1/models", headers=headers)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())
    for m in data.get("data", []):
        print(f"  - {m['id']} (owner: {m.get('owned_by')})")

# 测试2: 简单对话
print("\n💬 测试2: 自我介绍")
resp = ask([{"role": "user", "content": "你好，请介绍你自己，3句话以内。"}])
print(f"  {resp['choices'][0]['message']['content']}")

# 测试3: 代码生成
print("\n💻 测试3: 代码生成（Python 快速排序）")
resp = ask([{"role": "user", "content": "用Python写一个快速排序函数，带注释"}])
content = resp['choices'][0]['message']['content']
print(f"  {content[:400]}{'...' if len(content)>400 else ''}")

# 测试4: 中文写作
print("\n✍️  测试4: 中文写作（ComputeHub 宣传语）")
resp = ask([{"role": "user", "content": "给一个AI算力交易平台写一句宣传语，30字以内"}])
print(f"  {resp['choices'][0]['message']['content']}")

# 测试5: 逻辑推理
print("\n🧠 测试5: 逻辑推理")
resp = ask([{"role": "user", "content": "如果一个数除以3余2，除以5余3，除以7余2，这个数最小是多少？请逐步推理"}])
print(f"  {resp['choices'][0]['message']['content']}")

# 测试6: 编程 - 算法题
print("\n🎯 测试6: 算法题（两数之和）")
resp = ask([{"role": "user", "content": "给定一个整数数组 nums 和一个目标值 target，找出数组中两个数之和等于 target 的索引。用 Python 实现并解释时间复杂度。"}])
content = resp['choices'][0]['message']['content']
print(f"  {content[:400]}{'...' if len(content)>400 else ''}")

# 测试7: 超长输出能力
print("\n📝 测试7: 长文输出（300字总结深度学习）")
resp = ask([{"role": "user", "content": "用300字左右总结深度学习的基本原理"}])
print(f"  {resp['choices'][0]['message']['content']}")

print("\n" + "=" * 60)
print("✅ 全部测试完成")
print("=" * 60)
