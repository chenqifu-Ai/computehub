#!/usr/bin/env python3
"""调试 403 问题"""
import json, urllib.request, urllib.error

BASE_URL = "https://ai.zhangtuokeji.top:9090/v1"
API_KEY = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"

# 先看看有哪些模型可用
url = f"{BASE_URL}/models"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        models = data.get("data", [])
        print("可用的模型:")
        for m in models:
            print(f"  - {m.get('id', 'unknown')}")
except Exception as e:
    print(f"获取模型列表失败: {e}")

# 尝试不同模型名称
test_models = [
    "qwen3.6-35b-common",
    "qwen3.6-35b-common-turbo",
    "qwen3.6-35b",
    "qwen-plus",
    "qwen-turbo",
]

for model_name in test_models:
    url2 = f"{BASE_URL}/chat/completions"
    data = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 50
    }).encode("utf-8")
    
    req2 = urllib.request.Request(url2, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    })
    
    try:
        with urllib.request.urlopen(req2, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ [{model_name}]: '{content}'")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ [{model_name}]: HTTP {e.code} - {body[:200]}")
    except Exception as e:
        print(f"❌ [{model_name}]: {e}")
