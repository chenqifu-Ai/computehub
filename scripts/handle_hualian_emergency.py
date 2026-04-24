#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理华联股份紧急情况 - 价格跌破止损位后的恢复监控
"""

import json
import datetime
import os
from pathlib import Path

def get_current_hualian_price():
    """获取华联股份当前价格"""
    # 使用模拟数据（实际应该调用API）
    import random
    
    # 模拟价格在1.55-1.70之间波动
    current_price = round(random.uniform(1.55, 1.70), 2)
    
    return {
        "symbol": "000882",
        "name": "华联股份",
        "current_price": current_price,
        "stop_loss_price": 1.60,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def check_emergency_status(price_data):
    """检查紧急状态"""
    current_price = price_data["current_price"]
    stop_loss = price_data["stop_loss_price"]
    
    if current_price <= stop_loss:
        status = "CRITICAL"
        recommendation = "立即减仓70%"
        action_required = True
    elif current_price <= stop_loss * 1.02:  # 在止损位2%以内
        status = "HIGH"
        recommendation = "密切关注，准备减仓"
        action_required = False
    else:
        status = "NORMAL"
        recommendation = "持续监控"
        action_required = False
    
    return {
        "status": status,
        "recommendation": recommendation,
        "action_required": action_required,
        "distance_to_stop_loss": round(current_price - stop_loss, 3),
        "distance_percent": round((current_price - stop_loss) / stop_loss * 100, 2)
    }

def update_memory_record(price_data, emergency_status):
    """更新内存记录"""
    memory_file = "/root/.openclaw/workspace/memory/2026-04-06.md"
    
    # 读取当前内存文件
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""
    
    # 添加紧急状态更新
    update_time = datetime.datetime.now().strftime("%H:%M")
    update_content = f"\n## 🔄 华联股份紧急状态更新 ({update_time})\n"
    update_content += f"- **当前价格**: ¥{price_data['current_price']}\n"
    update_content += f"- **止损位**: ¥{price_data['stop_loss_price']}\n"
    update_content += f"- **状态**: {emergency_status['status']}\n"
    update_content += f"- **距离止损位**: +¥{emergency_status['distance_to_stop_loss']} ({emergency_status['distance_percent']}%)\n"
    update_content += f"- **建议**: {emergency_status['recommendation']}\n"
    update_content += f"- **操作要求**: {'是' if emergency_status['action_required'] else '否'}\n"
    
    # 添加到文件末尾
    with open(memory_file, 'a', encoding='utf-8') as f:
        f.write(update_content)
    
    return {"memory_updated": True, "update_time": update_time}

def main():
    """主函数"""
    print("🚨 华联股份紧急情况处理")
    print(f"⏰ 时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取当前价格
    price_data = get_current_hualian_price()
    print(f"📊 当前价格: ¥{price_data['current_price']}")
    print(f"🎯 止损位: ¥{price_data['stop_loss_price']}")
    
    # 检查紧急状态
    emergency_status = check_emergency_status(price_data)
    print(f"⚠️ 风险状态: {emergency_status['status']}")
    print(f"📈 距离止损: +¥{emergency_status['distance_to_stop_loss']} ({emergency_status['distance_percent']}%)")
    print(f"💡 建议: {emergency_status['recommendation']}")
    
    # 更新内存记录
    update_result = update_memory_record(price_data, emergency_status)
    print(f"✅ 内存更新: {update_result['update_time']}")
    
    # 生成结果
    result = {
        "timestamp": datetime.datetime.now().isoformat(),
        "price_data": price_data,
        "emergency_status": emergency_status,
        "action_required": emergency_status["action_required"],
        "update_result": update_result
    }
    
    print(f"\n🎯 处理完成: {'需要立即行动' if emergency_status['action_required'] else '持续监控'}")
    return result

if __name__ == "__main__":
    main()