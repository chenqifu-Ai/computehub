#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘交易测试脚本
用于测试券商接口和实盘交易功能
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """登录获取 token"""
    print("📝 正在登录...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data["data"]["token"]
        print(f"✅ 登录成功！Token: {token[:16]}...")
        return token
    else:
        print(f"❌ 登录失败：{response.text}")
        return None

def get_account(token):
    """查询账户信息"""
    print("\n📊 查询账户信息...")
    response = requests.get(f"{BASE_URL}/api/broker/account", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 账户信息:")
        print(f"   总资产：¥{data['data'].get('total_assets', 0):,.2f}")
        print(f"   可用资金：¥{data['data'].get('available_cash', 0):,.2f}")
        print(f"   持仓市值：¥{data['data'].get('position_value', 0):,.2f}")
        return data["data"]
    else:
        print(f"❌ 查询失败：{response.text}")
        return None

def get_positions(token):
    """查询持仓"""
    print("\n📈 查询持仓...")
    response = requests.get(f"{BASE_URL}/api/broker/positions", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if response.status_code == 200:
        data = response.json()
        positions = data["data"].get("positions", [])
        if positions:
            print(f"✅ 持仓数量：{len(positions)}")
            for pos in positions:
                print(f"   - {pos['stock_code']} {pos['stock_name']}: {pos['volume']}股，成本¥{pos['cost_price']:.2f}")
        else:
            print("✅ 当前无持仓")
        return positions
    else:
        print(f"❌ 查询失败：{response.text}")
        return []

def buy_stock(token, stock_code, volume, price=None):
    """买入股票"""
    print(f"\n🟢 买入测试：{stock_code} x {volume}股")
    
    # 获取实时价格（如果没有指定）
    if not price:
        response = requests.get(f"{BASE_URL}/api/market/quote", params={"code": stock_code})
        if response.status_code == 200:
            price = response.json()["data"]["price"]
            print(f"   当前价格：¥{price:.2f}")
    
    response = requests.post(f"{BASE_URL}/api/broker/order", 
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "stock_code": stock_code,
            "direction": "buy",
            "volume": volume,
            "price": price
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 买入成功！订单号：{data['data'].get('order_id', 'N/A')}")
        return data["data"]
    else:
        print(f"❌ 买入失败：{response.text}")
        return None

def sell_stock(token, stock_code, volume, price=None):
    """卖出股票"""
    print(f"\n🔴 卖出测试：{stock_code} x {volume}股")
    
    response = requests.post(f"{BASE_URL}/api/broker/order", 
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "stock_code": stock_code,
            "direction": "sell",
            "volume": volume,
            "price": price
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 卖出成功！订单号：{data['data'].get('order_id', 'N/A')}")
        return data["data"]
    else:
        print(f"❌ 卖出失败：{response.text}")
        return None

def get_orders(token):
    """查询订单"""
    print("\n📋 查询订单...")
    response = requests.get(f"{BASE_URL}/api/broker/orders", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if response.status_code == 200:
        data = response.json()
        orders = data["data"].get("orders", [])
        if orders:
            print(f"✅ 订单数量：{len(orders)}")
            for order in orders[:5]:  # 显示最近 5 笔
                print(f"   - {order['stock_code']} {order['direction']} {order['volume']}股 @ ¥{order['price']:.2f} [{order['status']}]")
        else:
            print("✅ 无订单记录")
        return orders
    else:
        print(f"❌ 查询失败：{response.text}")
        return []

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 股票交易系统 - 实盘测试脚本")
    print("=" * 60)
    
    # 登录
    token = login()
    if not token:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("📊 账户状态检查")
    print("=" * 60)
    
    # 查询账户
    account = get_account(token)
    if not account:
        print("⚠️  无法获取账户信息，继续测试...")
    
    # 查询持仓
    positions = get_positions(token)
    
    print("\n" + "=" * 60)
    print("🧪 交易测试")
    print("=" * 60)
    
    # 测试买入（100 股）
    print("\n⚠️  注意：以下是真实交易，请确认是否继续！")
    confirm = 'y'  # ("是否继续测试？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 已取消测试")
        sys.exit(0)
    
    # 测试股票：平安银行 (000001)
    stock_code = "000001"
    test_volume = 100
    
    buy_result = buy_stock(token, stock_code, test_volume)
    
    if buy_result:
        print("\n✅ 买入测试成功！")
        
        # 查询持仓确认
        print("\n等待 3 秒后查询持仓...")
        import time
        time.sleep(3)
        get_positions(token)
        
        # 测试卖出（可选）
        confirm_sell = "n"  # 非交互模式默认不卖出
        # confirm_sell = input("\n是否卖出平仓？(y/n): ")
        if confirm_sell.lower() == 'y':
            sell_result = sell_stock(token, stock_code, test_volume)
            if sell_result:
                print("\n✅ 卖出测试成功！")
    
    print("\n" + "=" * 60)
    print("📋 订单记录")
    print("=" * 60)
    get_orders(token)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
