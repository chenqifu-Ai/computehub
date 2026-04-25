#!/usr/bin/env python3
"""
代理日志实时监控 - 有数据就打印到控制台
"""

import time
import os
import sys

LOG_FILE = "/root/.openclaw/workspace/ai_agent/logs/lan_proxy_debug.log"

print("=" * 70)
print("🔍 代理日志实时监控中...")
print(f"📝 日志文件: {LOG_FILE}")
print(f"⏹ 按 Ctrl+C 停止")
print("=" * 70)

if not os.path.exists(LOG_FILE):
    print(f"❌ 日志文件不存在: {LOG_FILE}")
    sys.exit(1)

# 找到文件末尾位置
with open(LOG_FILE, 'r', encoding='utf-8') as f:
    f.seek(0, 2)  # 跳到文件末尾
    current_pos = f.tell()

print("\n" + "─" * 70)
print("开始监控...\n")

try:
    while True:
        # 检查文件是否存在
        if not os.path.exists(LOG_FILE):
            time.sleep(1)
            continue
        
        # 获取文件大小
        file_size = os.path.getsize(LOG_FILE)
        
        if file_size > current_pos:
            # 有新数据
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                f.seek(current_pos)
                new_data = f.read()
                current_pos = f.tell()
                
                # 按行输出新数据
                lines = new_data.split('\n')
                for line in lines:
                    if line.strip():
                        # 根据内容类型添加颜色提示
                        if '📥' in line or '【INCOMING' in line or '【REMOTE' in line:
                            print(f"🔴 {line}")  # 红色 - 接收
                        elif '📤' in line or '【OUTGOING' in line or '【CLIENT' in line:
                            print(f"🟢 {line}")  # 绿色 - 发送
                        elif '❌' in line or '【ERROR' in line:
                            print(f"🔴 {line}")  # 红色 - 错误
                        elif '📊' in line:
                            print(f"🟡 {line}")  # 黄色 - Token 用量
                        else:
                            print(line)
        
        time.sleep(0.5)  # 每 0.5 秒检查一次

except KeyboardInterrupt:
    print("\n\n" + "─" * 70)
    print("👋 监控已停止")
    print("─" * 70)
