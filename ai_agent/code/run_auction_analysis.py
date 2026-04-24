#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行集合竞价分析的入口脚本（修复版）
"""

import sys
import os
sys.path.append('/root/.openclaw/workspace/ai_agent/code')

from auction_analysis_fixed import AuctionAnalyzer

def main():
    """主函数"""
    print("=== 股票监控系统 - 集合竞价分析 ===")
    
    # 创建分析器实例
    analyzer = AuctionAnalyzer()
    
    # 强制执行分析（忽略时间检查，用于测试或手动触发）
    force_run = '--force' in sys.argv
    
    if force_run:
        print("强制执行模式 - 忽略时间检查")
        results = analyzer.run_auction_analysis()
    else:
        # 检查是否为集合竞价时间
        if not analyzer.is_auction_time():
            print("当前不是集合竞价时间，跳过分析")
            return
            
        results = analyzer.run_auction_analysis()
    
    # 保存结果
    if results:
        # 判断是早盘还是尾盘
        import datetime
        now = datetime.datetime.now().time()
        if datetime.time(9, 15) <= now <= datetime.time(9, 25):
            session_type = "morning"
        elif datetime.time(14, 57) <= now <= datetime.time(15, 0):
            session_type = "afternoon"
        else:
            session_type = "manual"  # 手动执行
            
        analyzer.save_results(results, session_type)
        
        # 输出摘要
        bullish_count = sum(1 for r in results if r['sentiment'] == 'bullish')
        bearish_count = sum(1 for r in results if r['sentiment'] == 'bearish')
        neutral_count = len(results) - bullish_count - bearish_count
        
        print(f"\n分析摘要:")
        print(f"  总股票数: {len(results)}")
        print(f"  看涨: {bullish_count}")
        print(f"  看跌: {bearish_count}")
        print(f"  中性: {neutral_count}")
        
        # 生成简要报告
        report = f"集合竞价分析完成！监控{len(results)}只股票，{bullish_count}只看涨，{bearish_count}只看跌。"
        print(f"\n报告: {report}")
        
        # 保存简要报告
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"/root/.openclaw/workspace/ai_agent/results/auction_summary_{session_type}_{timestamp}.txt"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"简要报告已保存到: {report_file}")
        except Exception as e:
            print(f"保存简要报告失败: {e}")

if __name__ == "__main__":
    main()