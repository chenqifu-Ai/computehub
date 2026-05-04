# 股票交易软件 - 配置文件

"""
应用配置
"""
import os

# 应用配置
APP_NAME = "股票交易系统"
APP_VERSION = "1.0.0"
DEBUG = True

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/stock_trading.db")

# JWT配置
SECRET_KEY = "stock-trading-secret-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# 服务器配置
HOST = "0.0.0.0"
PORT = 8000

# 数据源配置
DATASOURCE = "akshare"  # akshare / tushare / sinajs
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 风控配置
MAX_POSITION_RATIO = 0.8  # 最大仓位比例
STOP_LOSS_RATIO = 0.1     # 止损比例
STOP_PROFIT_RATIO = 0.3   # 止盈比例
MAX_SINGLE_TRADE_RATIO = 0.2  # 单笔最大交易比例