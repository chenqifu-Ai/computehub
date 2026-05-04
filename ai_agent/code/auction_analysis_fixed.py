#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集合竞价分析系统（修复版）
用于A股市场早盘(9:15-9:25)和尾盘(14:57-15:00)集合竞价分析
"""

import json
import time
import datetime
import requests
import re
from typing import Dict, List, Optional

class AuctionAnalyzer:
    def __init__(self):
        self.config = self.load_config()
        self.watchlist = self.get_watchlist()
        
    def load_config(self) -> dict:
        """加载股票监控配置"""
        try:
            with open('/root/.openclaw/workspace/stock_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载stock_config.json失败: {e}")
            return {}
            
    def get_watchlist(self) -> List[str]:
        """获取监控股票列表"""
        watchlist = []
        try:
            # 从stock_config.json获取
            if 'watchlist' in self.config:
                watchlist.extend(self.config['watchlist'])
                
            # 从stock_monitor_config.json获取
            with open('/root/.openclaw/workspace/stock_monitor_config.json', 'r', encoding='utf-8') as f:
                monitor_config = json.load(f)
                if 'monitoring_stocks' in monitor_config:
                    watchlist.extend(monitor_config['monitoring_stocks'])
                    
        except Exception as e:
            print(f"加载监控股票列表失败: {e}")
            
        # 去重并转换格式
        unique_stocks = list(set(watchlist))
        formatted_stocks = []
        for stock in unique_stocks:
            if stock.endswith('.SS') or stock.endswith('.SZ'):
                # 转换为腾讯财经格式
                code = stock.split('.')[0]
                if stock.endswith('.SS'):
                    formatted_stocks.append(f'sh{code}')
                else:
                    formatted_stocks.append(f'sz{code}')
            elif stock.startswith('SH') or stock.startswith('SZ'):
                # 转换SH000001格式为sh000001
                if stock.startswith('SH'):
                    formatted_stocks.append(f'sh{stock[2:]}')
                else:
                    formatted_stocks.append(f'sz{stock[2:]}')
            elif stock in ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'BABA']:
                # 美股使用不同的格式
                formatted_stocks.append(stock)
            else:
                formatted_stocks.append(stock)
                
        return formatted_stocks
        
    def safe_float(self, value: str) -> float:
        """安全转换字符串为浮点数"""
        if not value or value == '0.00' or value == '':
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
            
    def safe_int(self, value: str) -> int:
        """安全转换字符串为整数"""
        if not value or value == '0' or value == '' or value == '0.00':
            return 0
        try:
            # 移除可能的非数字字符
            clean_value = re.sub(r'[^\d\-]', '', value)
            if clean_value:
                return int(clean_value)
            return 0
        except (ValueError, TypeError):
            return 0
        
    def get_auction_data(self, symbol: str) -> Optional[Dict]:
        """获取集合竞价数据"""
        try:
            # 使用腾讯财经API获取实时数据
            url = f"http://qt.gtimg.cn/q={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # 处理编码问题
                response.encoding = 'gbk'
                data = response.text
                
                # 解析数据格式: v_sh000001="1~上证指数~000001~3986.22~3966.17~..."
                pattern = r'v_{}="([^"]*)"'.format(symbol)
                match = re.search(pattern, data)
                if match:
                    values_str = match.group(1)
                    # 分割数据
                    values = values_str.split('~')
                    
                    if len(values) > 10:
                        current_price = self.safe_float(values[3])
                        yesterday_close = self.safe_float(values[4])
                        
                        auction_data = {
                            'symbol': symbol,
                            'current_price': current_price,
                            'yesterday_close': yesterday_close,
                            'opening_price': self.safe_float(values[5]),
                            'volume': self.safe_int(values[6]),  # 成交量在第7个位置
                            'turnover': self.safe_float(values[37]) if len(values) > 37 else 0,
                            'bid_volume': self.safe_int(values[10]) if len(values) > 10 else 0,  # 买一量
                            'ask_volume': self.safe_int(values[11]) if len(values) > 11 else 0,  # 卖一量
                            'price_change_percent': ((current_price - yesterday_close) / yesterday_close * 100) if yesterday_close != 0 else 0
                        }
                        return auction_data
        except Exception as e:
            print(f"获取{symbol}集合竞价数据失败: {e}")
            
        return None
        
    def analyze_auction(self, auction_data: Dict) -> Dict:
        """分析集合竞价数据"""
        analysis = {
            'symbol': auction_data['symbol'],
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': auction_data['current_price'],
            'price_change_percent': auction_data['price_change_percent'],
            'volume_ratio': 0,
            'sentiment': 'neutral',
            'recommendations': []
        }
        
        # 计算量比（简化处理）
        if auction_data['volume'] > 0:
            analysis['volume_ratio'] = min(auction_data['volume'] / 100000, 10)  # 简化计算
            
        # 情绪分析
        if auction_data['price_change_percent'] > 2.0:
            analysis['sentiment'] = 'bullish'
        elif auction_data['price_change_percent'] < -2.0:
            analysis['sentiment'] = 'bearish'
            
        # 生成建议
        if analysis['sentiment'] == 'bullish' and auction_data['volume'] > 100000:
            analysis['recommendations'].append('高开高量，可考虑关注')
        elif analysis['sentiment'] == 'bearish' and auction_data['volume'] > 100000:
            analysis['recommendations'].append('低开高量，注意风险')
        elif abs(auction_data['price_change_percent']) < 0.5 and auction_data['volume'] > 500000:
            analysis['recommendations'].append('价格稳定但量能充足，关注后续走势')
            
        return analysis
        
    def run_auction_analysis(self) -> List[Dict]:
        """执行集合竞价分析"""
        print(f"开始集合竞价分析 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        results = []
        
        for symbol in self.watchlist:
            # 跳过美股，因为腾讯财经主要支持A股
            if symbol in ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'BABA']:
                continue
                
            print(f"分析股票: {symbol}")
            auction_data = self.get_auction_data(symbol)
            if auction_data and auction_data['current_price'] > 0:
                analysis = self.analyze_auction(auction_data)
                results.append(analysis)
                print(f"  价格: {auction_data['current_price']:.2f}, "
                      f"涨跌幅: {auction_data['price_change_percent']:.2f}%, "
                      f"情绪: {analysis['sentiment']}")
            else:
                print(f"  无法获取{symbol}的有效数据")
                
        return results
        
    def save_results(self, results: List[Dict], session_type: str = "auction"):
        """保存分析结果"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"/root/.openclaw/workspace/ai_agent/results/auction_analysis_{session_type}_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"分析结果已保存到: {filename}")
        except Exception as e:
            print(f"保存结果失败: {e}")
            
    def is_auction_time(self) -> bool:
        """检查是否为集合竞价时间"""
        now = datetime.datetime.now()
        current_time = now.time()
        
        # 早盘集合竞价: 9:15-9:25
        morning_start = datetime.time(9, 15)
        morning_end = datetime.time(9, 25)
        
        # 尾盘集合竞价: 14:57-15:00
        afternoon_start = datetime.time(14, 57)
        afternoon_end = datetime.time(15, 0)
        
        if (morning_start <= current_time <= morning_end or 
            afternoon_start <= current_time <= afternoon_end):
            # 检查是否为交易日（周一到周五）
            if now.weekday() < 5:  # 0=Monday, 4=Friday
                return True
                
        return False

def main():
    analyzer = AuctionAnalyzer()
    
    # 检查是否为集合竞价时间
    if not analyzer.is_auction_time():
        print("当前不是集合竞价时间，跳过分析")
        return
        
    # 执行分析
    results = analyzer.run_auction_analysis()
    
    # 保存结果
    if results:
        # 判断是早盘还是尾盘
        now = datetime.datetime.now().time()
        if datetime.time(9, 15) <= now <= datetime.time(9, 25):
            session_type = "morning"
        else:
            session_type = "afternoon"
            
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

if __name__ == "__main__":
    main()