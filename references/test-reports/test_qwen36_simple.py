#!/usr/bin/env python3
"""Qwen 3.6 35B 简单测试"""

import requests
import json

api_url = "http://58.23.129.98:8001/v1/chat/completions"
api_key = "sk-78sadn09bjawde123e"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# 测试请求
payload = {
    "model": "qwen3.6-35b",
    "messages": [{"role": "user", "content": "你好，请用中文简单介绍一下你自己。"}],
    "max_tokens": 500,
    "temperature": 0.3,
    "stream": False
}

print("🧪 测试 Qwen 3.6 35B 模型...")
print(f"API: {api_url}")
print("-" * 60)

try:
    response = requests.post(api_url, headers=headers, json=payload, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        # 提取回复内容
        choice = result['choices'][0]
        message = choice['message']
        
        # 推理模型可能 content 为 null，内容在 reasoning 中
        content = message.get('content') or message.get('reasoning') or '无内容'
        
        print("✅ 成功!")
        print(f"📊 Token 使用：{result['usage']}")
        print(f"💬 回复:\n{content}")
    else:
        print(f"❌ 错误：{response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ 异常：{e}")
