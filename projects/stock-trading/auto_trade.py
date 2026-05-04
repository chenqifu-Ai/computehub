#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动交易脚本 - 结合策略 + 风控的自动化交易
"""

import requests
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
TOKEN = None

def login():
    """登录"""
    global TOKEN
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        TOKEN = res.json()["data"]["token"]
        print(f"✅ 登录成功")
        return True
    return False

def get_account():
    """获取账户"""
    res = requests.get(f"{BASE_URL}/api/broker/account", headers={"Authorization": f"Bearer {TOKEN}"})
    return res.json()["data"] if res.status_code == 200 else None

def get_positions():
    """获取持仓"""
    res = requests.get(f"{BASE_URL}/api/broker/positions", headers={"Authorization": f"Bearer {TOKEN}"})
    return res.json()["data"].get("list", []) if res.status_code == 200 else []

def buy(stock_code, volume, price=None):
    """买入"""
    data = {"stock_code": stock_code, "direction": "buy", "volume": volume}
    if price:
        data["price"] = price
    res = requests.post(f"{BASE_URL}/api/broker/order", 
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json=data)
    return res.json()

def sell(stock_code, volume, price=None):
    """卖出"""
    data = {"stock_code": stock_code, "direction": "sell", "volume": volume}
    if price:
        data["price"] = price
    res = requests.post(f"{BASE_URL}/api/broker/order", 
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json=data)
    return res.json()

def get_signal(stock_code):
    """获取策略信号（模拟）"""
    # 实际应该调用策略引擎
    import random
    signals = ["buy", "sell", "hold"]
    return random.choice(signals)

def main():
    """主循环"""
    print("🚀 自动交易启动...")
    
    if not login():
        print("❌ 登录失败")
        return
    
    print(f"💰 账户：{get_account()}")
    print(f"📊 持仓：{len(get_positions())} 只")
    
    # 监控的股票池
    watchlist = ["000001", "600519", "002594", "300750"]
    
    print(f"\n👀 监控股票：{watchlist}")
    print(f"⏰ 开始监控... (Ctrl+C 停止)\n")
    
    last_signals = {}
    
    try:
        while True:
            for code in watchlist:
                signal = get_signal(code)
                
                # 信号变化才执行
                if signal != last_signals.get(code):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {code} 信号：{signal}")
                    
                    if signal == "buy":
                        # 检查是否已持仓
                        positions = get_positions()
                        if not any(p["code"] == code for p in positions):
                            result = buy(code, 100)
                            print(f"  🟢 买入：{result}")
                    
                    elif signal == "sell":
                        # 检查是否有持仓
                        positions = get_positions()
                        pos = next((p for p in positions if p["code"] == code), None)
                        if pos:
                            result = sell(code, pos["volume"])
                            print(f"  🔴 卖出：{result}")
                
                last_signals[code] = signal
            
            # 每 60 秒检查一次
            time.sleep(60)
    
    except KeyboardInterrupt:
        print("\n⛔ 停止交易")

if __name__ == "__main__":
    main()
