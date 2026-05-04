#!/usr/bin/env python3
"""
快速进程检查脚本
立即检查当前异常进程
"""

import psutil
import json
from datetime import datetime

def quick_check():
    """快速检查异常进程"""
    print("🔍 快速进程安全检查...")
    print("-" * 50)
    
    suspicious_count = 0
    known_processes = {
        'systemd', 'init', 'kthreadd', 'sshd', 'bash', 'python', 'node',
        'java', 'nginx', 'apache', 'mysql', 'redis', 'docker', 'containerd',
        'openclaw', 'adb', 'curl', 'wget', 'ssh', 'scp', 'top', 'htop', 'ps'
    }
    
    suspicious_patterns = [
        'miner', 'backdoor', 'reverse_shell', 'keylogger', 'crypto',
        'ransom', 'botnet', 'trojan', 'worm', 'rootkit', 'spyware'
    ]
    
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
        try:
            info = proc.info
            name = info['name'].lower() if info['name'] else ''
            cmdline = ' '.join(info['cmdline'] or []).lower()
            username = info['username']
            
            # 检查可疑性
            is_suspicious = False
            alerts = []
            
            # 未知进程
            if name not in known_processes and not any(k in name for k in known_processes):
                is_suspicious = True
                alerts.append("未知进程")
            
            # 可疑模式
            for pattern in suspicious_patterns:
                if pattern in name or pattern in cmdline:
                    is_suspicious = True
                    alerts.append(f"包含'{pattern}'")
            
            # 异常用户
            if username not in ['root', 'u0_a355', 'u0_a207', 'u0_a46'] and not username.startswith('u0_a'):
                is_suspicious = True
                alerts.append(f"异常用户:{username}")
            
            if is_suspicious:
                suspicious_count += 1
                print(f"\n⚠️  PID {info['pid']}: {name} ({username})")
                print(f"   警报: {', '.join(alerts)}")
                if cmdline:
                    print(f"   命令行: {cmdline[:100]}...")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print("-" * 50)
    if suspicious_count == 0:
        print("✅ 系统干净，未发现可疑进程")
    else:
        print(f"🔴 发现 {suspicious_count} 个可疑进程!")
    
    return suspicious_count

if __name__ == "__main__":
    quick_check()