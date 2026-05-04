#!/usr/bin/env python3
"""测试 qwen3.6-35b/qwen3.6-35b 模型"""
import urllib.request, json, time

URL = "http://58.23.129.98:8000/v1/chat/completions"
KEY = "sk-78sadn09bjawde123e"
MODEL = "qwen3.6-35b/qwen3.6-35b"  # 用户指定的模型名称

def test_model(model_name, prompt, max_tokens=4000):
    print(f"\n{'='*60}")
    print(f"🧪 测试模型: {model_name}")
    print(f"{'='*60}")
    
    h = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data, headers=h, method="POST")
    start = time.time()
    
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        elapsed = time.time() - start
        
        choice = resp["choices"][0]
        content = choice["message"].get("content", "") or ""
        reasoning = choice["message"].get("reasoning", "") or ""
        finish = choice.get("finish_reason", "?")
        usage = resp.get("usage", {})
        
        print(f"✅ 成功!")
        print(f"  ⏱️  耗时: {elapsed:.1f}s")
        print(f"  🏁 finish: {finish}")
        print(f"  📊 tokens: 总={usage.get('total_tokens')} prompt={usage.get('prompt_tokens')} comp={usage.get('completion_tokens')}")
        
        if reasoning:
            print(f"  🧠 reasoning: {len(reasoning)} 字符")
            print(f"     前200字: {reasoning[:200]}...")
        
        if content:
            print(f"  💬 回复: {content[:500]}...")
        else:
            print(f"  💬 回复: (空)")
        
        return True, content, reasoning, elapsed
        
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        error_body = e.read().decode('utf-8')
        print(f"❌ HTTP错误: {e.code}")
        print(f"  响应: {error_body[:500]}")
        return False, error_body, "", elapsed
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ 错误: {e}")
        return False, str(e), "", elapsed

# 测试1: 模型名称 qwen3.6-35b/qwen3.6-35b
ok1, c1, r1, t1 = test_model("qwen3.6-35b/qwen3.6-35b", "1+1等于几？直接回答。", max_tokens=500)

# 测试2: 如果失败，尝试标准名称 qwen3.6-35b
if not ok1:
    print("\n" + "="*60)
    print("尝试备用模型名称: qwen3.6-35b")
    ok2, c2, r2, t2 = test_model("qwen3.6-35b", "1+1等于几？直接回答。", max_tokens=500)

# 测试3: 如果成功，继续测试复杂任务
if ok1:
    test_model("qwen3.6-35b/qwen3.6-35b", 
               "用Python写一个快速排序函数，带类型注解和文档字符串。", 
               max_tokens=4000)

print("\n" + "="*60)
print("✅ 测试完成")
print("="*60)