#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控 192.168.2.165 Ollama 服务器模型下载
"""

import subprocess
import time
import sys
from datetime import datetime

SERVER = "192.168.2.165"
USER = "admin"
PASS = "admin"
MODEL = "ministral-3:14b"

def ssh_cmd(cmd):
    """执行 SSH 命令"""
    result = subprocess.run(
        ["sshpass", "-p", PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         f"{USER}@{SERVER}", cmd],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout

def format_size(bytes_val):
    return f"{bytes_val/1e9:.2f} GB"

def monitor():
    print("=" * 70)
    print(f"📥 Ollama 模型下载监控 - {SERVER}")
    print(f"   模型：{MODEL}")
    print("=" * 70)
    print()
    
    # 启动后台下载
    print("🚀 启动下载...")
    pull_cmd = f"powershell -Command \"Invoke-RestMethod -Uri 'http://localhost:11434/api/pull' -Method POST -Body '{{\\\"name\\\":\\\"{MODEL}\\\"}}' -ContentType 'application/json'\""
    
    subprocess.Popen(
        ["sshpass", "-p", PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         f"{USER}@{SERVER}", pull_cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("✅ 下载进程已启动")
    print()
    
    last_completed = 0
    last_time = time.time()
    
    # 监控进度
    for i in range(300):  # 最多监控 5 分钟
        time.sleep(5)
        
        # 获取标签
        tags_output = ssh_cmd("curl -s http://localhost:11434/api/tags")
        
        # 检查模型是否已存在
        if MODEL.split(":")[0] in tags_output:
            print("\n" + "=" * 70)
            print("✅ 下载完成!")
            print("=" * 70)
            print(f"\n📊 当前模型列表:")
            print(f"   • {MODEL}")
            return True
        
        # 尝试获取进度 (需要下载中的输出)
        # 这里简化处理，只显示时间
        
        elapsed = int(time.time() - last_time)
        mins = elapsed // 60
        secs = elapsed % 60
        print(f"\r⏳ 下载中... 已运行 {mins:02d}:{secs:02d}", end="", flush=True)
    
    print("\n\n⚠️ 监控超时，请手动检查")
    return False

if __name__ == '__main__':
    success = monitor()
    sys.exit(0 if success else 1)
