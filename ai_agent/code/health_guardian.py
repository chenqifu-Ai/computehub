#!/usr/bin/env python3
"""
🔴 CEO进程保活守护脚本
自动检测和恢复关键服务
"""

import subprocess
import time
from datetime import datetime

def check_process(name, cmd_check, cmd_restart=None):
    """检查并恢复进程"""
    result = subprocess.run(cmd_check, shell=True, capture_output=True)
    if result.returncode != 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ {name} 未运行")
        if cmd_restart:
            print(f"  ⏳ 尝试重启...")
            subprocess.Popen(cmd_restart, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    return False

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 开始健康检查...")
    
    # 检查关键服务
    services = [
        ('OpenClaw', 'pgrep -f "openclaw" > /dev/null', 'openclaw gateway start'),
        ('Python任务', 'pgrep -f "python3.*ai_agent" > /dev/null', None),
    ]
    
    restarted = []
    for name, check, restart in services:
        if check_process(name, check, restart):
            restarted.append(name)
    
    if restarted:
        print(f"  ✅ 已重启服务: {', '.join(restarted)}")
    else:
        print(f"  ✅ 所有服务运行正常")

if __name__ == '__main__':
    main()
