#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体任务：更新华联股份持仓数据
时间：2026-03-25 09:40:00
"""

import json
import re
from datetime import datetime
from pathlib import Path

def update_memory_md():
    """更新 MEMORY.md 中的持仓数据"""
    memory_path = "/root/.openclaw/workspace/MEMORY.md"
    
    with open(memory_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 当前持仓：华联股份 | 000882 | 22,600股 | ¥1.779 | ¥1.60 | ¥2.00
    # 更新为：华联股份 | 000882 | 17,600股 | ¥1.779 | ¥1.60 | ¥2.00
    
    pattern = r"(华联股份\s+\|\s+000882\s+\|\s+)22,600股(\s+\|\s+¥1\.779\s+\|\s+¥1\.60\s+\|\s+¥2\.00)"
    replacement = r"\117,600股\2"
    
    updated_content = re.sub(pattern, replacement, content)
    
    if content == updated_content:
        raise ValueError("未找到需要更新的持仓数据")
    
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    return {"memory_md_updated": True, "new_quantity": 17600}

def update_monitor_script():
    """更新监控脚本中的持仓数据"""
    monitor_path = "/root/.openclaw/workspace/scripts/monitor_position.py"
    
    with open(monitor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新持仓数量从22600到17600
    pattern = r'("volume":\s*)22600'
    replacement = r'\117600'
    
    updated_content = re.sub(pattern, replacement, content)
    
    if content == updated_content:
        raise ValueError("未找到需要更新的监控脚本数据")
    
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    return {"monitor_script_updated": True}

def main():
    try:
        print(f"🔧 执行持仓数据更新任务")
        print(f"⏰ 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 更新内容：华联股份从22,600股 → 17,600股（昨天已卖出5,000股）")
        
        # 更新 MEMORY.md
        memory_result = update_memory_md()
        print(f"✅ MEMORY.md 更新完成: {memory_result}")
        
        # 更新监控脚本
        monitor_result = update_monitor_script()
        print(f"✅ 监控脚本更新完成: {monitor_result}")
        
        result = {
            "status": "success",
            "message": "华联股份持仓数据更新完成",
            "data": {
                "previous_quantity": 22600,
                "current_quantity": 17600,
                "sold_yesterday": 5000,
                "files_updated": ["MEMORY.md", "monitor_position.py"]
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