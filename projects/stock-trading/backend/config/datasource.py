# 数据源配置
"""
股票行情数据源配置
支持多种数据源，可根据需要切换
"""

class DataSource:
    """数据源配置"""
    
    # Tushare配置（需要token）
    TUSHARE_TOKEN = None  # 在此填入你的token
    
    # 数据源选择
    PRIMARY_SOURCE = "akshare"  # 主数据源: akshare / tushare / sinajs
    
    # AKShare（免费，无需token）
    @staticmethod
    def get_akshare_config():
        return {
            "name": "akshare",
            "type": "free",
            "need_token": False,
            "rate_limit": "无限制",
            "features": ["实时行情", "历史K线", "财务数据"]
        }
    
    # Tushare（需要token）
    @staticmethod
    def get_tushare_config():
        return {
            "name": "tushare",
            "type": "free_with_token",
            "need_token": True,
            "rate_limit": "每分钟200次",
            "features": ["实时行情", "历史K线", "财务数据", "指数数据"]
        }
    
    # 新浪财经（免费）
    @staticmethod
    def get_sina_config():
        return {
            "name": "sinajs",
            "type": "free",
            "need_token": False,
            "rate_limit": "建议控制频率",
            "features": ["实时行情"]
        }


# 数据源实例配置
DATASOURCE_CONFIG = {
    "akshare": {
        "module": "akshare",
        "realtime_quote": "stock_zh_a_spot_em",
        "history_kline": "stock_zh_a_hist",
        "stock_list": "stock_info_a_code_name"
    },
    "tushare": {
        "module": "tushare",
        "realtime_quote": "realtime_quote",
        "history_kline": "pro_bar",
        "stock_list": "stock_basic"
    },
    "sinajs": {
        "module": "requests",
        "realtime_quote": "http://hq.sinajs.cn/list={code}",
        "history_kline": None,
        "stock_list": None
    }
}