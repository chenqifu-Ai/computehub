#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全 API 测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api(name, url, method='GET', json_data=None, headers=None):
    """测试单个 API"""
    try:
        if method == 'GET':
            res = requests.get(url, headers=headers, timeout=5)
        else:
            res = requests.post(url, json=json_data, headers=headers, timeout=5)
        
        status = "✅" if res.status_code == 200 else "❌"
        print(f"{status} {name}: {res.status_code}")
        return res.status_code == 200
    except Exception as e:
        print(f"❌ {name}: {str(e)[:50]}")
        return False

print("=" * 60)
print("🧪 股票交易系统 - 全 API 测试")
print("=" * 60)

# 登录获取 token
print("\n📝 登录...")
login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
if login_res.status_code == 200:
    token = login_res.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Token: {token[:16]}...")
else:
    print("❌ 登录失败")
    exit(1)

# 测试列表
tests = [
    # 行情 API
    ("行情列表", f"{BASE_URL}/api/market/stocks"),
    ("贵州茅台行情", f"{BASE_URL}/api/market/quote?code=600519"),
    ("K 线数据", f"{BASE_URL}/api/market/kline?code=000001&type=day&count=30"),
    
    # 账户 API
    ("账户信息", f"{BASE_URL}/api/broker/account", headers),
    ("持仓列表", f"{BASE_URL}/api/broker/positions", headers),
    ("订单列表", f"{BASE_URL}/api/broker/orders", headers),
    
    # 券商 API
    ("券商列表", f"{BASE_URL}/api/broker/list"),
    ("当前券商", f"{BASE_URL}/api/broker/current"),
    
    # 风控 API
    ("风控配置", f"{BASE_URL}/api/risk/config", headers),
    # ("风控报告", f"{BASE_URL}/api/risk/report", headers),
    
    # 策略 API
    ("策略列表", f"{BASE_URL}/api/strategy/list", headers),
    ("策略信号", f"{BASE_URL}/api/strategy/signal", 'POST', {"stock_code": "000001"}, headers),
]

print("\n📊 开始测试...")
print("-" * 60)

passed = 0
failed = 0

for test in tests:
    name = test[0]
    url = test[1]
    method = test[2] if len(test) > 2 else 'GET'
    json_data = test[3] if len(test) > 3 else None
    headers = test[4] if len(test) > 4 else None
    
    if test_api(name, url, method, json_data, headers):
        passed += 1
    else:
        failed += 1

print("-" * 60)
print(f"\n✅ 通过：{passed}/{passed+failed}")
print(f"❌ 失败：{failed}/{passed+failed}")
print(f"📊 通过率：{passed/(passed+failed)*100:.1f}%")

if passed == len(tests):
    print("\n🎉 全部通过！")
else:
    print(f"\n⚠️  有 {failed} 个 API 需要检查")
