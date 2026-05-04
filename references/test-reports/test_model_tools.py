#!/usr/bin/env python3
"""测试本地模型是否支持工具调用"""

import json
import requests
import time

OLLAMA_URL = "http://127.0.0.1:11434"

# 测试用的工具定义
test_tools = {
    "type": "function",
    "function": {
        "name": "test_function",
        "description": "测试函数",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "测试消息"
                }
            },
            "required": ["message"]
        }
    }
}

# 测试消息
test_messages = [
    {
        "role": "user",
        "content": "请调用test_function函数，参数message为'hello'"
    }
]

def test_model(model_name):
    """测试模型是否支持工具调用"""
    print(f"\n测试模型: {model_name}")
    print("-" * 50)

    try:
        # 构建请求
        payload = {
            "model": model_name,
            "messages": test_messages,
            "tools": [test_tools],
            "stream": False
        }

        # 发送请求
        response = requests.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 状态码: {response.status_code}")

            # 检查是否有工具调用
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "tool_calls" in choice.get("message", {}):
                    print(f"✅ 支持工具调用: {choice['message']['tool_calls']}")
                    return True
                else:
                    print(f"❌ 不支持工具调用")
                    print(f"   响应内容: {choice.get('message', {}).get('content', '')[:100]}")
                    return False
            else:
                print(f"⚠️  响应格式异常")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("本地模型工具调用支持测试")
    print("=" * 60)

    # 获取可用模型列表
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]

            print(f"\n找到 {len(models)} 个模型:")
            for model in models:
                print(f"  - {model}")

            print("\n开始测试...")
            print("=" * 60)

            # 测试每个模型
            results = {}
            for model in models:
                results[model] = test_model(model)
                time.sleep(1)  # 避免请求过快

            # 汇总结果
            print("\n" + "=" * 60)
            print("测试结果汇总")
            print("=" * 60)

            supported = [m for m, ok in results.items() if ok]
            not_supported = [m for m, ok in results.items() if not ok]

            if supported:
                print(f"\n✅ 支持工具调用的模型 ({len(supported)}):")
                for model in supported:
                    print(f"  - {model}")

            if not_supported:
                print(f"\n❌ 不支持工具调用的模型 ({len(not_supported)}):")
                for model in not_supported:
                    print(f"  - {model}")

            print("\n" + "=" * 60)
            print("建议:")
            if supported:
                print(f"使用: {supported[0]}")
            else:
                print("所有本地模型都不支持工具调用，建议使用云端模型")
            print("=" * 60)

        else:
            print(f"❌ 获取模型列表失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 异常: {str(e)}")

if __name__ == "__main__":
    main()