#!/usr/bin/env python3
"""
DeepSeek-V3.1 671B 快速能力测试 (测试当前对话模型能力)
按 SOP 流程: 分析 → 代码 → 执行 → 验证 → 报告
"""
import json, time, sys
from typing import Any

# ─── 测试用例 ──────────────────────────────────────────
# 注意：这些是发给模型的问题，不是让模型执行的代码
tests = {
    # 1. 逻辑推理
    "逻辑推理": {
        "prompt": "有三个盒子：一个红盒、一个蓝盒、一个绿盒。只有一个盒子里有钻石。\n红盒上写：\"钻石不在这里\"\n蓝盒上写：\"钻石在红盒里\"\n绿盒上写：\"钻石不在这里\"\n已知只有一句话是真话，钻石在哪个盒子里？请逐步推理。",
        "check": lambda r: "蓝盒" in r or "蓝色" in r
    },

    # 2. 数学
    "数学": {
        "prompt": "一个长方形的长是宽的3倍，如果周长是64厘米，面积是多少平方厘米？",
        "check": lambda r: "192" in r
    },

    # 3. 代码生成(Python)
    "代码生成": {
        "prompt": "写一个Python函数，输入一个整数列表，返回所有和为0的三元组（不重复）。示例：输入[-1,0,1,2,-1,-4]，输出[[-1,-1,2],[-1,0,1]]",
        "check": lambda r: "def " in r and "three_sum" in r or "def " in r and "threeSum" in r
    },

    # 4. 知识问答
    "知识问答": {
        "prompt": "解释一下区块链中的'共识机制'是什么，并比较PoW和PoS的主要区别。",
        "check": lambda r: len(r) > 100 and ("PoW" in r or "工作量" in r) and ("PoS" in r or "权益" in r)
    },

    # 5. 中文理解
    "中文理解": {
        "prompt": "\"这个项目太大，小公司吃不下\"中的\"吃\"字用了什么修辞手法？请解释。",
        "check": lambda r: "比喻" in r or "拟人" in r or "隐喻" in r
    },

    # 6. 代码调试
    "代码调试": {
        "prompt": "以下Python代码有bug，找出并修复：\ndef find_duplicates(arr):\n    seen = {}\n    dup = []\n    for i in arr:\n        if i in seen:\n            dup.append(i)\n        else:\n            seen[i] = True\n    return dup\n\nprint(find_duplicates([1,2,3,2,1,4]))  # 输出 [2,1] 正确\nprint(find_duplicates([1,1,1,1]))     # 输出 [1,1,1] 应该只输出 [1]",
        "check": lambda r: "set" in r.lower() or "return list" in r.lower()
    },

    # 7. 创意写作
    "创意写作": {
        "prompt": "用50字以内写一个关于'AI和人类成为同事'的微型科幻故事。",
        "check": lambda r: 20 <= len(r) <= 120
    },

    # 8. 翻译
    "翻译": {
        "prompt": "将这段英文翻译成地道的中文：\n'The blockchain is an immutable ledger that records transactions across a network of computers. It's not just about cryptocurrency — it's a fundamental shift in how we think about trust and verification.'",
        "check": lambda r: "区块链" in r and "账本" in r
    },

    # 9. 逻辑/常识
    "常识判断": {
        "prompt": "一个房间里有3盏灯，外面有3个开关分别控制这3盏灯。你只能进房间一次，如何确定哪个开关控制哪盏灯？",
        "check": lambda r: ("热" in r or "发热" in r or "温度" in r) and ("关" in r or "开" in r)
    },

    # 10. 代码优化
    "代码优化": {
        "prompt": "这段代码效率很低，请优化：\ndef sum_of_squares(n):\n    result = 0\n    for i in range(1, n+1):\n        for j in range(1, i+1):\n            if j == i:\n                result += j * j\n    return result",
        "check": lambda r: "range" in r and "公式" not in r
    }
}

# ─── 测试执行 ──────────────────────────────────────────
def run_test(name: str, case: dict) -> dict:
    """模拟模型响应（实际由当前对话模型作答，这里只采集结果）"""
    return {
        "name": name,
        "prompt": case["prompt"][:60] + "...",
        "result": "【需模型作答，见下方】",
        "check_desc": case["check"].__doc__ or "自定义验证",
        "status": "待作答"
    }

if __name__ == "__main__":
    print("=" * 60)
    print("🔬 DeepSeek-V3.1 671B 能力测试")
    print("=" * 60)
    print(f"\n📋 共 {len(tests)} 个测试项")
    print(f"⏰ 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n{'═' * 60}")
    print("📝 请依次回答以下问题，我将逐题验证：")
    print(f"{'═' * 60}\n")

    for i, (name, case) in enumerate(tests.items(), 1):
        print(f"\n{'─' * 50}")
        print(f"📌 第{i}题 | {name}")
        print(f"{'─' * 50}")
        print(f"问题: {case['prompt'][:200]}")
        print(f"{'─' * 50}")
        print(f"👉 请在聊天中逐个回答，每回答一个我给出评判")
        print()

    print(f"\n{'═' * 60}")
    print("✅ 测试脚本已准备就绪，开始吧老大！")
    print(f"{'═' * 60}")
