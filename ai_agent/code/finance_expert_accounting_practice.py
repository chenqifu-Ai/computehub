#!/usr/bin/env python3
"""
财务专家学习 - 会计实务
"""

import json
from datetime import datetime

# 学习内容：会计实务操作
accounting_practice_knowledge = {
    "topic": "会计实务操作",
    "date": datetime.now().isoformat(),
    "content": {
        "会计工作流程": [
            "原始凭证审核：检查凭证的真实性、合法性、完整性",
            "记账凭证编制：根据原始凭证编制记账凭证",
            "账簿登记：将记账凭证登记到相关账簿",
            "对账结账：核对账目，进行月末结账",
            "报表编制：编制财务报表"
        ],
        "凭证处理": [
            "收款凭证：记录现金和银行存款收入",
            "付款凭证：记录现金和银行存款支出",
            "转账凭证：记录不涉及现金和银行存款的业务",
            "通用凭证：适用于各种经济业务"
        ],
        "账簿设置": [
            "总账：总括反映经济业务",
            "明细账：详细反映某一科目",
            "日记账：按时间顺序记录经济业务",
            "备查账：辅助登记重要事项"
        ],
        "月末处理": [
            "计提折旧：固定资产折旧计提",
            "摊销费用：无形资产、长期待摊费用摊销",
            "计提准备：坏账准备、存货跌价准备等",
            "结转损益：将损益类科目余额结转到本年利润"
        ],
        "税务申报": [
            "增值税申报：按月或按季申报",
            "企业所得税申报：按季预缴，年度汇算清缴",
            "个人所得税申报：按月代扣代缴",
            "其他税种申报：城建税、教育费附加等"
        ]
    },
    "实务技巧": {
        "凭证审核技巧": "重点关注大额、异常、关联方交易",
        "账簿登记技巧": "及时登记、准确分类、清晰摘要",
        "对账技巧": "账证核对、账账核对、账实核对",
        "报表分析技巧": "趋势分析、比率分析、结构分析"
    },
    "常见问题": {
        "问题1": "原始凭证丢失如何处理？",
        "解答1": "及时补办或取得相关证明，确保业务真实性",
        "问题2": "记账错误如何更正？",
        "解答2": "采用划线更正法、红字冲销法或补充登记法",
        "问题3": "月末结账注意事项？",
        "解答3": "确保所有业务已入账，核对总账与明细账"
    }
}

# 保存学习内容
output_file = "/root/.openclaw/workspace/finance-expert/references/accounting_practice_20260325.json"

import os
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(accounting_practice_knowledge, f, indent=2, ensure_ascii=False)

print(f"✅ 财务专家学习完成")
print(f"📚 主题：{accounting_practice_knowledge['topic']}")
print(f"📁 保存到：{output_file}")