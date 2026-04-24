#!/usr/bin/env python3
"""
财务专家学习 - 财务分析（深入）
"""

import json
from datetime import datetime

# 学习内容：财务分析深入知识
financial_analysis_knowledge = {
    "topic": "财务分析深入知识",
    "date": datetime.now().isoformat(),
    "content": {
        "财务分析框架": [
            "战略分析：行业分析、竞争分析、企业战略",
            "会计分析：会计政策评估、会计质量分析",
            "财务分析：盈利能力、偿债能力、营运能力分析",
            "前景分析：财务预测、风险评估、价值评估"
        ],
        "盈利能力分析": [
            "毛利率 = (营业收入 - 营业成本) / 营业收入",
            "营业利润率 = 营业利润 / 营业收入",
            "净利率 = 净利润 / 营业收入",
            "总资产报酬率 = 息税前利润 / 平均总资产",
            "净资产收益率 = 净利润 / 平均净资产"
        ],
        "偿债能力分析": [
            "流动比率 = 流动资产 / 流动负债",
            "速动比率 = (流动资产 - 存货) / 流动负债",
            "现金比率 = 货币资金 / 流动负债",
            "资产负债率 = 总负债 / 总资产",
            "利息保障倍数 = 息税前利润 / 利息费用"
        ],
        "营运能力分析": [
            "应收账款周转率 = 营业收入 / 平均应收账款",
            "存货周转率 = 营业成本 / 平均存货",
            "总资产周转率 = 营业收入 / 平均总资产",
            "固定资产周转率 = 营业收入 / 平均固定资产"
        ],
        "发展能力分析": [
            "营业收入增长率 = (本期收入 - 上期收入) / 上期收入",
            "净利润增长率 = (本期净利润 - 上期净利润) / 上期净利润",
            "总资产增长率 = (本期总资产 - 上期总资产) / 上期总资产",
            "净资产增长率 = (本期净资产 - 上期净资产) / 上期净资产"
        ]
    },
    "分析技巧": {
        "横向分析": "与同行业企业比较，了解行业地位",
        "纵向分析": "与企业历史数据比较，了解发展趋势",
        "结构分析": "分析各项目占总体的比重",
        "因素分析": "分析各因素对指标的影响程度"
    },
    "预警指标": {
        "财务危机预警": "连续亏损、现金流紧张、负债率高",
        "经营风险预警": "收入下降、成本上升、市场份额萎缩",
        "管理风险预警": "内部控制薄弱、管理层变动频繁"
    }
}

# 保存学习内容
output_file = "/root/.openclaw/workspace/finance-expert/references/financial_analysis_v2_20260325.json"

import os
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(financial_analysis_knowledge, f, indent=2, ensure_ascii=False)

print(f"✅ 财务专家学习完成")
print(f"📚 主题：{financial_analysis_knowledge['topic']}")
print(f"📁 保存到：{output_file}")