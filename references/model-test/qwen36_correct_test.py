#!/usr/bin/env python3
"""
Qwen 3.6 35B 正确端点测试
使用正确的API端点进行测试
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
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "中文能力",
            "prompt": "请用中文写一段关于人工智能发展的短文，不少于200字。",
            "max_tokens": 500,
            "temperature": 0.3
        },
        {
            "name": "技术知识", 
            "prompt": "详细解释Transformer架构在自然语言处理中的应用和优势。",
            "max_tokens": 600,
            "temperature": 0.2
        },
        {
            "name": "代码能力",
            "prompt": "用Python实现一个简单的神经网络分类器，包含数据预处理、模型定义和训练过程。",
            "max_tokens": 800,
            "temperature": 0.3
        },
        {
            "name": "创意写作",
            "prompt": "写一个关于未来科技城市的短篇故事开头，要求有生动的场景描写。",
            "max_tokens": 400,
            "temperature": 0.7
        },
        {
            "name": "逻辑推理",
            "prompt": "如果明天会下雨，那么我会带伞。我今天带了伞，所以明天会下雨吗？请用逻辑推理解释。",
            "max_tokens": 300,
            "temperature": 0.2
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] 🔍 {test['name']}")
        print(f"   📝 {test['prompt'][:60]}...")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": test["prompt"]}],
            "max_tokens": test["max_tokens"],
            "temperature": test["temperature"],
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=45)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                
                response_time = round((end_time - start_time) * 1000, 2)
                token_count = usage.get('total_tokens', 0)
                
                # 评估回答质量
                quality = "🟢 优秀"
                if len(content) < 100:
                    quality = "🟡 一般"
                if "抱歉" in content or "无法" in content:
                    quality = "🔴 失败"
                
                print(f"   ✅ 成功 | 时间: {response_time}ms | Token: {token_count} | 质量: {quality}")
                
                # 显示回答摘要
                print(f"   💡 回答摘要:")
                lines = content.split('\n')
                for j, line in enumerate(lines[:4]):
                    if line.strip():
                        print(f"      {j+1}. {line.strip()[:80]}")
                if len(lines) > 4:
                    print(f"      ... (共{len(lines)}行, {len(content)}字符)")
                
                results.append({
                    "name": test["name"],
                    "success": True,
                    "time": response_time,
                    "tokens": token_count,
                    "quality": quality,
                    "content_length": len(content)
                })
                
            else:
                print(f"   ❌ 失败: HTTP {response.status_code}")
                print(f"   📄 响应: {response.text[:100]}...")
                
                results.append({
                    "name": test["name"],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ 超时: 请求超过45秒")
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
            print(f"   ❌ 错误: {e}")
            results.append({
                "name": test["name"],
                "success": False,
                "error": str(e)
            })
        
        print("   " + "-" * 50)
        time.sleep(2)  # 请求间隔
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    total_tests = len(results)
    
    if success_count > 0:
        avg_time = sum(r["time"] for r in results if r["success"]) / success_count
        avg_tokens = sum(r["tokens"] for r in results if r["success"]) / success_count
        avg_length = sum(r["content_length"] for r in results if r["success"]) / success_count
        
        print(f"✅ 成功率: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        print(f"⏱️  平均响应时间: {avg_time:.2f}ms")
        print(f"🔢 平均Token使用: {avg_tokens:.1f}")
        print(f"📝 平均回答长度: {avg_length:.0f}字符")
        
        # 质量统计
        qualities = [r["quality"] for r in results if r["success"]]
        quality_count = {}
        for q in qualities:
            quality_count[q] = quality_count.get(q, 0) + 1
        
        print(f"🎯 回答质量:")
        for quality, count in quality_count.items():
            print(f"   {quality}: {count}次")
    
    print(f"\n🔍 详细结果:")
    for result in results:
        if result["success"]:
            print(f"   {result['name']:12} | {result['time']:6}ms | {result['tokens']:4} tokens | {result['quality']}")
        else:
            print(f"   {result['name']:12} | ❌ {result['error']}")

def check_model_status():
    """检查模型状态"""
    print("🔍 检查模型状态...")
    
    api_url = "http://58.23.129.98:8001/v1/models"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ 模型服务正常")
            print("📋 可用模型:")
            for model in data.get('data', []):
                print(f"   • {model.get('id')}")
                if 'permission' in model:
                    print(f"     权限: {model['permission']}")
        else:
            print(f"❌ 模型服务异常: HTTP {response.status_code}")
            print(f"响应: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 无法连接到模型服务: {e}")

if __name__ == "__main__":
    check_model_status()
    print()
    test_qwen36()