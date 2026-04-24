#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体任务：记录华联股份今日卖出操作
时间：2026-03-25 09:43:00
"""

import json
import re
from datetime import datetime
from pathlib import Path

def update_memory_md_final():
    """更新 MEMORY.md 中的最终持仓数据"""
    memory_path = "/root/.openclaw/workspace/MEMORY.md"
    
    with open(memory_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 当前持仓：华联股份 | 000882 | 17,600股 | ¥1.779 | ¥1.60 | ¥2.00
    # 更新为：华联股份 | 000882 | 13,500股 | ¥1.779 | ¥1.60 | ¥2.00
    
    pattern = r"(华联股份\s+\|\s+000882\s+\|\s+)17,600股(\s+\|\s+¥1\.779\s+\|\s+¥1\.60\s+\|\s+¥2\.00)"
    replacement = r"\113,500股\2"
    
    updated_content = re.sub(pattern, replacement, content)
    
    if content == updated_content:
        raise ValueError("未找到需要更新的持仓数据")
    
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    return {"memory_md_updated": True, "final_quantity": 13500}

def update_monitor_script_final():
    """更新监控脚本中的最终持仓数据"""
    monitor_path = "/root/.openclaw/workspace/scripts/monitor_position.py"
    
    with open(monitor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新持仓数量从17600到13500
    pattern = r'("volume":\s*)17600'
    replacement = r'\113500'
    
    updated_content = re.sub(pattern, replacement, content)
    
    if content == updated_content:
        raise ValueError("未找到需要更新的监控脚本数据")
    
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    return {"monitor_script_updated": True}

def create_trade_record():
    """创建交易记录文件"""
    trade_record = {
        "date": "2026-03-25",
        "stock": "华联股份",
        "code": "000882",
        "action": "卖出",
        "quantity": 4100,
        "price": 1.67,
        "cost_price": 1.779,
        "profit_loss": round(4100 * (1.67 - 1.779), 2),
        "remaining_shares": 13500,
        "timestamp": datetime.now().isoformat()
    }
    
    record_path = "/root/.openclaw/workspace/memory/trade_record_2026-03-25.json"
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(trade_record, f, ensure_ascii=False, indent=2)
    
    return {"trade_record_created": True, "record_path": record_path}

def main():
    try:
        print(f"📊 记录华联股份卖出交易")
        print(f"⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 交易详情：卖出4,100股 @ ¥1.67")
        print(f"💰 成本价：¥1.779 | 亏损：¥{4100 * (1.779 - 1.67):.2f}")
        print(f"📊 剩余持仓：13,500股")
        
        # 更新 MEMORY.md
        memory_result = update_memory_md_final()
        print(f"✅ MEMORY.md 更新完成: {memory_result}")
        
        # 更新监控脚本
        monitor_result = update_monitor_script_final()
        print(f"✅ 监控脚本更新完成: {monitor_result}")
        
        # 创建交易记录
        trade_result = create_trade_record()
        print(f"✅ 交易记录创建完成: {trade_result}")
        
        result = {
            "status": "success",
            "message": "华联股份卖出交易记录完成",
            "data": {
                "sold_quantity": 4100,
                "sold_price": 1.67,
                "cost_price": 1.779,
                "loss_amount": round(4100 * (1.67 - 1.779), 2),
                "final_quantity": 13500,
                "files_updated": ["MEMORY.md", "monitor_position.py", "trade_record_2026-03-25.json"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ 最终结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
        
    except Exception as e:
        error_result = {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ 错误：{json.dumps(error_result, ensure_ascii=False, indent=2)}")
        return error_result

if __name__ == "__main__":
    import traceback
    main()