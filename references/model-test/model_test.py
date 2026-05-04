#!/usr/bin/env python3
"""
DeepSeek v3.1:671B 模型详细测试脚本
测试维度：代码能力、推理能力、中文理解、创意生成、数学计算
"""

import requests
import json
import time
import sys

# 配置
OLLAMA_CLOUD_URL = "https://ollama.com"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
MODEL = "deepseek-v3.1:671b"

# 测试用例
test_cases = [
    # 代码能力测试
    {
        "category": "代码能力",
        "prompt": "用Python写一个快速排序算法，要求：\n1. 包含详细的注释\n2. 处理边界情况\n3. 提供使用示例",
        "expected": "应该生成完整的快速排序实现"
    },
    
    # 推理能力测试
    {
        "category": "推理能力", 
        "prompt": "如果所有猫都会飞，而汤姆是一只猫，那么汤姆会飞吗？请用逻辑推理解释。",
        "expected": "应该基于给定前提进行逻辑推理"
    },
    
    # 中文理解测试
    {
        "category": "中文理解",
        "prompt": "解释'塞翁失马，焉知非福'这个成语的含义，并用现代生活中的例子说明。",
        "expected": "应该准确解释成语含义并提供现代例子"
    },
    
    # 创意生成测试
    {
        "category": "创意生成",
        "prompt": "创作一个关于人工智能助手帮助人类解决环境危机的短篇故事，200字左右。",
        "expected": "应该生成有创意的完整故事"
    },
    
    # 数学计算测试
    {
        "category": "数学计算",
        "prompt": "计算：有一个直角三角形，两条直角边分别是3cm和4cm，求斜边的长度。请展示计算过程。",
        "expected": "应该正确计算斜边长度为5cm"
    },
    
    # 多轮对话测试
    {
        "category": "多轮对话",
        "prompt": "第一轮：什么是机器学习？\n第二轮：那么监督学习和无监督学习有什么区别？",
        "expected": "应该保持上下文连贯性"
    }
]

def test_model():
    """执行模型测试"""
    print(f"🧪 开始测试模型: {MODEL}")
    print(f"📡 API端点: {OLLAMA_CLOUD_URL}")
    print("=" * 60)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 测试 {i}/{len(test_cases)}: {test_case['category']}")
        print(f"📝 输入: {test_case['prompt'][:100]}...")
        
        try:
            # 准备请求
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": MODEL,
                "prompt": test_case['prompt'],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            }
            
            start_time = time.time()
            
            # 发送请求
            response = requests.post(
                f"{OLLAMA_CLOUD_URL}/api/generate",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 分析结果
                response_text = result.get('response', '')
                tokens_used = result.get('eval_count', 0)
                
                # 简单评估
                quality_score = assess_response_quality(test_case['category'], response_text)
                
                test_result = {
                    "category": test_case['category'],
                    "prompt": test_case['prompt'],
                    "response": response_text,
                    "response_time": round(response_time, 2),
                    "tokens_used": tokens_used,
                    "quality_score": quality_score,
                    "status": "success"
                }
                
                print(f"✅ 成功 | 耗时: {response_time:.2f}s | 质量: {quality_score}/10")
                
            else:
                test_result = {
                    "category": test_case['category'],
                    "prompt": test_case['prompt'],
                    "response": f"API错误: {response.status_code} - {response.text}",
                    "response_time": response_time,
                    "tokens_used": 0,
                    "quality_score": 0,
                    "status": "error"
                }
                print(f"❌ 失败 | 错误: {response.status_code}")
                
        except Exception as e:
            test_result = {
                "category": test_case['category'],
                "prompt": test_case['prompt'],
                "response": f"异常: {str(e)}",
                "response_time": 0,
                "tokens_used": 0,
                "quality_score": 0,
                "status": "exception"
            }
            print(f"⚠️ 异常: {str(e)}")
        
        results.append(test_result)
        
        # 稍微延迟避免速率限制
        time.sleep(2)
    
    return results

def assess_response_quality(category, response):
    """评估响应质量"""
    if not response or len(response.strip()) < 10:
        return 2
    
    score = 7  # 基础分
    
    # 根据类别增加评分
    if category == "代码能力":
        if "def " in response and "return " in response:
            score += 2
        if "#" in response or "\"\"\"" in response:  # 注释
            score += 1
    
    elif category == "推理能力":
        if "逻辑" in response or "推理" in response or "因为" in response:
            score += 2
    
    elif category == "中文理解":
        if "成语" in response and "例子" in response:
            score += 2
    
    elif category == "创意生成":
        if len(response) > 100:  # 足够长度
            score += 2
        if "人工智能" in response and "环境" in response:
            score += 1
    
    elif category == "数学计算":
        if "5" in response and ("cm" in response or "厘米" in response):
            score += 3
    
    # 限制最高分
    return min(score, 10)

def generate_report(results):
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("📊 测试报告汇总")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['status'] == 'success')
    avg_response_time = sum(r['response_time'] for r in results if r['status'] == 'success') / successful_tests if successful_tests > 0 else 0
    avg_quality = sum(r['quality_score'] for r in results if r['status'] == 'success') / successful_tests if successful_tests > 0 else 0
    
    print(f"✅ 成功测试: {successful_tests}/{total_tests}")
    print(f"⏱️ 平均响应时间: {avg_response_time:.2f}秒")
    print(f"🎯 平均质量评分: {avg_quality:.1f}/10")
    print(f"🔢 总token使用: {sum(r['tokens_used'] for r in results if r['status'] == 'success')}")
    
    # 分类统计
    print("\n📈 分类表现:")
    categories = set(r['category'] for r in results)
    for category in categories:
        cat_results = [r for r in results if r['category'] == category and r['status'] == 'success']
        if cat_results:
            avg_time = sum(r['response_time'] for r in cat_results) / len(cat_results)
            avg_qual = sum(r['quality_score'] for r in cat_results) / len(cat_results)
            print(f"  {category}: {avg_qual:.1f}/10 | {avg_time:.2f}s")
    
    # 保存详细结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename = f"/root/.openclaw/workspace/model_test_report_{timestamp}.json"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump({
            "model": MODEL,
            "test_time": timestamp,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "avg_response_time": avg_response_time,
                "avg_quality_score": avg_quality
            },
            "detailed_results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细报告已保存: {report_filename}")
    return report_filename

if __name__ == "__main__":
    print("🚀 DeepSeek v3.1:671B 模型全面测试")
    print("📋 测试维度: 代码、推理、中文、创意、数学、多轮对话")
    
    try:
        results = test_model()
        report_file = generate_report(results)
        
        # 读取报告内容用于展示
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        print("\n🎯 测试完成！")
        
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")