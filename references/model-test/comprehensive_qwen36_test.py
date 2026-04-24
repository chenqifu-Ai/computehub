#!/usr/bin/env python3
"""
Qwen 3.6 35B 全面测试套件
测试模型的多方面能力
"""

import requests
import json
import time
import re

def test_model(api_url, api_key, test_name, messages, max_tokens=2000):
    """通用模型测试函数"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False
    }
    
    print(f"\n🧪 测试: {test_name}")
    print(f"📝 问题: {messages[0]['content'][:100]}...")
    
    try:
        start_time = time.time()
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            usage = result.get('usage', {})
            
            response_time = round((end_time - start_time) * 1000, 2)
            token_speed = round(usage.get('completion_tokens', 0) / (response_time / 1000), 2) if response_time > 0 else 0
            
            print(f"✅ 成功 | 时间: {response_time}ms | Token: {usage.get('total_tokens', 0)} | 速度: {token_speed} token/s")
            print(f"📊 使用: 输入{usage.get('prompt_tokens', 0)} | 输出{usage.get('completion_tokens', 0)}")
            
            # 简要显示回复内容
            preview = content[:200].replace('\n', ' ')
            if len(content) > 200:
                preview += "..."
            print(f"📄 回复预览: {preview}")
            
            return True, content, response_time, usage
        else:
            print(f"❌ 失败: HTTP {response.status_code}")
            return False, f"HTTP {response.status_code}", 0, {}
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False, str(e), 0, {}

def comprehensive_test():
    """全面测试Qwen 3.6 35B模型"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    print("🚀 开始Qwen 3.6 35B全面测试")
    print("=" * 60)
    
    # 测试用例列表
    test_cases = [
        {
            "name": "中文语言能力",
            "messages": [{"role": "user", "content": "请用优美的中文写一首关于春天的七言绝句，并解释其意境。"}]
        },
        {
            "name": "逻辑推理能力", 
            "messages": [{"role": "user", "content": "如果所有的猫都会爬树，有些动物是猫，那么这些动物会爬树吗？请用逻辑推理证明你的结论。"}]
        },
        {
            "name": "代码生成能力",
            "messages": [{"role": "user", "content": "写一个Python函数，实现快速排序算法，并添加详细注释说明每一步的作用。"}]
        },
        {
            "name": "知识问答能力",
            "messages": [{"role": "user", "content": "请详细解释量子计算的基本原理，包括量子比特、叠加态和量子纠缠的概念。"}]
        },
        {
            "name": "创意写作能力",
            "messages": [{"role": "user", "content": "写一个关于人工智能助手帮助人类解决环境危机的短篇科幻故事，约300字。"}]
        },
        {
            "name": "数学计算能力",
            "messages": [{"role": "user", "content": "计算定积分 ∫(0到π) sin(x) dx 的值，并展示计算过程。"}]
        },
        {
            "name": "多轮对话能力",
            "messages": [
                {"role": "user", "content": "我想学习机器学习"},
                {"role": "assistant", "content": "很好！机器学习是人工智能的重要分支。你想从哪个方面开始学习？"},
                {"role": "user", "content": "请推荐一些适合初学者的资源"}
            ]
        },
        {
            "name": "长文本理解",
            "messages": [{"role": "user", "content": "请总结以下文章的主要观点：（此处省略长文本，实际测试时会包含真实长文本）"}],
            "max_tokens": 3000
        }
    ]
    
    results = []
    total_time = 0
    total_tokens = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}]")
        
        success, content, response_time, usage = test_model(
            api_url, api_key, 
            test_case["name"], 
            test_case["messages"],
            test_case.get("max_tokens", 2000)
        )
        
        results.append({
            "test": test_case["name"],
            "success": success,
            "time_ms": response_time,
            "tokens": usage.get("total_tokens", 0),
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        })
        
        if success:
            total_time += response_time
            total_tokens += usage.get("total_tokens", 0)
        
        # 短暂暂停避免服务器压力
        time.sleep(2)
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📊 测试报告汇总")
    print("=" * 60)
    
    successful_tests = sum(1 for r in results if r["success"])
    avg_time = total_time / successful_tests if successful_tests > 0 else 0
    avg_speed = total_tokens / (total_time / 1000) if total_time > 0 else 0
    
    print(f"✅ 通过测试: {successful_tests}/{len(test_cases)}")
    print(f"⏱️  总耗时: {round(total_time/1000, 2)}s")
    print(f"📊 总Token: {total_tokens}")
    print(f"🚀 平均速度: {round(avg_speed, 2)} token/s")
    print(f"⏰ 平均响应: {round(avg_time, 2)}ms")
    
    print("\n📋 详细结果:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['test']}: {result['time_ms']}ms, {result['tokens']}tokens")
    
    return results

if __name__ == "__main__":
    comprehensive_test()