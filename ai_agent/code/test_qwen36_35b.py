#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen 3.6-35B 模型综合测试脚本
测试项目：基础对话、代码生成、数学计算、逻辑推理、文本理解、响应速度
"""

import requests
import json
import time
from datetime import datetime

# 模型配置
API_URL = "http://58.23.129.98:8001/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
MODEL_NAME = "qwen3.6-35b"

# 测试用例
TEST_CASES = [
    {
        "name": "基础对话",
        "prompt": "请用一句话介绍你自己，包括你的能力和特点。",
        "expected": "自我介绍，包含能力描述"
    },
    {
        "name": "代码生成-Python",
        "prompt": "写一个 Python 函数，计算斐波那契数列的第 n 项，要求使用递归和迭代两种方式。",
        "expected": "包含递归和迭代两种实现的 Python 代码"
    },
    {
        "name": "数学计算",
        "prompt": "计算：12345 * 67890 + 98765 / 5 = ? 请给出详细计算过程。",
        "expected": "正确的计算结果和步骤"
    },
    {
        "name": "逻辑推理",
        "prompt": "如果所有的猫都怕水，而 Tom 是一只猫，那么 Tom 怕水吗？请解释推理过程。",
        "expected": "正确的逻辑推理结论"
    },
    {
        "name": "文本理解",
        "prompt": "请总结这句话的核心意思：'虽然人工智能技术日新月异，但人类创造力和情感理解仍然是机器难以替代的核心竞争力。'",
        "expected": "准确的核心意思总结"
    },
    {
        "name": "多轮对话-上下文",
        "prompt": "小明今年 10 岁，他比他弟弟大 3 岁。请问小明的弟弟几岁？5 年后小明比弟弟大几岁？",
        "expected": "正确的年龄计算和差值理解"
    },
    {
        "name": "创意写作",
        "prompt": "请用 50 字以内描写春天的早晨。",
        "expected": "优美的春天早晨描写"
    },
    {
        "name": "知识问答",
        "prompt": "什么是量子纠缠？请用通俗易懂的语言解释。",
        "expected": "准确的量子纠缠概念解释"
    }
]

def call_model(prompt, temperature=0.7, max_tokens=2048):
    """调用模型 API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    start_time = time.time()
    response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        return {
            "success": True,
            "content": result["choices"][0]["message"]["content"],
            "response_time": end_time - start_time,
            "tokens": result.get("usage", {})
        }
    else:
        return {
            "success": False,
            "error": f"HTTP {response.status_code}: {response.text}",
            "response_time": end_time - start_time
        }

def evaluate_response(test_case, response):
    """评估响应质量（简单规则）"""
    if not response["success"]:
        return "❌ 失败", response.get("error", "未知错误")
    
    content = response.get("content")
    if content is None:
        return "❌ 失败", "响应内容为空"
    
    expected = test_case["expected"]
    
    # 简单评估：检查响应长度和关键词
    if len(content) < 10:
        return "⚠️ 响应过短", "内容可能不完整"
    
    # 代码测试检查是否包含代码块
    if "代码" in test_case["name"]:
        if "```" in content or "def " in content or "function" in content:
            return "✅ 通过", "生成了代码结构"
        else:
            return "⚠️ 警告", "未检测到代码块格式"
    
    # 数学测试检查是否包含数字
    if "数学" in test_case["name"]:
        if any(c.isdigit() for c in content):
            return "✅ 通过", "包含计算结果"
        else:
            return "⚠️ 警告", "未检测到数字结果"
    
    # 其他测试默认通过
    return "✅ 通过", f"响应长度：{len(content)} 字符"

def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print(f"🤖 Qwen 3.6-35B 模型综合测试")
    print(f"📍 API: {API_URL}")
    print(f"⏰ 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    results = []
    total_time = 0
    success_count = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] 测试：{test_case['name']}")
        print(f"    问题：{test_case['prompt'][:60]}...")
        
        response = call_model(test_case["prompt"])
        total_time += response["response_time"]
        
        status, evaluation = evaluate_response(test_case, response)
        
        if response["success"]:
            success_count += 1
        
        result = {
            "test_name": test_case["name"],
            "status": status,
            "evaluation": evaluation,
            "response_time": response["response_time"],
            "success": response["success"],
            "content_preview": response.get("content", "")[:200] if response["success"] else ""
        }
        results.append(result)
        
        print(f"    状态：{status}")
        print(f"    耗时：{response['response_time']:.2f}秒")
        print(f"    评估：{evaluation}")
        print()
    
    # 生成报告
    avg_time = total_time / len(TEST_CASES) if TEST_CASES else 0
    
    print("=" * 80)
    print("📊 测试报告总结")
    print("=" * 80)
    print(f"✅ 成功：{success_count}/{len(TEST_CASES)}")
    print(f"⏱️  平均响应时间：{avg_time:.2f}秒")
    print(f"⏱️  总测试时间：{total_time:.2f}秒")
    print(f"📈 成功率：{success_count/len(TEST_CASES)*100:.1f}%")
    print()
    
    # 详细结果表
    print("详细结果:")
    print("-" * 80)
    print(f"{'测试项目':<20} {'状态':<10} {'耗时 (秒)':<10} {'评估'}")
    print("-" * 80)
    for r in results:
        print(f"{r['test_name']:<20} {r['status']:<10} {r['response_time']:<10.2f} {r['evaluation']}")
    print("-" * 80)
    
    # 保存报告
    report = {
        "model": MODEL_NAME,
        "api_url": API_URL,
        "test_time": datetime.now().isoformat(),
        "summary": {
            "total_tests": len(TEST_CASES),
            "success_count": success_count,
            "success_rate": f"{success_count/len(TEST_CASES)*100:.1f}%",
            "avg_response_time": f"{avg_time:.2f}s",
            "total_time": f"{total_time:.2f}s"
        },
        "results": results
    }
    
    report_file = "/root/.openclaw/workspace/ai_agent/results/qwen36_35b_test_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 报告已保存：{report_file}")
    print("=" * 80)
    
    return report

if __name__ == "__main__":
    run_tests()
