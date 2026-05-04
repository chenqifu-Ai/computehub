"""
股票交易软件 - 启动脚本（简化版）
无需pandas也能运行
"""
import sys
import os

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(__file__))

print("="*50)
print("  股票交易软件 - 启动中...")
print("="*50)
print()

# 检查Python版本
print(f"📌 Python版本: {sys.version.split()[0]}")

# 检查核心依赖
print()
print("📦 检查依赖...")
dependencies = {
    'fastapi': 'FastAPI框架',
    'uvicorn': 'ASGI服务器',
    'jwt': 'JWT认证',
    'pydantic': '数据验证',
    'requests': 'HTTP请求'
}

missing = []
for pkg, desc in dependencies.items():
    try:
        if pkg == 'jwt':
            __import__('jwt')
        else:
            __import__(pkg)
        print(f"   ✅ {pkg} ({desc})")
    except ImportError:
        print(f"   ❌ {pkg} ({desc}) - 缺失")
        missing.append(pkg)

# 检查可选依赖
print()
print("📦 可选依赖...")
optional = {
    'pandas': '数据分析（回测引擎）',
    'akshare': 'A股数据源'
}
for pkg, desc in optional.items():
    try:
        __import__(pkg)
        print(f"   ✅ {pkg} ({desc})")
    except ImportError:
        print(f"   ⚠️ {pkg} ({desc}) - 缺失，使用备用方案")

if missing:
    print()
    print("❌ 缺少必要依赖，请安装:")
    print(f"   pip install {' '.join(missing)}")
    print()
    print("完整安装:")
    print("   pip install fastapi uvicorn pydantic PyJWT requests")
    sys.exit(1)

# 初始化数据库
print()
print("📊 初始化数据库...")
try:
    from database import db
    stocks = db.get_stocks()
    print(f"   ✅ 股票: {len(stocks)}只")
    
    user = db.get_user('admin')
    if user:
        print(f"   ✅ 用户: admin")
    
    account = db.get_account(1)
    if account:
        print(f"   ✅ 资金: ¥{account['balance']:,.0f}")
except Exception as e:
    print(f"   ❌ 数据库初始化失败: {e}")
    sys.exit(1)

# 启动服务器
print()
print("="*50)
print("  🚀 启动服务...")
print("="*50)
print()
print("  访问地址:")
print("  ─────────────────────────────────────")
print("  后端API:  http://localhost:8000")
print("  API文档:  http://localhost:8000/docs")
print("  前端页面: 浏览器打开 frontend/index.html")
print("  ─────────────────────────────────────")
print()
print("  默认账户:")
print("  ─────────────────────────────────────")
print("  用户名: admin")
print("  密码:   admin123")
print("  资金:   1,000,000元")
print("  ─────────────────────────────────────")
print()

# 导入并启动FastAPI
try:
    import uvicorn
    from main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
except Exception as e:
    print(f"❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)