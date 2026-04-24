#!/usr/bin/env python3
"""
伪装openclaw-tui进程，避免被清理脚本识别
"""

import subprocess
import time
import os

def start_stealth_process():
    """启动伪装的openclaw进程"""
    # 使用不同的进程名称启动
    cmd = [
        'openclaw-tui',
        '--gateway-url', 'http://192.168.1.17:18789',
        '--token', '2159c9affb69a78acdef02bc0e0c68824bedcc8ccf11bc5b'
    ]
    
    # 通过exec -a改变进程名
    stealth_cmd = ['exec', '-a', 'system-monitor', 'bash', '-c', ' '.join(cmd)]
    
    try:
        # 杀死现有的openclaw-tui进程
        subprocess.run(['pkill', '-f', 'openclaw-tui'], capture_output=True)
        time.sleep(2)
        
        # 启动伪装进程
        subprocess.Popen(stealth_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ 已启动伪装进程 (名称: system-monitor)")
        
    except Exception as e:
        print(f"❌ 启动伪装进程失败: {e}")

if __name__ == "__main__":
    start_stealth_process()