#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试风控 API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def login():
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return res.json()["data"]["token"]

token = login()
headers = {"Authorization": f"Bearer {token}"}

print("=" * 50)
print("🧪 风控 API 测试")
print("=" * 50)

# 1. 获取风控配置
print("\n1. 获取风控配置...")
res = requests.get(f"{BASE_URL}/api/risk/config", headers=headers)
print(f"   状态码：{res.status_code}")
if res.status_code == 200:
    print(f"   ✅ {res.json()}")
else:
    print(f"   ❌ {res.text}")

# 2. 获取风控报告
print("\n2. 获取风控报告...")
res = requests.get(f"{BASE_URL}/api/risk/report", headers=headers)
print(f"   状态码：{res.status_code}")
if res.status_code == 200:
    data = res.json()["data"]
    print(f"   ✅ 持仓数：{data.get('total_positions', 0)}")
    print(f"   ✅ 总盈亏：¥{data.get('total_profit', 0):.2f}")
    print(f"   ✅ 警告数：{len(data.get('warnings', []))}")
else:
    print(f"   ❌ {res.text}")

# 3. 策略信号测试
print("\n3. 策略信号测试...")
res = requests.post(f"{BASE_URL}/api/strategy/signal", 
    headers=headers, 
    json={"stock_code": "000001"})
print(f"   状态码：{res.status_code}")
if res.status_code == 200:
    signals = res.json()["data"]
    print(f"   ✅ MA 信号：{signals.get('ma_cross', 'N/A')}")
    print(f"   ✅ RSI 信号：{signals.get('rsi', 'N/A')}")
    print(f"   ✅ MACD 信号：{signals.get('macd', 'N/A')}")
else:
    print(f"   ❌ {res.text}")

# 4. 策略列表
print("\n4. 策略列表...")
res = requests.get(f"{BASE_URL}/api/strategy/list", headers=headers)
print(f"   状态码：{res.status_code}")
if res.status_code == 200:
    strategies = res.json()["data"]["list"]
    print(f"   ✅ 策略数：{len(strategies)}")
else:
    print(f"   ❌ {res.text}")

print("\n" + "=" * 50)
print("✅ 测试完成")
print("=" * 50)
