#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集合竞价分析系统 - 改进版
执行时间：每个交易日 9:15 (集合竞价结束时)
功能：分析集合竞价数据，提供开盘交易建议
"""

import requests
import json
import time
import datetime
from typing import Dict, List, Optional

class AuctionAnalyzer:
    def __init__(self):
        self.stocks_of_interest = [
            {"code": "601866", "name": "中远海发", "exchange": "sh"},
            {"code": "000882", "name": "华联股份", "exchange": "sz"}
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def safe_float(self, value: str, default: float = 0.0) -> float:
        """安全转换字符串为浮点数"""
        if not value or value == '':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(self, value: str, default: int = 0) -> int:
        """安全转换字符串为整数"""
        if not value or value == '':
            return default
        try:
            # 处理可能包含小数点的字符串（如"0.00"）
            float_val = float(value)
            return int(float_val)
        except (ValueError, TypeError):
            return default
    
    def get_auction_data(self, stock_code: str, exchange: str) -> Optional[Dict]:
        """获取集合竞价数据"""
        try:
            # 使用腾讯财经API获取详细数据
            symbol = f"{exchange}{stock_code}"
            url = f"http://qt.gtimg.cn/q={symbol}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.text
                # 解析腾讯财经返回的数据格式
                import re
                match = re.search(r'v_{}="([^"]*)"'.format(symbol), data)
                if match:
                    values = match.group(1).split('~')
                    print(f"Debug: {symbol} 原始数据长度: {len(values)}")
                    if len(values) > 10:  # 至少需要基本字段
                        auction_data = {
                            "code": stock_code,
                            "name": values[1] if len(values) > 1 else stock_code,
                            "current_price": self.safe_float(values[3] if len(values) > 3 else "0"),
                            "yesterday_close": self.safe_float(values[4] if len(values) > 4 else "0"),
                            "open_price": self.safe_float(values[5] if len(values) > 5 else "0"),
                            "volume": self.safe_int(values[13] if len(values) > 13 else "0"),
                            "amount": self.safe_float(values[37] if len(values) > 37 else "0"),
                            "high": self.safe_float(values[33] if len(values) > 33 else "0"),
                            "low": self.safe_float(values[34] if len(values) > 34 else "0"),
                            "bid_price": self.safe_float(values[9] if len(values) > 9 else "0"),  # 买一价
                            "ask_price": self.safe_float(values[19] if len(values) > 19 else "0"),  # 卖一价
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # 验证关键数据是否有效
                        if auction_data["current_price"] <= 0:
                            print(f"Warning: {symbol} 当前价格无效: {auction_data['current_price']}")
                            return None
                        
                        return auction_data
        except Exception as e:
            print(f"获取{stock_code}集合竞价数据失败: {e}")
        
        return None
    
    def analyze_auction(self, auction_data: Dict) -> Dict:
        """分析集合竞价数据"""
        analysis = {
            "code": auction_data["code"],
            "name": auction_data["name"],
            "current_price": auction_data["current_price"],
            "open_price": auction_data["open_price"],
            "yesterday_close": auction_data["yesterday_close"],
            "volume": auction_data["volume"],
            "price_change_pct": 0,
            "gap_up": False,
            "gap_down": False,
            "volume_significance": "normal",
            "recommendation": "",
            "risk_level": "medium"
        }
        
        # 计算涨跌幅
        if auction_data["yesterday_close"] > 0:
            analysis["price_change_pct"] = (
                (auction_data["current_price"] - auction_data["yesterday_close"]) / 
                auction_data["yesterday_close"] * 100
            )
        
        # 判断跳空缺口
        if analysis["price_change_pct"] > 2:
            analysis["gap_up"] = True
        elif analysis["price_change_pct"] < -2:
            analysis["gap_down"] = True
        
        # 成交量分析（简化版，实际需要历史数据对比）
        if auction_data["volume"] > 1000000:  # 大于100万股
            analysis["volume_significance"] = "high"
        elif auction_data["volume"] < 100000:  # 小于10万股
            analysis["volume_significance"] = "low"
        
        # 生成交易建议
        self._generate_recommendation(analysis, auction_data)
        
        return analysis
    
    def _generate_recommendation(self, analysis: Dict, auction_data: Dict):
        """生成交易建议"""
        price_change = analysis["price_change_pct"]
        volume_level = analysis["volume_significance"]
        
        # 中远海发特定逻辑
        if analysis["code"] == "601866":
            if 2.50 <= auction_data["current_price"] <= 2.70:
                if price_change > 0:
                    analysis["recommendation"] = "✅ 股价在目标区间且上涨，可考虑买入"
                    analysis["risk_level"] = "low"
                else:
                    analysis["recommendation"] = "⚠️ 股价在目标区间但下跌，谨慎观察"
                    analysis["risk_level"] = "medium"
            elif auction_data["current_price"] < 2.50:
                if price_change > 1:
                    analysis["recommendation"] = "📈 股价低于目标但强势上涨，关注突破机会"
                    analysis["risk_level"] = "medium"
                else:
                    analysis["recommendation"] = "📉 股价低于目标区间，暂不建议买入"
                    analysis["risk_level"] = "high"
            else:
                analysis["recommendation"] = f"💰 股价高于目标区间({auction_data['current_price']:.2f})，等待回调"
                analysis["risk_level"] = "high"
        
        # 华联股份特定逻辑
        elif analysis["code"] == "000882":
            cost_price = 1.779  # 从之前的分析中获取的成本价
            if auction_data["current_price"] >= cost_price:
                if price_change > 0:
                    analysis["recommendation"] = "✅ 股价回到成本线以上且上涨，可持有"
                    analysis["risk_level"] = "low"
                else:
                    analysis["recommendation"] = "⚠️ 股价在成本线附近，谨慎持有"
                    analysis["risk_level"] = "medium"
            else:
                stop_loss_price = 1.60
                if auction_data["current_price"] <= stop_loss_price:
                    analysis["recommendation"] = "🚨 股价触及止损位，建议减仓或清仓"
                    analysis["risk_level"] = "very_high"
                elif price_change > 0:
                    analysis["recommendation"] = "📈 股价虽低于成本但上涨，继续持有观察"
                    analysis["risk_level"] = "medium"
                else:
                    analysis["recommendation"] = "📉 股价低于成本且下跌，密切关注"
                    analysis["risk_level"] = "high"
        
        # 通用逻辑
        else:
            if price_change > 3 and volume_level == "high":
                analysis["recommendation"] = "🚀 强势高开且放量，积极关注"
                analysis["risk_level"] = "low"
            elif price_change < -3 and volume_level == "high":
                analysis["recommendation"] = "💣 弱势低开且放量，谨慎回避"
                analysis["risk_level"] = "very_high"
            elif abs(price_change) <= 1:
                analysis["recommendation"] = "🔄 平稳开盘，观望为主"
                analysis["risk_level"] = "medium"
    
    def run_analysis(self) -> List[Dict]:
        """执行完整的集合竞价分析"""
        results = []
        
        print("=== 股票集合竞价分析报告 ===")
        print(f"分析时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for stock in self.stocks_of_interest:
            print(f"正在分析 {stock['name']} ({stock['code']})...")
            auction_data = self.get_auction_data(stock['code'], stock['exchange'])
            
            if auction_data:
                analysis = self.analyze_auction(auction_data)
                results.append(analysis)
                
                # 打印分析结果
                print(f"📊 {analysis['name']} ({analysis['code']})")
                print(f"   开盘价: ¥{analysis['current_price']:.2f}")
                print(f"   昨收价: ¥{analysis['yesterday_close']:.2f}")
                print(f"   涨跌幅: {analysis['price_change_pct']:+.2f}%")
                print(f"   成交量: {analysis['volume']:,}")
                print(f"   建议: {analysis['recommendation']}")
                print(f"   风险等级: {analysis['risk_level']}")
                print()
            else:
                print(f"❌ 无法获取 {stock['name']} ({stock['code']}) 的有效数据")
                print()
        
        return results

def main():
    analyzer = AuctionAnalyzer()
    results = analyzer.run_analysis()
    
    # 保存结果到文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"/root/.openclaw/workspace/ai_agent/results/auction_analysis_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"分析结果已保存至: {result_file}")
    
    # 如果没有获取到任何数据，尝试使用备用方法
    if not results:
        print("\n⚠️ 主要API数据获取失败，尝试备用方法...")
        backup_results = try_backup_methods()
        if backup_results:
            backup_file = f"/root/.openclaw/workspace/ai_agent/results/auction_analysis_backup_{timestamp}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_results, f, ensure_ascii=False, indent=2)
            print(f"备用分析结果已保存至: {backup_file}")
            results = backup_results
    
    return results

def try_backup_methods():
    """尝试备用数据获取方法"""
    results = []
    
    # 尝试新浪API
    stocks = [
        {"code": "sh601866", "name": "中远海发", "short_code": "601866"},
        {"code": "sz000882", "name": "华联股份", "short_code": "000882"}
    ]
    
    for stock in stocks:
        try:
            url = f"http://hq.sinajs.cn/list={stock['code']}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.text
                if '="' in data:
                    parts = data.split('"')[1].split(',')
                    if len(parts) > 3:
                        current_price = float(parts[3]) if parts[3] else 0
                        yesterday_close = float(parts[2]) if parts[2] else 0
                        open_price = float(parts[1]) if parts[1] else 0
                        volume = int(parts[8]) if parts[8] else 0
                        
                        if current_price > 0:
                            analysis = {
                                "code": stock["short_code"],
                                "name": stock["name"],
                                "current_price": current_price,
                                "open_price": open_price,
                                "yesterday_close": yesterday_close,
                                "volume": volume,
                                "price_change_pct": ((current_price - yesterday_close) / yesterday_close * 100) if yesterday_close > 0 else 0,
                                "recommendation": "备用API数据 - 请验证准确性",
                                "risk_level": "medium"
                            }
                            results.append(analysis)
                            print(f"✅ 通过新浪API获取到 {stock['name']} 数据")
                        else:
                            print(f"❌ {stock['name']} 新浪API返回无效价格")
                    else:
                        print(f"❌ {stock['name']} 新浪API数据格式异常")
                else:
                    print(f"❌ {stock['name']} 新浪API返回空数据")
            else:
                print(f"❌ {stock['name']} 新浪API请求失败")
        except Exception as e:
            print(f"❌ {stock['name']} 新浪API异常: {e}")
    
    return results

if __name__ == "__main__":
    main()