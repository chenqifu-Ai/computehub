#!/usr/bin/env python3
"""
更强力的openclaw-tui进程保护
"""

import time
import subprocess
import os
import sys

def check_and_restart():
    """检查并重启openclaw-tui进程"""
    try:
        # 检查进程数量
        result = subprocess.run(['pgrep', '-f', 'openclaw-tui'], 
                              capture_output=True, text=True)
        process_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 当前openclaw-tui进程数: {process_count}")
        
        # 如果进程数少于1个，重启
        if process_count < 1:
            print("⚠️ 进程被杀死，立即重启...")
            # 杀死所有残留进程
            subprocess.run(['pkill', '-f', 'openclaw-tui'], capture_output=True)
            time.sleep(2)
            # 重启多个实例确保稳定性
            for i in range(3):
                subprocess.Popen(['nohup', 'openclaw-tui', '--gateway-url', 'http://192.168.1.17:18789', 
                                '--token', '2159c9affb69a78acdef02bc0e0c68824bedcc8ccf11bc5b', '&'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ 已重启3个openclaw-tui进程")
            
    except Exception as e:
        print(f"❌ 保护进程出错: {e}")

def main():
    print("=== 强力保护模式启动 ===")
    print("每5秒检查一次openclaw-tui进程状态")
    
    while True:
        check_and_restart()
        time.sleep(5)  # 每5秒检查一次，比清理脚本更快

if __name__ == "__main__":
    main()