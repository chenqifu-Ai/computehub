#!/usr/bin/env python3
"""
ministral-3:3B 测试脚本
目标: 192.168.2.165:11434
测试维度: 推理速度、语言理解、代码能力、逻辑推理、多轮对话
"""

import json
import time
import sys
from datetime import datetime

OLLAMA_URL = "http://192.168.2.165:11434/api/generate"

def ask(prompt, timeout=30):
    """发送请求并返回结果"""
    data = {
        "model": "ministral-3:3B",
        "prompt": prompt,
        "stream": False
    }
    import urllib.request
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            elapsed = time.time() - start
            return result.get("response", ""), elapsed
    except Exception as e:
        return f"ERROR: {str(e)}", 0

def run_test(name, prompt, expected_keywords=None):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"🧪 测试: {name}")
    print(f"{'='*60}")
    print(f"📝 提示: {prompt}")
    
    start = time.time()
    response, elapsed = ask(prompt)
    
    print(f"✅ 耗时: {elapsed:.2f}秒")
    print(f"📤 回答: {response[:200]}")
    
    if expected_keywords:
        for kw in expected_keywords:
            if kw in response:
                print(f"   ✅ 包含关键词: {kw}")
            else:
                print(f"   ❌ 缺少关键词: {kw}")
    
    return {
        "name": name,
        "response": response,
        "elapsed": elapsed,
        "timestamp": datetime.now().isoformat()
    }

def main():
    results = []
    
    # 1. 基础功能测试
    results.append(run_test(
        "基础问候",
        "你好，请用一句话介绍你自己",
        ["助手", "你好"]
    ))
    
    # 2. 数学能力
    results.append(run_test(
        "基础数学",
        "15 + 27 = ?",
        ["42"]
    ))
    
    # 3. 中文理解
    results.append(run_test(
        "中文理解",
        "请用中文回答：今天天气怎么样？",
        ["天气", "好", "不错"]
    ))
    
    # 4. 代码能力
    results.append(run_test(
        "简单代码",
        "写一个 Python 函数，判断一个数是否为偶数",
        ["def", "if", "return", "% 2"]
    ))
    
    # 5. 逻辑推理
    results.append(run_test(
        "逻辑推理",
        "如果所有猫都会爬树，Tom 是一只猫，那么 Tom 会爬树吗？",
        ["会", "是的", "Tom"]
    ))
    
    # 6. 多轮对话
    results.append(run_test(
        "上下文理解",
        "昨天我们聊到了什么？请用一句话回答",
        ["昨天", "聊过", "之前"]
    ))
    
    # 生成报告
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['name']}: {r['elapsed']:.2f}秒")
    
    total_time = sum(r['elapsed'] for r in results)
    avg_time = total_time / len(results)
    
    print(f"\n总耗时: {total_time:.2f}秒")
    print(f"平均耗时: {avg_time:.2f}秒")
    
    # 保存报告
    report = {
        "model": "ministral-3:3B",
        "server": "192.168.2.165:11434",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "total_tests": len(results),
            "total_time": round(total_time, 2),
            "avg_time": round(avg_time, 2),
            "best_test": min(results, key=lambda x: x['elapsed'])['name'],
            "worst_test": max(results, key=lambda x: x['elapsed'])['name']
        }
    }
    
    report_file = f"projects/computehub/tests/ministral3_3b_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 报告已保存到: {report_file}")

if __name__ == "__main__":
    main()
