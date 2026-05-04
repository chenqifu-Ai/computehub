#!/usr/bin/env python3
"""
财务专家学习 - 税收政策
"""

import json
from datetime import datetime

# 学习内容：增值税基础知识
tax_knowledge = {
    "topic": "增值税基础知识",
    "date": datetime.now().isoformat(),
    "content": {
        "定义": "增值税是以商品（含应税劳务）在流转过程中产生的增值额作为计税依据而征收的一种流转税。",
        "纳税人": "在中国境内销售货物或者提供加工、修理修配劳务以及进口货物的单位和个人。",
        "税率": [
            "基本税率：13%",
            "低税率：9%（农产品、图书、饲料等）",
            "零税率：出口货物、国际运输服务等",
            "征收率：3%（小规模纳税人）"
        ],
        "计税方法": [
            "一般计税方法：应纳税额 = 销项税额 - 进项税额",
            "简易计税方法：应纳税额 = 销售额 × 征收率"
        ],
        "申报周期": [
            "按月申报：一般纳税人",
            "按季申报：小规模纳税人"
        ],
        "优惠政策": [
            "小规模纳税人月销售额10万元以下免征增值税",
            "农产品免税政策",
            "高新技术企业税收优惠"
        ]
    },
    "案例": {
        "案例1": "某企业当月销售额100万元，进项税额8万元，销项税额13万元，应纳增值税=13-8=5万元",
        "案例2": "小规模纳税人季度销售额25万元，应纳增值税=25万×3%=7500元"
    }
}

# 保存学习内容
output_file = "/root/.openclaw/workspace/finance-expert/references/tax_knowledge_20260325.json"

import os
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(tax_knowledge, f, indent=2, ensure_ascii=False)

print(f"✅ 财务专家学习完成")
print(f"📚 主题：{tax_knowledge['topic']}")
print(f"📁 保存到：{output_file}")