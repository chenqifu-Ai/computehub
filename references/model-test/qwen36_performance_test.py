#!/usr/bin/env python3
"""
Qwen 3.6 35B模型性能全面测试
"""

import requests
import json
import time
import statistics

def performance_test():
    """全面性能测试"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 不同长度的测试问题
    test_cases = [
        {
            "name": "短问题",
            "message": "你好，请简单介绍一下自己"
        },
        {
            "name": "中等问题", 
            "message": "请用中文详细介绍一下Qwen 3.6模型的技术特点和优势，包括参数规模、训练数据、支持的语言能力等"
        },
        {
            "name": "代码问题",
            "message": "请用Python写一个快速排序算法的实现，并添加详细注释"
        }
    ]
    
    results = []
    
    print("🚀 开始Qwen 3.6 35B模型性能全面测试...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"💬 问题: {test_case['message']}")
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": test_case['message']}],
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            end_time = time.time()
            
            response_time = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get('usage', {})
                
                result_data = {
                    "test_case": test_case['name'],
                    "success": True,
                    "response_time": response_time,
                    "prompt_tokens": usage.get('prompt_tokens', 0),
                    "completion_tokens": usage.get('completion_tokens', 0),
                    "total_tokens": usage.get('total_tokens', 0),
                    "tokens_per_second": round(usage.get('completion_tokens', 0) / (response_time / 1000), 2) if response_time > 0 else 0
                }
                
                print(f"✅ 成功 | 时间: {response_time}ms | Token: {result_data['total_tokens']} | 速度: {result_data['tokens_per_second']} token/s")
                
            else:
                result_data = {
                    "test_case": test_case['name'],
                    "success": False,
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}"
                }
                print(f"❌ 失败 | 错误: {result_data['error']}")
                
        except Exception as e:
            result_data = {
                "test_case": test_case['name'],
                "success": False,
                "response_time": 0,
                "error": str(e)
            }
            print(f"❌ 异常 | 错误: {e}")
        
        results.append(result_data)
        time.sleep(2)  # 短暂休息
    
    # 统计结果
    print("\n" + "=" * 60)
    print("📊 性能测试结果汇总")
    print("=" * 60)
    
    successful_tests = [r for r in results if r['success']]
    
    if successful_tests:
        avg_response_time = statistics.mean([r['response_time'] for r in successful_tests])
        avg_tokens_per_sec = statistics.mean([r['tokens_per_second'] for r in successful_tests])
        total_tokens = sum([r['total_tokens'] for r in successful_tests])
        
        print(f"✅ 成功测试: {len(successful_tests)}/{len(test_cases)}")
        print(f"⏱️  平均响应时间: {avg_response_time:.2f}ms")
        print(f"⚡ 平均生成速度: {avg_tokens_per_sec:.2f} token/s")
        print(f"📈 总Token消耗: {total_tokens}")
        
        print("\n🔍 详细结果:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            if result['success']:
                print(f"{status} {result['test_case']}: {result['response_time']}ms, {result['tokens_per_second']} token/s")
            else:
                print(f"{status} {result['test_case']}: 失败 - {result['error']}")
    else:
        print("❌ 所有测试都失败了")
        
    return results

if __name__ == "__main__":
    performance_test()