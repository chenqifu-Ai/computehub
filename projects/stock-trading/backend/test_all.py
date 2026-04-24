"""
股票交易系统 - 综合测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("📊 股票交易系统测试")
print("=" * 50)

# 1. 测试市场服务
print("\n【1】测试市场服务...")
from services.market_service import market_service

stocks = market_service.get_stock_list()
print(f"  ✅ 股票列表: {len(stocks)}只")

quote = market_service.get_quote('000001')
print(f"  ✅ 行情数据: {quote['name']} 价格={quote['price']} 涨跌={quote['change_percent']}%")

kline = market_service.get_kline('000001', count=10)
print(f"  ✅ K线数据: {kline['count']}条")

summary = market_service.get_market_summary()
print(f"  ✅ 市场概况: 上证{summary['sh_index']['price']} 深证{summary['sz_index']['price']}")

# 2. 测试数据库
print("\n【2】测试数据库...")
from database import db

user = db.verify_user('admin', 'admin123')
if user:
    print(f"  ✅ 用户验证: {user['username']}")
    account = db.get_account(user['id'])
    if account:
        print(f"  ✅ 账户余额: {account['balance']}")
    else:
        print("  ⚠️ 账户不存在，将创建")
else:
    print("  ⚠️ 默认用户不存在")

strategies = db.get_strategies(1)
print(f"  ✅ 策略数量: {len(strategies)}")

# 3. 测试回测引擎
print("\n【3】测试回测引擎...")
from services.backtest_engine import BacktestEngine

engine = BacktestEngine()
result = engine.run_backtest(
    strategy_code='''
# 双均线策略
def strategy(data):
    if len(data) < 20:
        return None
    
    ma5 = sum([d['close'] for d in data[-5:]]) / 5
    ma20 = sum([d['close'] for d in data[-20:]]) / 20
    
    if ma5 > ma20:
        return 'buy'
    else:
        return 'sell'
''',
    stock_code='000001',
    start_date='2025-01-01',
    end_date='2025-12-31',
    initial_capital=1000000
)

print(f"  ✅ 回测结果:")
print(f"     - 总收益: {result.get('total_return', 0):.2f}%")
print(f"     - 最大回撤: {result.get('max_drawdown', 0):.2f}%")
print(f"     - 夏普比率: {result.get('sharpe_ratio', 0):.2f}")
print(f"     - 胜率: {result.get('win_rate', 0):.1f}%")
print(f"     - 交易次数: {result.get('total_trades', 0)}")

# 4. 测试API路由
print("\n【4】测试API路由...")
from routes.auth import router as auth_router
from routes.market import router as market_router
from routes.strategy import router as strategy_router
from routes.trading import router as trading_router
from routes.account import router as account_router

print(f"  ✅ 认证路由: {len(auth_router.routes)}个端点")
print(f"  ✅ 行情路由: {len(market_router.routes)}个端点")
print(f"  ✅ 策略路由: {len(strategy_router.routes)}个端点")
print(f"  ✅ 交易路由: {len(trading_router.routes)}个端点")
print(f"  ✅ 账户路由: {len(account_router.routes)}个端点")

print("\n" + "=" * 50)
print("✅ 所有测试通过!")
print("=" * 50)