#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票交易软件 - 完整测试脚本
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def check_and_install_dependencies():
    """检查并安装依赖"""
    print("\n📦 检查依赖...")
    
    # 核心依赖
    core_deps = ['fastapi', 'uvicorn', 'pydantic', 'jwt']
    missing_core = []
    
    for pkg in core_deps:
        try:
            if pkg == 'jwt':
                __import__('jwt')
            else:
                __import__(pkg)
            print(f"   ✅ {pkg}")
        except ImportError:
            print(f"   ❌ {pkg} (缺失)")
            missing_core.append(pkg)
    
    # 可选依赖
    optional_deps = ['pandas', 'akshare']
    for pkg in optional_deps:
        try:
            __import__(pkg)
            print(f"   ✅ {pkg} (可选)")
        except ImportError:
            print(f"   ⚠️ {pkg} (可选，未安装)")
    
    # 安装缺失的核心依赖
    if missing_core:
        print(f"\n正在安装缺失的依赖: {', '.join(missing_core)}")
        import subprocess
        try:
            for dep in missing_core:
                if dep == 'jwt':
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyJWT', '-q'])
                else:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep, '-q'])
            print("✅ 依赖安装完成")
            return True
        except Exception as e:
            print(f"❌ 依赖安装失败: {e}")
            print("\n请手动安装:")
            cmd = 'pip install ' + ' '.join(['PyJWT' if d == 'jwt' else d for d in missing_core])
            print(f"   {cmd}")
            return False
    
    return True


def test_database():
    """测试数据库"""
    print("\n📊 测试数据库...")
    try:
        from database import db
        
        # 测试股票
        stocks = db.get_stocks()
        print(f"   ✅ 股票列表: {len(stocks)}只")
        
        # 测试用户
        user = db.get_user('admin')
        if user:
            print(f"   ✅ 用户: admin (id={user['id']})")
        
        # 测试账户
        account = db.get_account(1)
        if account:
            print(f"   ✅ 资金: ¥{account['balance']:,.0f}")
        
        # 测试策略
        strategies = db.get_strategies(1)
        print(f"   ✅ 策略: {len(strategies)}个")
        
        return True
    except Exception as e:
        print(f"   ❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_service():
    """测试行情服务"""
    print("\n📈 测试行情服务...")
    try:
        from services import market_service
        
        # 测试股票列表
        stocks = market_service.get_stock_list()
        print(f"   ✅ 股票列表: {len(stocks)}只")
        
        # 测试实时行情（可能失败，因为网络）
        try:
            quote = market_service.get_quote('000001')
            print(f"   ✅ 实时行情: {quote.get('name', 'N/A')} ¥{quote.get('price', 0)}")
        except Exception as e:
            print(f"   ⚠️ 实时行情测试跳过 (网络原因)")
        
        return True
    except Exception as e:
        print(f"   ❌ 行情服务测试失败: {e}")
        return False


def test_backtest():
    """测试回测引擎"""
    print("\n🧪 测试回测引擎...")
    try:
        from services import backtest_engine
        
        # 使用模拟数据测试
        mock_klines = backtest_engine._generate_mock_kline(30)
        result = backtest_engine.run_backtest(
            strategy_func=None,  # 使用默认策略
            klines=mock_klines,
            strategy_name="双均线策略"
        )
        print(f"   ✅ 回测结果:")
        print(f"      总收益率: {result.total_return}%")
        print(f"      最大回撤: {result.max_drawdown}%")
        print(f"      夏普比率: {result.sharpe_ratio}")
        print(f"      交易次数: {result.total_trades}笔")
        
        return True
    except Exception as e:
        print(f"   ❌ 回测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api():
    """测试API路由"""
    print("\n🔌 测试API路由...")
    try:
        from routes import auth, market, strategy, trading, account
        print("   ✅ 路由模块导入成功")
        
        # 测试主应用
        from main import app
        print("   ✅ FastAPI应用创建成功")
        
        return True
    except Exception as e:
        print(f"   ❌ API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("="*50)
    print("  股票交易软件 - 功能测试")
    print("="*50)
    
    # 检查并安装依赖
    if not check_and_install_dependencies():
        print("\n⚠️ 部分依赖缺失，继续测试...")
    
    # 运行测试
    results = []
    results.append(("数据库", test_database()))
    results.append(("行情服务", test_market_service()))
    results.append(("回测引擎", test_backtest()))
    results.append(("API路由", test_api()))
    
    # 输出结果
    print("\n" + "="*50)
    print("  测试结果汇总")
    print("="*50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*50)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        print("\n🚀 启动服务:")
        print("   python main.py")
        print("\n📚 API文档:")
        print("   http://localhost:8000/docs")
        print("\n💻 前端页面:")
        print("   浏览器打开 frontend/index.html")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
        print("\n💡 建议:")
        print("   1. 确保安装了所有依赖: pip install fastapi uvicorn PyJWT requests")
        print("   2. 可选依赖pandas用于高级回测功能")
        print("   3. 程序会在缺少pandas时自动降级运行")


if __name__ == "__main__":
    main()