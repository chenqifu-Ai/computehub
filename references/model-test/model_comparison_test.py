#!/usr/bin/env python3
"""
模型能力对比测试 - 使用本地可用模型进行测试
"""

import subprocess
import json
import time

def test_local_model(model_name, prompt):
    """测试本地Ollama模型"""
    try:
        start_time = time.time()
        
        result = subprocess.run([
            'ollama', 'run', model_name, prompt
        ], capture_output=True, text=True, timeout=60)
        
        response_time = (time.time() - start_time) * 1000
        
        if result.returncode == 0:
            return {
                'success': True,
                'response': result.stdout.strip(),
                'time_ms': response_time,
                'error': None
            }
        else:
            return {
                'success': False,
                'response': None,
                'time_ms': response_time,
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'response': None,
            'time_ms': 60000,
            'error': 'Timeout after 60 seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'response': None,
            'time_ms': 0,
            'error': str(e)
        }

def run_comprehensive_test():
    """运行全面能力测试"""
    
    test_cases = [
        {
            'name': '语言理解',
            'prompt': '请用中文、英文、法文三种语言说"你好，世界！"',
            'expected': '多语言能力'
        },
        {
            'name': '代码生成',
            'prompt': '用Python写一个函数，计算斐波那契数列的第n项',
            'expected': '代码正确性'
        },
        {
            'name': '逻辑推理',
            'prompt': '如果所有的猫都会爬树，而Tom是一只猫，那么Tom会爬树吗？请用逻辑推理说明',
            'expected': '逻辑推理能力'
        },
        {
            'name': '知识问答',
            'prompt': '请简要介绍人工智能的发展历史',
            'expected': '知识准确性'
        },
        {
            'name': '创意写作',
            'prompt': '写一个关于机器人和人类成为朋友的短故事开头（100字以内）',
            'expected': '创造性'
        }
    ]
    
    # 可用的本地模型
    local_models = [
        'qwen2.5:3b',
        'qwen2.5:latest', 
        'glm-4.7-flash:latest'
    ]
    
    print("🤖 本地模型能力对比测试")
    print("=" * 70)
    
    results = {}
    
    for model in local_models:
        print(f"\n🔍 测试模型: {model}")
        print("-" * 50)
        
        model_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"  测试 {i}/5: {test_case['name']}")
            
            result = test_local_model(model, test_case['prompt'])
            
            if result['success']:
                print(f"    ✅ 成功! ({result['time_ms']:.0f}ms)")
                print(f"      响应: {result['response'][:80]}...")
                model_results.append({
                    'test': test_case['name'],
                    'status': '✅',
                    'time_ms': result['time_ms'],
                    'response_length': len(result['response'])
                })
            else:
                print(f"    ❌ 失败: {result['error']}")
                model_results.append({
                    'test': test_case['name'],
                    'status': '❌',
                    'time_ms': result['time_ms'],
                    'error': result['error']
                })
        
        results[model] = model_results
    
    # 生成测试报告
    print("\n" + "=" * 70)
    print("📊 测试总结报告")
    print("=" * 70)
    
    for model, model_results in results.items():
        success_count = sum(1 for r in model_results if r['status'] == '✅')
        total_time = sum(r['time_ms'] for r in model_results if 'time_ms' in r)
        
        print(f"\n🤖 {model}:")
        print(f"   通过率: {success_count}/5 ({success_count/5*100:.1f}%)")
        print(f"   总耗时: {total_time/1000:.1f}s")
        
        for result in model_results:
            status = result['status']
            if status == '✅':
                print(f"     {status} {result['test']}: {result['time_ms']:.0f}ms, {result['response_length']}字符")
            else:
                print(f"     {status} {result['test']}: 失败")

if __name__ == "__main__":
    run_comprehensive_test()