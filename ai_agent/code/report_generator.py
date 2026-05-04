#!/usr/bin/env python3
"""
数据报告生成脚本
生成JSON和Markdown格式的报告
"""

import json
import datetime
from pathlib import Path

def generate_report(competitor_data, hot_topics, market_trends):
    """生成综合报告"""
    report = {
        "report_date": datetime.datetime.now().isoformat(),
        "competitor_analysis": competitor_data,
        "hot_topics": hot_topics,
        "market_trends": market_trends,
        "summary": {
            "key_findings": [
                "AI大模型价格战持续",
                "多模态AI技术快速发展",
                "边缘计算市场稳步增长"
            ],
            "recommendations": [
                "关注AI价格战对行业影响",
                "投资多模态AI技术研发",
                "布局边缘计算基础设施"
            ]
        }
    }
    
    return report

def save_json_report(report, filename):
    """保存JSON报告"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

def save_markdown_report(report, filename):
    """保存Markdown报告"""
    md_content = f"# 数据部监控报告

"
    md_content += f"**报告日期**: {report['report_date']}

"
    
    md_content += "## 竞品动态分析

"
    for company, news in report['competitor_analysis'].items():
        md_content += f"### {company}
"
        for item in news:
            md_content += f"- {item['title']} ({item['date']})
"
        md_content += "
"
    
    md_content += "## 热点话题

"
    for topic in report['hot_topics']:
        md_content += f"### {topic['topic']} (热度: {topic['trend_level']})
"
        md_content += f"相关企业: {', '.join(topic['related_companies'])}
"
        for event in topic['recent_events']:
            md_content += f"- {event}
"
        md_content += "
"
    
    md_content += "## 市场趋势

"
    for trend in report['market_trends']:
        md_content += f"### {trend['trend']}
"
        md_content += f"增长率: {trend['growth_rate']}
"
        md_content += f"市场规模: {trend['market_size']}
"
        md_content += f"主要玩家: {', '.join(trend['key_players'])}
"
        for dev in trend['recent_developments']:
            md_content += f"- {dev}
"
        md_content += "
"
    
    md_content += "## 总结与建议

"
    md_content += "### 主要发现
"
    for finding in report['summary']['key_findings']:
        md_content += f"- {finding}
"
    
    md_content += "
### 建议
"
    for recommendation in report['summary']['recommendations']:
        md_content += f"- {recommendation}
"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md_content)

if __name__ == "__main__":
    # 示例数据
    competitor_data = {"百度": [{"title": "测试", "date": "2024-01-01"}]}
    hot_topics = [{"topic": "测试", "trend_level": "高"}]
    market_trends = [{"trend": "测试", "growth_rate": "高"}]
    
    report = generate_report(competitor_data, hot_topics, market_trends)
    save_json_report(report, "test_report.json")
    save_markdown_report(report, "test_report.md")
    print("测试报告生成完成")
