#!/usr/bin/env python3
"""
使用OpenAI客户端测试Qwen API
"""

try:
    from openai import OpenAI
    
    # 配置客户端
    client = OpenAI(
        base_url="http://58.23.129.98:8001/v1",
        api_key="78sadn09bjawde123e"
    )
    
    print("🔧 使用OpenAI客户端测试...")
    
    # 测试列出模型
    try:
        models = client.models.list()
        print("✅ 成功获取模型列表:")
        for model in models.data:
            print(f"   - {model.id}")
    except Exception as e:
        print(f"❌ 获取模型列表失败: {e}")
    
    # 测试聊天完成
    try:
        completion = client.chat.completions.create(
            model="qwen3.6-35b",
            messages=[{"role": "user", "content": "你好，请说'测试成功'"}],
            max_tokens=20
        )
        print("✅ 聊天测试成功:")
        print(f"   回复: {completion.choices[0].message.content}")
    except Exception as e:
        print(f"❌ 聊天测试失败: {e}")
        
except ImportError:
    print("❌ 未安装openai库，尝试安装...")
    import subprocess
    import sys
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
        print("✅ openai库安装成功，请重新运行测试")
    except:
        print("❌ 安装openai库失败")
        
    # 回退到requests方式
    import requests
    import json
    
    print("\n🔄 回退到requests方式测试...")
    
    try:
        response = requests.post(
            "http://58.23.129.98:8001/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer 78sadn09bjawde123e"
            },
            json={
                "model": "qwen3.6-35b",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            },
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 成功!")
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        else:
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")