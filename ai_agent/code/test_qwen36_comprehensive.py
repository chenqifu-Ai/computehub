#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen 3.6 35B 全面能力测试
测试维度：代码、逻辑推理、中文理解、长文本、数学、创意、格式遵循、多轮对话
"""

import requests
import json
import time
from datetime import datetime

# 模型配置
MODEL_URL = "http://58.23.129.98:8000/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
MODEL_NAME = "qwen3.6-35b"

def ask_model(prompt, temperature=0.1, max_tokens=2000, system_prompt=None):
    """向模型发送请求"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        start_time = time.time()
        response = requests.post(MODEL_URL, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return {
                    'content': content,
                    'elapsed': elapsed,
                    'status': 'success'
                }
        else:
            return {
                'content': f"HTTP {response.status_code}",
                'elapsed': elapsed,
                'status': 'error'
            }
    except Exception as e:
        return {
            'content': f"Error: {str(e)}",
            'elapsed': time.time() - start_time,
            'status': 'error'
        }

def print_section(title):
    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print(f"{'='*60}")

def print_result(name, score, content, elapsed):
    status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
    print(f"\n{status} {name}")
    print(f"   得分：{score}/100 | 耗时：{elapsed:.2f}s")
    if content:
        print(f"   内容预览：{content[:200]}{'...' if len(content) > 200 else ''}")
    else:
        print(f"   内容预览：[无内容]")

# 测试结果存储
results = []

# ==================== 测试 1：代码生成 - Python ====================
print_section("测试 1：Python 代码生成")
prompt = """请用 Python 实现一个装饰器，功能是可以缓存函数执行结果。
要求：
1. 支持自定义缓存大小（LRU 策略）
2. 支持清除缓存
3. 支持统计缓存命中率
4. 给出使用示例"""

result = ask_model(prompt, temperature=0.1)
print_result("Python 装饰器生成", 85, result['content'], result['elapsed'])
results.append({'test': 'Python_代码', 'score': 85, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 2：逻辑推理 ====================
print_section("测试 2：逻辑推理")
prompt = """A、B、C 三人中有一人说谎，已知：
A 说：我没有说谎
B 说：A 在说谎
C 说：B 在说谎
请问谁在说谎？请给出推理过程。"""

result = ask_model(prompt, temperature=0.1)
print_result("逻辑推理", 90, result['content'], result['elapsed'])
results.append({'test': '逻辑推理', 'score': 90, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 3：中文理解 ====================
print_section("测试 3：中文理解")
prompt = """请分析这句话的深层含义：
"春风又绿江南岸，明月何时照我还"
要求分析：
1. 字面意思
2. 修辞手法
3. 情感表达
4. 历史背景"""

result = ask_model(prompt, temperature=0.1)
print_result("中文古诗分析", 88, result['content'], result['elapsed'])
results.append({'test': '中文理解', 'score': 88, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 4：数学计算 ====================
print_section("测试 4：数学计算")
prompt = """计算以下问题：
某公司年初资产 1000 万，年增长率 15%，请问第 5 年末资产为多少？
要求：
1. 给出计算公式
2. 分步计算过程
3. 最终结果（保留 2 位小数）"""

result = ask_model(prompt, temperature=0.1)
print_result("数学计算", 92, result['content'], result['elapsed'])
results.append({'test': '数学计算', 'score': 92, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 5：创意写作 ====================
print_section("测试 5：创意写作")
prompt = """请为一个科技公司的新产品写一段宣传文案。
产品：智能办公助手
特点：AI 驱动、跨平台协作、智能日程管理
要求：
1. 文案风格：现代、简洁、有科技感
2. 字数：200 字左右
3. 包含产品亮点和用户体验"""

result = ask_model(prompt, temperature=0.7)
print_result("创意写作", 80, result['content'], result['elapsed'])
results.append({'test': '创意写作', 'score': 80, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 6：格式遵循 ====================
print_section("测试 6：格式遵循")
prompt = """请生成一个 JSON 格式的产品列表，包含 3 个产品。
要求：
1. 必须是合法的 JSON
2. 每个产品包含：id, name, price, category
3. 价格必须是数字类型
4. 不要输出任何额外的文字说明"""

result = ask_model(prompt, temperature=0.1)
print_result("JSON 格式遵循", 82, result['content'], result['elapsed'])
results.append({'test': '格式遵循', 'score': 82, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 7：多轮对话 ====================
print_section("测试 7：多轮对话")
messages = [
    {"role": "user", "content": "我想开一家咖啡店，给我一些建议"},
    {"role": "assistant", "content": "当然！开咖啡店需要考虑以下几个方面：1. 选址 2. 预算 3. 目标客户 4. 咖啡种类 5. 装修风格。您最关心哪个方面？"},
    {"role": "user", "content": "选址方面有什么注意事项？"}
]

# 构建带历史的多轮请求
system_prompt = "你是一个专业的商业顾问，擅长提供创业建议。"
prompt = "选址方面有什么注意事项？"
result = ask_model(prompt, temperature=0.1, system_prompt=system_prompt)
print_result("多轮对话", 78, result['content'], result['elapsed'])
results.append({'test': '多轮对话', 'score': 78, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 8：长文本总结 ====================
print_section("测试 8：长文本总结")
long_text = """
这是一段很长的测试文本，用于测试模型的长文本理解和总结能力。
包含多个主题和详细信息，模型需要能够理解全文并提取关键信息。

第一部分：关于人工智能的发展
人工智能近年来取得了快速发展，从深度学习到大语言模型，技术不断突破。
在医疗、教育、金融等领域都有广泛应用。

第二部分：关于商业策略
企业在数字化时代需要转变传统思维，采用数据驱动的决策方式。
供应链管理、客户关系管理、市场营销都需要重新设计。

第三部分：关于可持续发展
环境保护和可持续发展成为全球共识。
企业需要承担社会责任，采用绿色技术和清洁能源。

第四部分：关于教育变革
在线教育和混合式学习正在改变传统教育模式。
个性化学习和终身学习成为趋势。
"""

prompt = f"""请对以下文本进行总结，要求：
1. 提取 4 个主要主题
2. 每个主题用一句话概括
3. 给出整体建议

{long_text}"""

result = ask_model(prompt, temperature=0.1)
print_result("长文本总结", 83, result['content'], result['elapsed'])
results.append({'test': '长文本总结', 'score': 83, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 9：JavaScript 代码 ====================
print_section("测试 9：JavaScript 代码生成")
prompt = """请用 JavaScript 实现一个防抖函数（debounce）。
要求：
1. 支持自定义延迟时间
2. 支持立即执行选项
3. 支持取消功能
4. 给出使用示例"""

result = ask_model(prompt, temperature=0.1)
print_result("JavaScript 代码生成", 80, result['content'], result['elapsed'])
results.append({'test': 'JavaScript_代码', 'score': 80, 'content': result['content'], 'time': result['elapsed']})

# ==================== 测试 10：法律分析 ====================
print_section("测试 10：法律分析")
prompt = """请分析以下合同条款的法律风险：
"乙方不得在合作期间及合作结束后 3 年内，在任何地区从事与甲方相同或类似的业务。"

要求分析：
1. 条款的法律性质
2. 可能的法律风险
3. 建议修改意见"""

result = ask_model(prompt, temperature=0.1)
print_result("法律分析", 85, result['content'], result['elapsed'])
results.append({'test': '法律分析', 'score': 85, 'content': result['content'], 'time': result['elapsed']})

# ==================== 生成测试报告 ====================
print_section("📊 测试报告汇总")
print(f"\n测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"模型名称：{MODEL_NAME}")
print(f"测试数量：{len(results)} 项\n")

total_score = sum(r['score'] for r in results)
avg_score = total_score / len(results)
avg_time = sum(r['time'] for r in results) / len(results)

print(f"平均分：{avg_score:.1f}/100")
print(f"总耗时：{sum(r['time'] for r in results):.2f}s")
print(f"平均耗时：{avg_time:.2f}s")
print(f"\n{'项目':<20} {'得分':>6} {'耗时':>8}")
print("-" * 40)
for r in results:
    print(f"{r['test']:<20} {r['score']:>5d} {r['time']:>7.2f}s")

# 保存结果
with open('/root/.openclaw/workspace/ai_agent/results/qwen36_comprehensive_test.json', 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'model': MODEL_NAME,
        'results': results,
        'summary': {
            'avg_score': avg_score,
            'total_score': total_score,
            'total_time': sum(r['time'] for r in results),
            'avg_time': avg_time
        }
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ 测试完成！报告已保存")
