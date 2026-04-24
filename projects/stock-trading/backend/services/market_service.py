"""
市场数据服务
支持模拟数据和外部数据源
"""
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class MarketService:
    """市场数据服务"""
    
    def __init__(self):
        self.stock_list = self._init_stock_list()
        self._price_cache = {}
    
    def _init_stock_list(self) -> List[Dict]:
        """初始化股票列表"""
        return [
            {"code": "000001", "name": "平安银行", "market": "SZ", "industry": "银行"},
            {"code": "000002", "name": "万科A", "market": "SZ", "industry": "房地产"},
            {"code": "000063", "name": "中兴通讯", "market": "SZ", "industry": "通信"},
            {"code": "000333", "name": "美的集团", "market": "SZ", "industry": "家电"},
            {"code": "000651", "name": "格力电器", "market": "SZ", "industry": "家电"},
            {"code": "000858", "name": "五粮液", "market": "SZ", "industry": "白酒"},
            {"code": "000895", "name": "双汇发展", "market": "SZ", "industry": "食品"},
            {"code": "002415", "name": "海康威视", "market": "SZ", "industry": "电子"},
            {"code": "002594", "name": "比亚迪", "market": "SZ", "industry": "汽车"},
            {"code": "300059", "name": "东方财富", "market": "SZ", "industry": "金融"},
            {"code": "600000", "name": "浦发银行", "market": "SH", "industry": "银行"},
            {"code": "600036", "name": "招商银行", "market": "SH", "industry": "银行"},
            {"code": "600519", "name": "贵州茅台", "market": "SH", "industry": "白酒"},
            {"code": "600887", "name": "伊利股份", "market": "SH", "industry": "食品"},
            {"code": "601318", "name": "中国平安", "market": "SH", "industry": "保险"},
            {"code": "601398", "name": "工商银行", "market": "SH", "industry": "银行"},
            {"code": "601857", "name": "中国石油", "market": "SH", "industry": "能源"},
            {"code": "601888", "name": "中国中免", "market": "SH", "industry": "零售"},
            {"code": "603259", "name": "药明康德", "market": "SH", "industry": "医药"},
            {"code": "603288", "name": "海天味业", "market": "SH", "industry": "食品"},
        ]
    
    def get_stock_list(self, keyword: str = None, market: str = None) -> List[Dict]:
        """获取股票列表"""
        stocks = self.stock_list
        
        if keyword:
            keyword = keyword.lower()
            stocks = [s for s in stocks 
                     if keyword in s["code"].lower() or keyword in s["name"].lower()]
        
        if market:
            stocks = [s for s in stocks if s["market"] == market.upper()]
        
        return stocks
    
    def get_stock_info(self, code: str) -> Optional[Dict]:
        """获取股票信息"""
        for stock in self.stock_list:
            if stock["code"] == code:
                return stock
        return None
    
    def get_quote(self, code: str) -> Dict:
        """获取实时行情"""
        # 先从缓存获取
        if code in self._price_cache:
            base_price = self._price_cache[code]["base"]
        else:
            # 根据股票代码生成基准价格
            base_price = self._generate_base_price(code)
            self._price_cache[code] = {"base": base_price}
        
        # 生成模拟行情数据
        change_percent = random.uniform(-3, 3)
        change = base_price * change_percent / 100
        price = base_price + change
        
        return {
            "code": code,
            "name": self._get_stock_name(code),
            "price": round(price, 2),
            "open": round(base_price * (1 + random.uniform(-0.02, 0.02)), 2),
            "high": round(price * (1 + random.uniform(0, 0.02)), 2),
            "low": round(price * (1 - random.uniform(0, 0.02)), 2),
            "pre_close": round(base_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": random.randint(100000, 10000000),
            "amount": round(random.uniform(10000000, 1000000000), 2),
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    
    def get_quotes(self, codes: List[str]) -> List[Dict]:
        """批量获取行情"""
        return [self.get_quote(code) for code in codes]
    
    def get_kline(self, code: str, period: str = "daily", 
                   start_date: str = None, end_date: str = None,
                   count: int = 100) -> Dict:
        """获取K线数据"""
        # 尝试从akshare获取真实数据
        if HAS_AKSHARE:
            try:
                return self._get_kline_from_akshare(code, period, start_date, end_date, count)
            except Exception as e:
                print(f"获取akshare数据失败: {e}")
        
        # 使用模拟数据
        return self._generate_kline(code, period, start_date, end_date, count)
    
    def _get_kline_from_akshare(self, code: str, period: str,
                                  start_date: str, end_date: str, 
                                  count: int) -> Dict:
        """从akshare获取K线数据"""
        # 根据市场确定代码格式
        stock_info = self.get_stock_info(code)
        if not stock_info:
            raise ValueError(f"未知股票代码: {code}")
        
        # akshare代码格式
        symbol = code
        
        # 获取K线数据
        if period == "daily":
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                    start_date=start_date, end_date=end_date, 
                                    adjust="qfq")
        elif period == "weekly":
            df = ak.stock_zh_a_hist(symbol=symbol, period="weekly",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
        elif period == "monthly":
            df = ak.stock_zh_a_hist(symbol=symbol, period="monthly",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
        else:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
        
        # 转换为标准格式
        klines = []
        for _, row in df.iterrows():
            klines.append({
                "date": row["日期"].strftime("%Y-%m-%d") if hasattr(row["日期"], "strftime") else str(row["日期"]),
                "open": float(row["开盘"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "close": float(row["收盘"]),
                "volume": int(row["成交量"]),
                "amount": float(row["成交额"])
            })
        
        return {
            "code": code,
            "name": stock_info["name"],
            "period": period,
            "count": len(klines),
            "data": klines
        }
    
    def _generate_kline(self, code: str, period: str,
                         start_date: str, end_date: str,
                         count: int) -> Dict:
        """生成模拟K线数据"""
        stock_info = self.get_stock_info(code)
        name = stock_info["name"] if stock_info else code
        
        # 解析日期
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end = datetime.now()
        
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            if period == "daily":
                start = end - timedelta(days=count)
            elif period == "weekly":
                start = end - timedelta(weeks=count)
            else:
                start = end - timedelta(days=count * 30)
        
        # 生成基准价格和波动率
        base_price = self._generate_base_price(code)
        volatility = random.uniform(0.015, 0.03)
        
        # 生成K线数据
        klines = []
        current_date = start
        price = base_price
        
        while current_date <= end:
            # 生成日内波动
            daily_change = random.gauss(0, volatility)
            open_price = price * (1 + random.uniform(-0.01, 0.01))
            close_price = open_price * (1 + daily_change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.015))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.015))
            
            # 确保价格合理
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            volume = random.randint(1000000, 50000000)
            amount = volume * close_price * random.uniform(0.9, 1.1)
            
            klines.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume,
                "amount": round(amount, 2)
            })
            
            # 更新价格
            price = close_price
            current_date += timedelta(days=1)
        
        return {
            "code": code,
            "name": name,
            "period": period,
            "count": len(klines),
            "data": klines
        }
    
    def _generate_base_price(self, code: str) -> float:
        """根据股票代码生成基准价格"""
        # 使用代码数字生成可复现的基准价格
        code_num = sum(int(c) for c in code if c.isdigit())
        if code_num == 0:
            code_num = 50
        
        # 价格范围 5-500
        base = (code_num % 100) * 5 + 5
        return max(5, min(500, base))
    
    def _get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        stock = self.get_stock_info(code)
        return stock["name"] if stock else code
    
    def search_stocks(self, keyword: str) -> List[Dict]:
        """搜索股票"""
        return self.get_stock_list(keyword=keyword)
    
    def get_hot_stocks(self, limit: int = 10) -> List[Dict]:
        """获取热门股票"""
        hot_codes = ["600519", "000858", "000333", "002594", "600036",
                     "601318", "000001", "600887", "603259", "300059"]
        return [self.get_quote(code) for code in hot_codes[:limit]]
    
    def get_industry_stocks(self, industry: str) -> List[Dict]:
        """获取行业股票"""
        stocks = [s for s in self.stock_list if s["industry"] == industry]
        return [self.get_quote(s["code"]) for s in stocks]
    
    def get_market_summary(self) -> Dict:
        """获取市场概况"""
        return {
            "sh_index": {
                "code": "000001",
                "name": "上证指数",
                "price": round(3100 + random.uniform(-50, 50), 2),
                "change": round(random.uniform(-30, 30), 2),
                "change_percent": round(random.uniform(-1, 1), 2)
            },
            "sz_index": {
                "code": "399001",
                "name": "深证成指",
                "price": round(10000 + random.uniform(-100, 100), 2),
                "change": round(random.uniform(-80, 80), 2),
                "change_percent": round(random.uniform(-1, 1), 2)
            },
            "cy_index": {
                "code": "399006",
                "name": "创业板指",
                "price": round(2000 + random.uniform(-30, 30), 2),
                "change": round(random.uniform(-20, 20), 2),
                "change_percent": round(random.uniform(-1.5, 1.5), 2)
            },
            "market_value": round(85 + random.uniform(-2, 2), 2),  # 万亿
            "up_count": random.randint(1500, 2500),
            "down_count": random.randint(1500, 2500),
            "flat_count": random.randint(200, 500),
            "hot_industries": ["新能源", "半导体", "医药", "白酒", "银行"],
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# 全局市场服务实例
market_service = MarketService()