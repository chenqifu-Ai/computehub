#!/usr/bin/env python3
"""
Qwen 3.6 35B 专业领域测试
测试模型在专业场景下的表现
"""

import requests
import json
import time

def professional_test():
    """专业领域测试"""
    
    api_url = "http://58.23.129.98:8000/v1/chat/completions"
    api_key = "sk-78sadn09bjawde123e"
    
    print("🎯 开始Qwen 3.6 35B专业领域测试")
    print("=" * 60)
    
    # 专业测试用例
    professional_tests = [
        {
            "category": "医学诊断",
            "prompt": "患者出现发热、咳嗽、呼吸困难症状，血氧饱和度92%。请分析可能的病因，并建议初步诊断步骤。"
        },
        {
            "category": "法律咨询", 
            "prompt": "解释《中华人民共和国合同法》中关于违约责任的条款，包括实际履行、损害赔偿和违约金的规定。"
        },
        {
            "category": "金融分析",
            "prompt": "分析当前股市行情，给出一份投资建议报告，包括行业分析、风险提示和投资策略。"
        },
        {
            "category": "编程代码审查",
            "prompt": "请审查以下Python代码，指出潜在问题并给出改进建议：\n```python\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n        else:\n            result.append(item)\n    return result\n```"
        },
        {
            "category": "学术写作",
            "prompt": "撰写一篇关于人工智能伦理的学术论文摘要，包括研究背景、方法、结果和结论。"
        },
        {
            "category": "商业策划",
            "prompt": "为一家新开的咖啡店制定一份市场营销计划，包括目标客户、推广策略和预算分配。"
        },
        {
            "category": "技术文档",
            "prompt": "编写一个RESTful API的使用文档，包括端点说明、请求示例和响应格式。"
        },
        {
            "category": "教育培训",
            "prompt": "设计一个面向初学者的机器学习课程大纲，包含学习目标、课程内容和实践项目。"
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    for i, test in enumerate(professional_tests, 1):
        print(f"\n[{i}/{len(professional_tests)}] 🎯 {test['category']}")
        print(f"📋 {test['prompt'][:80]}...")
        
        payload = {
            "model": "qwen3.6-35b",
            "messages": [{"role": "user", "content": test["prompt"]}],
            "max_tokens": 1500,
            "temperature": 0.3,  # 更低的温度用于专业回答
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
                
                print(f"✅ 成功 | 时间: {response_time}ms | Token: {usage.get('total_tokens', 0)}")
                
                # 显示专业回答的关键部分
                lines = content.split('\n')
                print("💡 关键要点:")
                for line in lines[:5]:  # 显示前5行
                    if line.strip():
                        print(f"   • {line.strip()}")
                if len(lines) > 5:
                    print(f"   • ...（共{len(lines)}行）")
                    
            else:
                print(f"❌ 失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        print("-" * 50)
        time.sleep(3)  # 避免服务器过载

if __name__ == "__main__":
    professional_test()