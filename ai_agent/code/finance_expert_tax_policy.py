#!/usr/bin/env python3
"""
财务专家学习 - 税收政策
"""

import json
from datetime import datetime

# 学习内容：最新税收政策
tax_policy_knowledge = {
    "topic": "最新税收政策",
    "date": datetime.now().isoformat(),
    "content": {
        "增值税政策": [
            "小规模纳税人免征政策：月销售额10万元以下免征增值税",
            "留抵退税政策：符合条件的纳税人可申请留抵退税",
            "加计抵减政策：特定行业可享受进项税额加计抵减"
        ],
        "企业所得税政策": [
            "小微企业优惠：年应纳税所得额不超过100万元部分，减按25%计入应纳税所得额",
            "研发费用加计扣除：制造业企业研发费用加计扣除比例提高至100%",
            "高新技术企业优惠：减按15%税率征收企业所得税"
        ],
        "个人所得税政策": [
            "专项附加扣除：子女教育、继续教育、大病医疗、住房贷款利息等",
            "年终奖优惠政策：可选择单独计税或并入综合所得",
            "个体工商户优惠：可享受应纳税所得额减免"
        ],
        "税收优惠政策": [
            "西部大开发税收优惠：西部地区鼓励类产业减按15%税率",
            "海南自由贸易港政策：符合条件的企业享受15%企业所得税",
            "粤港澳大湾区政策：特定行业享受税收优惠"
        ],
        "税收征管政策": [
            "电子发票推广：全面推行电子发票",
            "税收大数据应用：加强税收风险监控",
            "信用等级管理：根据纳税信用等级实施差异化服务"
        ]
    },
    "政策解读": {
        "小微企业政策": "重点支持小微企业发展，减轻税收负担",
        "研发创新政策": "鼓励企业加大研发投入，促进科技创新",
        "区域发展政策": "支持区域协调发展，优化产业布局"
    },
    "实务操作": {
        "申报注意事项": "及时了解政策变化，准确填报申报表",
        "优惠政策申请": "符合条件的及时申请享受税收优惠",
        "风险防范": "加强税务合规管理，防范税务风险"
    }
}

# 保存学习内容
output_file = "/root/.openclaw/workspace/finance-expert/references/tax_policy_20260325.json"

import os
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(tax_policy_knowledge, f, indent=2, ensure_ascii=False)

print(f"✅ 财务专家学习完成")
print(f"📚 主题：{tax_policy_knowledge['topic']}")
print(f"📁 保存到：{output_file}")