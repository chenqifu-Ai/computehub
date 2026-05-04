#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的集合竞价分析
"""

import sys
import os
sys.path.append('/root/.openclaw/workspace/ai_agent/code')

from auction_analysis_fixed import AuctionAnalyzer

def main():
    """测试函数"""
    print("=== 测试修复后的集合竞价分析 ===")
    
    # 创建分析器实例
    analyzer = AuctionAnalyzer()
    
    # 执行分析（忽略时间检查）
    print("开始测试分析...")
    results = analyzer.run_auction_analysis()
    
    # 输出结果
    print(f"\n测试完成，共分析 {len(results)} 只股票")
    
    if results:
        # 保存测试结果
        analyzer.save_results(results, "test")
        
        # 输出摘要
        bullish_count = sum(1 for r in results if r['sentiment'] == 'bullish')
        bearish_count = sum(1 for r in results if r['sentiment'] == 'bearish')
        neutral_count = len(results) - bullish_count - bearish_count
        
        print(f"\n测试摘要:")
        print(f"  总股票数: {len(results)}")
        print(f"  看涨: {bullish_count}")
        print(f"  看跌: {bearish_count}")
        print(f"  中性: {neutral_count}")

if __name__ == "__main__":
    main()