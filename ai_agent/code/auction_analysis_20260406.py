#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票集合竞价分析系统 - 2026年4月6日执行版
执行时间: 2026-04-06 09:15 (集合竞价结束时)
功能: 分析今日集合竞价数据，提供开盘交易建议
"""

import requests
import json
import time
import datetime
import os
from typing import Dict, List, Optional

class AuctionAnalyzer20260406:
    def __init__(self):
        # 关注的股票列表（包含持仓股和目标股）
        self.stocks_of_interest = [
            {"code": "601866", "name": "中远海发", "exchange": "sh"},
            {"code": "000882", "name": "华联股份", "exchange": "sz"}
        ]
        
        # 持仓信息
        self.holding_info = {
            "000882": {
                'cost_price': 1.779,
                'stop_loss': 1.60,
                'take_profit': 2.00,
                'quantity': 22600
            }
        }
        
        # 目标买入区间
        self.target_buy_ranges = {
            "601866": {"min": 2.50, "max": 2.70}
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.results_dir = "/root/.openclaw/workspace/ai_agent/results"
        self.today = "2026-04-06"
    
    def safe_float(self, value: str, default: float = 0.0) -> float:
        """安全转换字符串为浮点数"""
        if not value or value == '' or value == '0.00':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(self, value: str, default: int = 0) -> int:
        """安全转换字符串为整数"""
        if not value or value == '' or value == '0':
            return default
        try:
            float_val = float(value)
            return int(float_val)
        except (ValueError, TypeError):
            return default
    
    def get_auction_data_tencent(self, stock_code: str, exchange: str) -> Optional[Dict]:
        """使用腾讯财经API获取集合竞价数据"""
        try:
            symbol = f"{exchange}{stock_code}"
            url = f"http://qt.gtimg.cn/q={symbol}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.text
                import re
                match = re.search(r'v_{}="([^"]*)"'.format(symbol), data)
                if match:
                    values = match.group(1).split('~')
                    if len(values) > 37:  # 需要足够多的字段
                        auction_data = {
                            "code": stock_code,
                            "name": values[1] if len(values) > 1 else stock_code,
                            "current_price": self.safe_float(values[3]),
                            "yesterday_close": self.safe_float(values[4]),
                            "open_price": self.safe_float(values[5]),
                            "volume": self.safe_int(values[13]),
                            "amount": self.safe_float(values[37]),
                            "high": self.safe_float(values[33]),
                            "low": self.safe_float(values[34]),
                            "bid_price": self.safe_float(values[9]),  # 买一价
                            "ask_price": self.safe_float(values[19]),  # 卖一价
                            "timestamp": f"{self.today} 09:25:00"
                        }
                        
                        # 验证关键数据有效性
                        if auction_data["current_price"] > 0 and auction_data["yesterday_close"] > 0:
                            return auction_data
                        else:
                            print(f"Warning: {symbol} 数据无效 - price: {auction_data['current_price']}, prev: {auction_data['yesterday_close']}")
        except Exception as e:
            print(f"腾讯API获取{stock_code}数据失败: {e}")
        return None
    
    def get_auction_data_sina(self, stock_code: str, exchange: str) -> Optional[Dict]:
        """使用新浪API作为备用方案"""
        try:
            symbol = f"{exchange}{stock_code}"
            url = f"http://hq.sinajs.cn/list={symbol}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.text
                if '="' in data:
                    parts = data.split('"')[1].split(',')
                    if len(parts) >= 9:
                        current_price = self.safe_float(parts[3])
                        yesterday_close = self.safe_float(parts[2])
                        open_price = self.safe_float(parts[1])
                        volume = self.safe_int(parts[8])
                        
                        if current_price > 0 and yesterday_close > 0:
                            auction_data = {
                                "code": stock_code,
                                "name": parts[0],
                                "current_price": current_price,
                                "yesterday_close": yesterday_close,
                                "open_price": open_price,
                                "volume": volume,
                                "amount": 0,  # 新浪API不直接提供成交额
                                "high": self.safe_float(parts[4]),
                                "low": self.safe_float(parts[5]),
                                "bid_price": self.safe_float(parts[6]),
                                "ask_price": self.safe_float(parts[7]),
                                "timestamp": f"{self.today} 09:25:00"
                            }
                            return auction_data
        except Exception as e:
            print(f"新浪API获取{stock_code}数据失败: {e}")
        return None
    
    def get_auction_data(self, stock_code: str, exchange: str) -> Optional[Dict]:
        """获取集合竞价数据（优先腾讯，备用新浪）"""
        # 尝试腾讯API
        data = self.get_auction_data_tencent(stock_code, exchange)
        if data:
            print(f"✅ 腾讯API成功获取 {stock_code} 数据")
            return data
        
        # 腾讯失败，尝试新浪API
        data = self.get_auction_data_sina(stock_code, exchange)
        if data:
            print(f"✅ 新浪API成功获取 {stock_code} 数据")
            return data
        
        print(f"❌ 无法获取 {stock_code} 的有效数据")
        return None
    
    def analyze_auction(self, auction_data: Dict) -> Dict:
        """分析集合竞价数据并生成建议"""
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
            "recommendations": [],
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
        
        # 成交量分析（简化版）
        if auction_data["volume"] > 1000000:  # 大于100万股
            analysis["volume_significance"] = "high"
        elif auction_data["volume"] < 100000:  # 小于10万股
            analysis["volume_significance"] = "low"
        
        # 通用市场分析
        self._add_general_recommendations(analysis)
        
        # 特定股票分析
        self._add_specific_recommendations(analysis, auction_data)
        
        # 确定风险等级
        self._determine_risk_level(analysis)
        
        return analysis
    
    def _add_general_recommendations(self, analysis: Dict):
        """添加通用推荐"""
        price_change = analysis["price_change_pct"]
        volume_level = analysis["volume_significance"]
        
        if price_change > 3 and volume_level == "high":
            analysis["recommendations"].append("🚀 强势高开且放量，积极关注")
        elif price_change > 3 and volume_level == "normal":
            analysis["recommendations"].append("📈 强势高开，但成交量一般")
        elif price_change < -3 and volume_level == "high":
            analysis["recommendations"].append("💣 弱势低开且放量，谨慎回避")
        elif price_change < -3 and volume_level == "normal":
            analysis["recommendations"].append("📉 弱势低开，但成交量一般")
        elif abs(price_change) <= 1:
            analysis["recommendations"].append("🔄 平稳开盘，观望为主")
        elif price_change > 0:
            analysis["recommendations"].append("🟢 温和上涨开盘")
        else:
            analysis["recommendations"].append("🔴 温和下跌开盘")
    
    def _add_specific_recommendations(self, analysis: Dict, auction_data: Dict):
        """添加特定股票推荐"""
        code = analysis["code"]
        current_price = auction_data["current_price"]
        
        # 持仓股分析（华联股份）
        if code in self.holding_info:
            holding = self.holding_info[code]
            cost_price = holding['cost_price']
            stop_loss = holding['stop_loss']
            take_profit = holding['take_profit']
            
            if current_price <= stop_loss:
                analysis["recommendations"].append(f"🚨 触及止损位 ¥{stop_loss:.3f}，建议考虑止损")
            elif current_price >= take_profit:
                analysis["recommendations"].append(f"🎯 触及止盈位 ¥{take_profit:.3f}，建议考虑止盈")
            elif current_price < cost_price * 0.9:
                analysis["recommendations"].append(f"📉 浮亏较大（成本 ¥{cost_price:.3f}），密切关注")
            elif current_price > cost_price * 1.1:
                analysis["recommendations"].append(f"📈 盈利良好（成本 ¥{cost_price:.3f}），可考虑部分止盈")
            elif current_price >= cost_price:
                analysis["recommendations"].append(f"✅ 股价回到成本线以上（成本 ¥{cost_price:.3f}），可继续持有")
            else:
                analysis["recommendations"].append(f"⚠️ 股价低于成本线（成本 ¥{cost_price:.3f}），谨慎持有")
        
        # 目标股分析（中远海发）
        if code in self.target_buy_ranges:
            target_range = self.target_buy_ranges[code]
            buy_min, buy_max = target_range["min"], target_range["max"]
            
            if buy_min <= current_price <= buy_max:
                analysis["recommendations"].append(f"💡 进入目标买入区间 [¥{buy_min:.2f}, ¥{buy_max:.2f}]，可考虑建仓")
            elif current_price < buy_min:
                analysis["recommendations"].append(f"🔍 低于目标区间（目标 ¥{buy_min:.2f}-{buy_max:.2f}），继续观察")
            elif current_price > buy_max:
                analysis["recommendations"].append(f"🚀 突破目标区间（目标 ¥{buy_min:.2f}-{buy_max:.2f}），可能已错过最佳买点")
    
    def _determine_risk_level(self, analysis: Dict):
        """确定风险等级"""
        price_change = analysis["price_change_pct"]
        recommendations = analysis["recommendations"]
        
        # 检查是否有高风险信号
        high_risk_signals = sum([
            "止损" in rec for rec in recommendations
        ])
        
        if high_risk_signals > 0:
            analysis["risk_level"] = "very_high"
        elif price_change < -5:
            analysis["risk_level"] = "high"
        elif price_change > 5:
            analysis["risk_level"] = "low"
        elif -2 <= price_change <= 2:
            analysis["risk_level"] = "medium"
        elif price_change > 2:
            analysis["risk_level"] = "low_medium"
        else:
            analysis["risk_level"] = "medium_high"
    
    def run_analysis(self) -> List[Dict]:
        """执行完整的集合竞价分析"""
        results = []
        
        print("=== 📊 股票集合竞价分析报告 ===")
        print(f"📅 分析日期: {self.today}")
        print(f"⏰ 分析时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for stock in self.stocks_of_interest:
            print(f"🔍 正在分析 {stock['name']} ({stock['code']})...")
            auction_data = self.get_auction_data(stock['code'], stock['exchange'])
            
            if auction_data:
                analysis = self.analyze_auction(auction_data)
                results.append(analysis)
                
                # 打印详细分析结果
                print(f"📈 {analysis['name']} ({analysis['code']})")
                print(f"   开盘价: ¥{analysis['current_price']:.3f}")
                print(f"   昨收价: ¥{analysis['yesterday_close']:.3f}")
                print(f"   涨跌幅: {analysis['price_change_pct']:+.2f}%")
                print(f"   成交量: {analysis['volume']:,}")
                print(f"   风险等级: {analysis['risk_level']}")
                print("   操作建议:")
                for i, rec in enumerate(analysis['recommendations'], 1):
                    print(f"     {i}. {rec}")
                print()
            else:
                error_analysis = {
                    "code": stock['code'],
                    "name": stock['name'],
                    "error": "无法获取有效数据",
                    "recommendations": ["❌ 数据获取失败，请手动检查"],
                    "risk_level": "unknown"
                }
                results.append(error_analysis)
                print(f"❌ 无法获取 {stock['name']} ({stock['code']}) 的有效数据")
                print()
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """生成完整分析报告"""
        report_lines = []
        report_lines.append("📊 股票集合竞价分析报告")
        report_lines.append("=" * 60)
        report_lines.append(f"📅 日期: {self.today}")
        report_lines.append(f"⏰ 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        for result in results:
            if "error" in result:
                report_lines.append(f"❌ {result['name']} ({result['code']})")
                report_lines.append(f"   错误: {result['error']}")
                for rec in result['recommendations']:
                    report_lines.append(f"   • {rec}")
            else:
                report_lines.append(f"📈 {result['name']} ({result['code']})")
                report_lines.append(f"   当前价格: ¥{result['current_price']:.3f}")
                report_lines.append(f"   昨日收盘: ¥{result['yesterday_close']:.3f}")
                report_lines.append(f"   涨跌幅: {result['price_change_pct']:+.2f}%")
                report_lines.append(f"   成交量: {result['volume']:,}")
                report_lines.append(f"   风险等级: {result['risk_level']}")
                report_lines.append("   操作建议:")
                for rec in result['recommendations']:
                    report_lines.append(f"     • {rec}")
            
            report_lines.append("-" * 40)
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_results(self, results: List[Dict], report: str):
        """保存分析结果和报告"""
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 保存JSON结果
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(self.results_dir, f"auction_analysis_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 保存文本报告
        txt_file = os.path.join(self.results_dir, f"auction_report_{timestamp}.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 分析结果已保存至: {json_file}")
        print(f"✅ 分析报告已保存至: {txt_file}")
        
        return json_file, txt_file

def main():
    """主函数"""
    print("🔄 开始执行2026年4月6日股票集合竞价分析...")
    
    analyzer = AuctionAnalyzer20260406()
    results = analyzer.run_analysis()
    
    if results:
        report = analyzer.generate_report(results)
        print("\n" + "="*60)
        print(report)
        print("="*60)
        
        json_file, txt_file = analyzer.save_results(results, report)
        
        # 返回结果用于后续处理
        return {
            "status": "success",
            "results": results,
            "report": report,
            "json_file": json_file,
            "txt_file": txt_file
        }
    else:
        error_msg = "❌ 集合竞价分析失败：未获取到任何有效数据"
        print(error_msg)
        return {"status": "error", "message": error_msg}

if __name__ == "__main__":
    result = main()
    if result["status"] == "success":
        print("\n✅ 集合竞价分析任务完成！")
    else:
        print(f"\n{result['message']}")