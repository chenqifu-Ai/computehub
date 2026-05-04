#!/usr/bin/env python3
"""
Qwen 3.6 35B 全面测试套件
包含多种测试类型，全方位评估模型能力
"""

import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def comprehensive_test():
    """全面测试套件"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    print("🧪 Qwen 3.6 35B 全面测试套件")
    print("=" * 70)
    
    # 定义各种测试类型
    test_categories = {
        "基础能力": [
            {"name": "语言理解", "prompt": "解释'人工智能'和'机器学习'的区别和联系。", "temp": 0.3},
            {"name": "逻辑推理", "prompt": "如果所有的猫都会爬树，而Tom是一只猫，那么Tom会爬树吗？请用逻辑推理解释。", "temp": 0.2},
            {"name": "数学计算", "prompt": "计算：2^10 + 3^4 - √144 × 5 ÷ 2", "temp": 0.1}
        ],
        "专业知识": [
            {"name": "医学知识", "prompt": "解释高血压的病因、症状和预防措施。", "temp": 0.3},
            {"name": "法律知识", "prompt": "简述《民法典》中关于合同成立的要件。", "temp": 0.3},
            {"name": "金融知识", "prompt": "解释股票市场中的'市盈率'和'市净率'概念。", "temp": 0.3}
        ],
        "创意写作": [
            {"name": "诗歌创作", "prompt": "写一首关于春天的七言绝句。", "temp": 0.8},
            {"name": "故事创作", "prompt": "创作一个关于时间旅行的短篇故事开头。", "temp": 0.7},
            {"name": "广告文案", "prompt": "为一款智能手表写一则30字的广告语。", "temp": 0.6}
        ],
        "技术能力": [
            {"name": "代码生成", "prompt": "用Python写一个函数，计算斐波那契数列的第n项。", "temp": 0.3},
            {"name": "代码审查", "prompt": "找出以下代码的问题：def add(a,b): return a+b", "temp": 0.3},
            {"name": "技术文档", "prompt": "写一个简单的REST API使用说明。", "temp": 0.4}
        ],
        "实时交互": [
            {"name": "多轮对话", "prompt": "你好，我想了解人工智能的发展历史。", "temp": 0.5},
            {"name": "上下文理解", "prompt": "（接上文）那么现在的主要应用领域有哪些？", "temp": 0.5},
            {"name": "纠错能力", "prompt": "我刚才说错了，应该是机器学习的主要应用领域。", "temp": 0.5}
        ],
        "边缘案例": [
            {"name": "长文本处理", "prompt": "请总结以下长文本的主要内容：" + "人工智能是..." * 50, "temp": 0.3},
            {"name": "模糊查询", "prompt": "那个...呃...关于...科技的东西...", "temp": 0.6},
            {"name": "多语言", "prompt": "Translate 'Hello, how are you?' to Chinese and French.", "temp": 0.4}
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    total_tests = sum(len(tests) for tests in test_categories.values())
    completed = 0
    results = []
    
    def run_single_test(category, test):
        """运行单个测试"""
        nonlocal completed
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": test["prompt"]}],
            "max_tokens": 800,
            "temperature": test["temp"],
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                
                response_time = round((end_time - start_time) * 1000, 2)
                
                # 评估回答质量（简单评估）
                quality = "🟢 优秀"
                if len(content) < 50:
                    quality = "🟡 一般"
                if "抱歉" in content or "无法" in content:
                    quality = "🔴 失败"
                
                test_result = {
                    "category": category,
                    "name": test["name"],
                    "status": "✅ 成功",
                    "time": response_time,
                    "tokens": usage.get('total_tokens', 0),
                    "quality": quality,
                    "snippet": content[:100] + "..." if len(content) > 100 else content
                }
                
            else:
                test_result = {
                    "category": category,
                    "name": test["name"],
                    "status": f"❌ HTTP {response.status_code}",
                    "time": 0,
                    "tokens": 0,
                    "quality": "🔴 失败",
                    "snippet": ""
                }
                
        except Exception as e:
            test_result = {
                "category": category,
                "name": test["name"],
                "status": f"❌ 错误: {str(e)[:30]}",
                "time": 0,
                "tokens": 0,
                "quality": "🔴 失败", 
                "snippet": ""
            }
        
        completed += 1
        return test_result
    
    # 执行所有测试
    print(f"📊 开始执行 {total_tests} 项测试...\n")
    
    all_results = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        
        for category, tests in test_categories.items():
            print(f"🧩 {category} 测试组 ({len(tests)}项)")
            
            for test in tests:
                futures.append(executor.submit(run_single_test, category, test))
        
        # 收集结果
        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)
            
            # 实时进度显示
            progress = (completed / total_tests) * 100
            print(f"   [{completed}/{total_tests}] {result['category']} - {result['name']}: {result['status']}")
    
    # 生成测试报告
    print("\n" + "=" * 70)
    print("📈 测试报告摘要")
    print("=" * 70)
    
    success_count = sum(1 for r in all_results if "✅" in r["status"])
    avg_time = sum(r["time"] for r in all_results if r["time"] > 0) / max(1, success_count)
    total_tokens = sum(r["tokens"] for r in all_results)
    
    print(f"✅ 成功率: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
    print(f"⏱️  平均响应时间: {avg_time:.2f}ms")
    print(f"🔢 总Token消耗: {total_tokens}")
    
    # 按类别统计
    print("\n📊 按类别统计:")
    for category in test_categories.keys():
        cat_results = [r for r in all_results if r["category"] == category]
        cat_success = sum(1 for r in cat_results if "✅" in r["status"])
        print(f"   {category}: {cat_success}/{len(cat_results)} ✅")
    
    # 显示详细结果
    print("\n🔍 详细结果:")
    for result in all_results:
        print(f"   {result['category']:12} {result['name']:15} {result['status']:15} {result['time']:6}ms {result['quality']}")

if __name__ == "__main__":
    comprehensive_test()