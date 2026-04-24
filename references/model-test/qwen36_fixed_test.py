#!/usr/bin/env python3
"""
Qwen 3.6 35B 修复测试
处理API响应格式问题
"""

import requests
import json
import time

def test_qwen36():
    """测试Qwen 3.6 35B模型"""
    
    api_url = "http://58.23.129.98:8001/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    model_name = "qwen3.6-35b"
    
    print("🧪 Qwen 3.6 35B 模型测试")
    print("=" * 60)
    print(f"API端点: {api_url}")
    print(f"模型: {model_name}")
    print("=" * 60)
    
    # 更简单的测试用例
    test_cases = [
        {
            "name": "基础问候",
            "prompt": "你好，请简单介绍一下你自己。",
            "max_tokens": 100,
            "temperature": 0.3
        },
        {
            "name": "简单问答", 
            "prompt": "什么是机器学习？",
            "max_tokens": 150,
            "temperature": 0.3
        },
        {
            "name": "中文测试",
            "prompt": "用中文回答：人工智能有哪些应用领域？",
            "max_tokens": 200,
            "temperature": 0.3
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] 🔍 {test['name']}")
        print(f"   📝 {test['prompt']}")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": test["prompt"]}],
            "max_tokens": test["max_tokens"],
            "temperature": test["temperature"],
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            end_time = time.time()
            
            print(f"   📡 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   📊 响应格式: JSON (有效)")
                    
                    # 检查响应结构
                    if 'choices' in result and len(result['choices']) > 0:
                        choice = result['choices'][0]
                        if 'message' in choice and 'content' in choice['message']:
                            content = choice['message']['content']
                            usage = result.get('usage', {})
                            
                            response_time = round((end_time - start_time) * 1000, 2)
                            token_count = usage.get('total_tokens', 0)
                            
                            print(f"   ✅ 成功 | 时间: {response_time}ms | Token: {token_count}")
                            print(f"   💡 回答: {content[:100]}...")
                            
                            results.append({
                                "name": test["name"],
                                "success": True,
                                "time": response_time,
                                "tokens": token_count,
                                "content": content
                            })
                        else:
                            print(f"   ❌ 响应格式错误: 缺少message/content")
                            print(f"   📄 响应: {result}")
                            results.append({
                                "name": test["name"],
                                "success": False,
                                "error": "Invalid response format: missing message/content"
                            })
                    else:
                        print(f"   ❌ 响应格式错误: 缺少choices")
                        print(f"   📄 响应: {result}")
                        results.append({
                            "name": test["name"],
                            "success": False,
                            "error": "Invalid response format: missing choices"
                        })
                        
                except json.JSONDecodeError:
                    print(f"   ❌ JSON解析错误")
                    print(f"   📄 原始响应: {response.text[:200]}...")
                    results.append({
                        "name": test["name"],
                        "success": False,
                        "error": "JSON decode error"
                    })
                    
            else:
                print(f"   ❌ HTTP错误: {response.status_code}")
                print(f"   📄 错误信息: {response.text[:200]}...")
                results.append({
                    "name": test["name"],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ 超时: 请求超过30秒")
            results.append({
                "name": test["name"],
                "success": False,
                "error": "Timeout"
            })
        except requests.exceptions.ConnectionError:
            print(f"   🔌 连接错误: 无法连接到服务器")
            results.append({
                "name": test["name"],
                "success": False,
                "error": "ConnectionError"
            })
        except Exception as e:
            print(f"   ❌ 未知错误: {e}")
            results.append({
                "name": test["name"],
                "success": False,
                "error": str(e)
            })
        
        print("   " + "-" * 50)
        time.sleep(1)
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    total_tests = len(results)
    
    if success_count > 0:
        avg_time = sum(r["time"] for r in results if r["success"]) / success_count
        avg_tokens = sum(r["tokens"] for r in results if r["success"]) / success_count
        
        print(f"✅ 成功率: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        print(f"⏱️  平均响应时间: {avg_time:.2f}ms")
        print(f"🔢 平均Token使用: {avg_tokens:.1f}")
        
        # 显示成功案例
        print(f"\n🎯 成功案例:")
        for result in results:
            if result["success"]:
                print(f"   {result['name']}: {result['content'][:80]}...")
    
    if total_tests - success_count > 0:
        print(f"\n❌ 失败案例:")
        for result in results:
            if not result["success"]:
                print(f"   {result['name']}: {result['error']}")

def test_api_directly():
    """直接测试API端点"""
    print("🔍 直接测试API端点...")
    
    api_url = "http://58.23.129.98:8001/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 最简单的测试
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10,
        "temperature": 0.1
    }
    
    try:
        print(f"📡 发送测试请求到: {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        
        print(f"📊 响应状态: {response.status_code}")
        print(f"📄 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ API响应正常")
                print(f"📋 响应JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError:
                print("❌ 响应不是JSON格式")
                print(f"📄 原始响应: {response.text}")
        else:
            print(f"❌ HTTP错误")
            print(f"📄 错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    test_api_directly()
    print("\n" + "=" * 60)
    test_qwen36()