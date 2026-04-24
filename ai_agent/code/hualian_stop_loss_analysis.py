#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华联股份(000882)止损操作分析脚本
执行止损决策分析和报告生成
"""

import datetime
import math
from typing import Dict, Any


def calculate_stop_loss_analysis() -> Dict[str, Any]:
    """计算止损分析数据"""
    # 输入数据
    current_price = 1.610  # 当前价
    stop_loss_price = 1.60  # 止损位
    position = 13500  # 持仓股数
    cost_price = 1.873  # 成本价
    
    # 计算关键指标
    current_value = current_price * position
    cost_value = cost_price * position
    loss_amount = cost_value - current_value
    loss_percentage = (loss_amount / cost_value) * 100
    
    # 止损相关计算
    is_below_stop_loss = current_price < stop_loss_price
    stop_loss_value = stop_loss_price * position
    potential_stop_loss_amount = cost_value - stop_loss_value
    
    # 资金回收分析
    recovered_cash = current_value
    max_loss_if_stop = potential_stop_loss_amount
    
    return {
        "current_price": current_price,
        "stop_loss_price": stop_loss_price,
        "position": position,
        "cost_price": cost_price,
        "current_value": round(current_value, 2),
        "cost_value": round(cost_value, 2),
        "loss_amount": round(loss_amount, 2),
        "loss_percentage": round(loss_percentage, 2),
        "is_below_stop_loss": is_below_stop_loss,
        "stop_loss_value": round(stop_loss_value, 2),
        "potential_stop_loss_amount": round(potential_stop_loss_amount, 2),
        "recovered_cash": round(recovered_cash, 2),
        "max_loss_if_stop": round(max_loss_if_stop, 2)
    }


def generate_analysis_report(analysis_data: Dict[str, Any]) -> str:
    """生成详细分析报告"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    report = f"# 华联股份(000882)止损决策分析报告\n"
    report += f"**分析日期**: {today}\n\n"
    
    # 基本信息
    report += "## 1. 持仓基本信息\n"
    report += f"- **股票代码**: 000882 (华联股份)\n"
    report += f"- **当前价格**: ¥{analysis_data['current_price']}\n"
    report += f"- **止损价位**: ¥{analysis_data['stop_loss_price']}\n"
    report += f"- **持仓数量**: {analysis_data['position']:,} 股\n"
    report += f"- **成本价格**: ¥{analysis_data['cost_price']}\n"
    report += f"- **持仓成本**: ¥{analysis_data['cost_value']:,.2f}\n"
    report += f"- **当前市值**: ¥{analysis_data['current_value']:,.2f}\n"
    report += f"- **当前亏损**: -¥{analysis_data['loss_amount']:,.2f} (-{analysis_data['loss_percentage']}%)\n\n"
    
    # 止损分析
    report += "## 2. 止损位分析\n"
    if analysis_data['is_below_stop_loss']:
        report += "🔴 **已跌破止损位**: 当前价格 ¥1.610 < 止损位 ¥1.60\n"
        report += "   - **技术信号**: 触发止损条件\n"
        report += "   - **风险等级**: 高风险（继续持有可能扩大亏损）\n"
    else:
        report += "🟢 **未跌破止损位**: 当前价格高于止损位\n"
    report += f"- **止损触发价差**: ¥{abs(analysis_data['current_price'] - analysis_data['stop_loss_price']):.3f}\n"
    report += f"- **止损时市值**: ¥{analysis_data['stop_loss_value']:,.2f}\n"
    report += f"- **最大止损亏损**: -¥{analysis_data['max_loss_if_stop']:,.2f}\n\n"
    
    # 操作建议
    report += "## 3. 操作建议\n"
    if analysis_data['is_below_stop_loss']:
        report += "### 🚨 立即止损操作建议\n"
        report += "**建议操作**: **全部卖出**\n"
        report += "**理由**:\n"
        report += "1. 已跌破预设止损位，风险控制机制触发\n"
        report += "2. 当前亏损14.04%，继续持有可能扩大亏损\n"
        report += "3. 回收资金可寻找更好的投资机会\n"
        report += "4. 遵守投资纪律，避免情绪化决策\n\n"
        
        report += "**具体操作步骤**:\n"
        report += "1. 立即下单卖出全部13,500股\n"
        report += "2. 卖出价格：按市价或略低于市价确保成交\n"
        report += "3. 预计回收资金：¥21,735.00\n"
        report += "4. 确认成交后资金到账\n\n"
    else:
        report += "### 🟡 持仓观察建议\n"
        report += "**建议操作**: 继续持有，密切监控\n"
        report += "**理由**: 当前价格仍在止损位之上，可继续观察\n\n"
    
    # 资金回收和再投资建议
    report += "## 4. 资金回收和再投资建议\n"
    report += f"- **可回收资金**: ¥{analysis_data['recovered_cash']:,.2f}\n"
    report += "- **建议再投资策略**:\n"
    report += "  1. **短期观望**: 保留现金1-2周，观察市场机会\n"
    report += "  2. **分散投资**: 将资金分散到2-3只不同行业股票\n"
    report += "  3. **稳健选择**: 考虑低估值蓝筹股或指数基金\n"
    report += "  4. **止损设置**: 新投资严格设置5-8%止损位\n\n"
    
    report += "**具体标的建议**:\n"
    report += "- 消费板块：贵州茅台、五粮液\n"
    report += "- 金融板块：招商银行、中国平安\n"
    report += "- 科技板块：腾讯控股、阿里巴巴\n"
    report += "- 指数基金：沪深300ETF、创业板ETF\n\n"
    
    # 风险提示
    report += "## 5. 风险提示\n"
    report += "⚠️ **投资有风险，决策需谨慎**\n"
    report += "- 以上分析基于当前市场情况和技术指标\n"
    report += "- 股市存在不确定性，价格可能继续波动\n"
    report += "- 建议结合个人风险承受能力做出最终决策\n"
    report += "- 止损操作可能产生交易费用和税费\n\n"
    
    # 总结
    report += "## 6. 总结\n"
    if analysis_data['is_below_stop_loss']:
        report += "**决策结论**: 立即执行止损操作，卖出全部持仓。\n"
        report += "**核心理由**: 严格遵守投资纪律，控制亏损在可接受范围内。\n"
    else:
        report += "**决策结论**: 继续持有，但需密切监控价格走势。\n"
    
    report += f"**分析时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report


def main():
    """主函数"""
    print("开始执行华联股份止损分析...")
    
    # 计算分析数据
    analysis_data = calculate_stop_loss_analysis()
    
    # 生成报告
    report = generate_analysis_report(analysis_data)
    
    # 输出到文件
    output_path = "/root/.openclaw/workspace/ai_agent/results/华联股份止损分析_2026-04-23.md"
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 分析报告已生成: {output_path}")
        
        # 打印关键结论
        print("\n" + "="*50)
        print("关键分析结论:")
        print("="*50)
        print(f"当前价格: ¥{analysis_data['current_price']}")
        print(f"止损价位: ¥{analysis_data['stop_loss_price']}")
        print(f"是否跌破止损: {'是' if analysis_data['is_below_stop_loss'] else '否'}")
        print(f"当前亏损: -¥{analysis_data['loss_amount']:,.2f} ({analysis_data['loss_percentage']}%)")
        print(f"建议操作: {'立即全部卖出止损' if analysis_data['is_below_stop_loss'] else '继续持有观察'}")
        print(f"可回收资金: ¥{analysis_data['recovered_cash']:,.2f}")
        
    except Exception as e:
        print(f"❌ 文件写入失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)