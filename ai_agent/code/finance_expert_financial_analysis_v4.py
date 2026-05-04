#!/usr/bin/env python3
"""
财务专家学习 - 财务分析（实务应用）
"""

import json
from datetime import datetime

# 学习内容：财务分析实务应用
financial_analysis_knowledge = {
    "topic": "财务分析实务应用",
    "date": datetime.now().isoformat(),
    "content": {
        "财务报表分析实务": [
            "资产负债表分析：重点关注资产质量、负债结构、资本结构",
            "利润表分析：分析收入结构、成本控制、盈利能力",
            "现金流量表分析：评估现金流质量、偿债能力、投资能力",
            "报表勾稽关系：三张报表之间的内在联系"
        ],
        "财务比率分析实务": [
            "盈利能力分析：销售净利率、净资产收益率、总资产报酬率",
            "偿债能力分析：流动比率、速动比率、资产负债率",
            "营运能力分析：应收账款周转率、存货周转率、总资产周转率",
            "发展能力分析：收入增长率、净利润增长率、资产增长率"
        ],
        "财务分析报告撰写": [
            "报告结构：摘要、分析、结论、建议",
            "数据呈现：图表结合、重点突出、逻辑清晰",
            "结论表达：客观准确、有理有据、建议可行",
            "语言风格：专业严谨、通俗易懂、重点突出"
        ],
        "财务分析工具应用": [
            "Excel分析：数据透视表、图表制作、公式计算",
            "专业软件：财务分析软件、BI工具",
            "数据分析：Python、R等编程工具",
            "可视化工具：Tableau、Power BI等"
        ],
        "行业分析实务": [
            "行业特征分析：行业生命周期、竞争格局",
            "行业财务特征：行业特有的财务指标",
            "行业比较分析：与行业平均水平比较",
            "行业趋势分析：行业发展方向和趋势"
        ]
    },
    "案例分析": {
        "制造业企业分析": "重点分析成本控制、资产周转、盈利能力",
        "零售业企业分析": "重点关注存货周转、现金流、坪效",
        "科技企业分析": "重点分析研发投入、成长性、估值",
        "金融企业分析": "重点关注风险管理、资本充足率、盈利能力"
    },
    "实务技巧": {
        "数据质量检查": "确保财务数据的真实性和完整性",
        "异常值识别": "识别和处理异常财务数据",
        "趋势分析": "分析财务数据的长期趋势",
        "比较分析": "与历史、行业、竞争对手比较"
    }
}

# 保存学习内容
output_file = "/root/.openclaw/workspace/finance-expert/references/financial_analysis_v4_20260325.json"

import os
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(financial_analysis_knowledge, f, indent=2, ensure_ascii=False)

print(f"✅ 财务专家学习完成")
print(f"📚 主题：{financial_analysis_knowledge['topic']}")
print(f"📁 保存到：{output_file}")