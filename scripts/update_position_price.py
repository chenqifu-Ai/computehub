#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动更新持仓价格
每日收盘后使用
"""

import json
from datetime import datetime
from pathlib import Path

# 持仓文件
POSITION_FILE = Path.home() / ".openclaw" / "workspace" / "positions.json"

def update_price(code, price, date=None):
    """更新股票价格"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # 读取持仓
    if POSITION_FILE.exists():
        with open(POSITION_FILE, 'r', encoding='utf-8') as f:
            positions = json.load(f)
    else:
        positions = {}
    
    # 更新价格
    if code not in positions:
        positions[code] = {
            "name": "",
            "volume": 0,
            "cost": 0,
            "history": []
        }
    
    positions[code]["history"].append({
        "date": date,
        "price": price
    })
    
    # 保存
    with open(POSITION_FILE, 'w', encoding='utf-8') as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已更新 {code} 价格：¥{price} ({date})")

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        code = sys.argv[1]
        price = float(sys.argv[2])
        date = sys.argv[3] if len(sys.argv) > 3 else None
        update_price(code, price, date)
    else:
        print("用法：python3 update_position_price.py <代码> <价格> [日期]")
        print("示例：python3 update_position_price.py 600460 25.85 2026-03-23")
