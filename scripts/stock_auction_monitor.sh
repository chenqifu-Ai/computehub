#!/bin/bash
# 股票集合竞价监控脚本
# 执行时间：每个交易日 9:15

set -e

WORKSPACE="/root/.openclaw/workspace"
SCRIPT_DIR="$WORKSPACE/ai_agent/code"
RESULT_DIR="$WORKSPACE/ai_agent/results"
LOG_FILE="$WORKSPACE/logs/stock_auction_$(date +%Y%m%d).log"

# 创建日志目录
mkdir -p "$WORKSPACE/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行股票集合竞价分析" >> "$LOG_FILE"

# 执行分析脚本
cd "$WORKSPACE"
python3 "$SCRIPT_DIR/auction_analysis_v2.py" >> "$LOG_FILE" 2>&1

# 检查是否生成了结果文件
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="$RESULT_DIR/auction_analysis_$TIMESTAMP.json"

if [ -f "$RESULT_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 分析完成，结果文件: $RESULT_FILE" >> "$LOG_FILE"
    
    # 生成Markdown报告
    python3 << EOF
import json
import datetime
import os

timestamp = "$TIMESTAMP"
result_file = "$RESULT_FILE"
report_file = "$RESULT_DIR/auction_analysis_report_\$(date +%Y%m%d).md"

if os.path.exists(result_file):
    with open(result_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    report_content = f"""# 📊 股票集合竞价分析报告

**分析时间**: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')}（星期{['一','二','三','四','五','六','日'][datetime.datetime.now().weekday()]}）  
**市场状态**: 集合竞价结束，即将开始连续竞价交易

---

## 🎯 关键股票分析
"""
    
    for result in results:
        if result['code'] == '601866':
            status = "股价高于目标区间(¥2.50-2.70)" if result['current_price'] > 2.70 else ("股价在目标区间内" if result['current_price'] >= 2.50 else "股价低于目标区间")
            recommendation = result['recommendation']
            risk_emoji = "⚠️" if result['risk_level'] == 'high' else ("✅" if result['risk_level'] == 'low' else "🔄")
        elif result['code'] == '000882':
            status = f"股价{'低于' if result['current_price'] < 1.779 else '高于'}持仓成本(¥1.779)"
            recommendation = result['recommendation']
            risk_emoji = "⚠️" if result['risk_level'] == 'high' else ("✅" if result['risk_level'] == 'low' else "🔄")
        else:
            status = "正常交易"
            recommendation = result['recommendation']
            risk_emoji = "⚠️" if result['risk_level'] == 'high' else ("✅" if result['risk_level'] == 'low' else "🔄")
        
        report_content += f"""
### {result['name']} ({result['code']})
- **当前价格**: ¥{result['current_price']:.2f}
- **昨日收盘**: ¥{result['yesterday_close']:.2f}
- **涨跌幅**: {result['price_change_pct']:+.2f}%
- **状态**: {status}
- **建议**: {recommendation}
- **风险等级**: {risk_emoji} {result['risk_level']}
"""
    
    report_content += f"""

---

## 📈 市场整体观察

- **集合竞价成交量**: 数据暂未完全更新（集合竞价刚结束）
- **市场情绪**: 相对平稳，重点关注个股表现
- **操作策略**: 
  - 中远海发：观望等待回调机会
  - 华联股份：严格控制风险，设置止损提醒

---

## ⏰ 后续监控计划

- **10:00**: 检查连续竞价30分钟后的价格走势
- **11:30**: 午盘前再次评估持仓情况
- **14:30**: 尾盘前最后确认当日操作策略

> **注**: 集合竞价数据可能存在延迟，实际开盘后请以实时行情为准。

---
*报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"报告已生成: {report_file}")
else:
    print("未找到结果文件，跳过报告生成")
EOF

else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 分析失败，未生成结果文件" >> "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 股票集合竞价分析执行完毕" >> "$LOG_FILE"