#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华联股份临界点监控 - 专门监控接近止损位的情况
"""

import time
import datetime

def monitor_hualian_critical():
    """监控华联股份临界状态"""
    
    stop_loss = 1.60
    critical_zone_upper = 1.65  # 临界区上限
    critical_zone_lower = 1.60  # 临界区下限
    
    print("🔴 华联股份临界点监控启动")
    print(f"⏰ 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 止损位: ¥{stop_loss}")
    print(f"🚨 临界区: ¥{critical_zone_lower}-{critical_zone_upper}")
    print("-" * 50)
    
    # 模拟实时价格监控（实际应该调用API）
    for i in range(10):  # 监控10个周期
        # 模拟价格波动
        import random
        current_price = round(random.uniform(1.58, 1.68), 2)
        
        # 分析状态
        if current_price <= stop_loss:
            status = "🔴 已跌破止损位"
            action = "立即执行70%减仓"
            urgency = "CRITICAL"
        elif current_price <= critical_zone_upper:
            status = "🟡 临界区监控"
            action = "准备减仓指令"
            urgency = "HIGH"
        else:
            status = "🟢 安全区"
            action = "持续监控"
            urgency = "NORMAL"
        
        distance = current_price - stop_loss
        distance_percent = (distance / stop_loss) * 100
        
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ")
        print(f"  价格: ¥{current_price} | 状态: {status}")
        print(f"  距离止损: {distance:+.3f} ({distance_percent:+.2f}%)")
        print(f"  紧急度: {urgency} | 建议: {action}")
        print("-" * 30)
        
        # 如果是临界或跌破状态，记录到紧急日志
        if urgency in ["HIGH", "CRITICAL"]:
            log_emergency(current_price, stop_loss, urgency, action)
        
        # 等待一段时间（实际监控中应该是实时或近实时）
        time.sleep(2)
    
    print("✅ 临界点监控完成")

def log_emergency(price, stop_loss, urgency, action):
    """记录紧急情况"""
    log_file = "/root/.openclaw/workspace/memory/hualian_critical_log.md"
    
    log_entry = f"""
## {urgency} - {datetime.datetime.now().strftime('%H:%M:%S')}
- 价格: ¥{price}
- 止损位: ¥{stop_loss}
- 距离: {price - stop_loss:+.3f}
- 建议操作: {action}
- 记录时间: {datetime.datetime.now().isoformat()}
"""
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    print(f"📝 紧急日志记录: {urgency}状态")

if __name__ == "__main__":
    monitor_hualian_critical()