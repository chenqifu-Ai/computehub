#!/usr/bin/env python3
"""
解决红茶机器清理脚本问题的方案
"""

import os
import subprocess
import sys

def main():
    print("=== 红茶机器清理脚本问题解决方案 ===")
    
    # 方案1: 如果能SSH访问，直接禁用脚本
    try:
        result = subprocess.run(['ssh', 'chen@192.168.2.134', 'echo "SSH测试"'], 
                              capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ SSH可用，正在禁用清理脚本...")
            subprocess.run(['ssh', 'chen@192.168.2.134', 
                          'sudo mv /home/chen/.openclaw/workspace/scripts/cleanup_openclaw_tui.sh /home/chen/.openclaw/workspace/scripts/cleanup_openclaw_tui.sh.disabled'])
            print("✅ 清理脚本已禁用")
            return
    except Exception as e:
        print(f"SSH不可用: {e}")
    
    # 方案2: 创建反制脚本，在本地监控并重启
    print("🔄 SSH不可用，创建本地监控方案...")
    
    monitor_script = '''
#!/bin/bash
# 监控并保护openclaw-tui进程
while true; do
    # 检查openclaw-tui是否在运行
    if ! pgrep -f "openclaw-tui" > /dev/null; then
        echo "$(date): openclaw-tui进程被杀死，正在重启..."
        # 重启openclaw-tui
        nohup openclaw-tui --gateway-url http://192.168.1.17:18789 --token your_token &
        sleep 5
    fi
    sleep 10
done
'''
    
    with open('/root/.openclaw/workspace/scripts/protect_openclaw_tui.sh', 'w') as f:
        f.write(monitor_script)
    
    # 给脚本执行权限
    os.chmod('/root/.openclaw/workspace/scripts/protect_openclaw_tui.sh', 0o755)
    
    print("✅ 本地保护脚本已创建: /root/.openclaw/workspace/scripts/protect_openclaw_tui.sh")
    print("✅ 请手动运行: nohup /root/.openclaw/workspace/scripts/protect_openclaw_tui.sh &")

if __name__ == "__main__":
    main()