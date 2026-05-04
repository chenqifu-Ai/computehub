#!/usr/bin/env python3
"""
综合进程监控脚本 - 检查安全威胁和性能问题
"""

import subprocess
import psutil
import time
from datetime import datetime

def get_process_info():
    """获取详细的进程信息"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', 'cmdline']):
        try:
            proc_info = proc.info
            # 计算运行时间
            create_time = proc_info['create_time']
            if create_time:
                run_time = time.time() - create_time
                run_hours = run_time / 3600
            else:
                run_hours = 0
            
            processes.append({
                'pid': proc_info['pid'],
                'name': proc_info['name'],
                'username': proc_info['username'],
                'cpu_percent': proc_info['cpu_percent'],
                'memory_percent': proc_info['memory_percent'],
                'run_hours': run_hours,
                'cmdline': ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else '',
                'create_time': create_time
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def check_security_threats(processes):
    """检查安全威胁"""
    suspicious_patterns = [
        "miner", "backdoor", "reverse_shell", "keylogger",
        "crypto", "ransom", "botnet", "trojan", "worm",
        "rootkit", "spyware", "adware", "malware",
        "hidden", "stealth", "obfuscated", "packed"
    ]
    
    normal_users = ["root", "u0_a355", "u0_a207", "u0_a46"]
    
    threats = []
    for proc in processes:
        alerts = []
        
        # 检查可疑模式
        for pattern in suspicious_patterns:
            if pattern in proc['cmdline'].lower():
                alerts.append(f"包含{pattern}")
        
        # 检查异常用户
        if proc['username'] not in normal_users and not proc['username'].isdigit():
            alerts.append(f"异常用户:{proc['username']}")
        
        if alerts:
            threats.append({
                'proc': proc,
                'alerts': alerts
            })
    
    return threats

def check_performance_issues(processes):
    """检查性能问题"""
    performance_issues = []
    
    for proc in processes:
        alerts = []
        
        # 高CPU使用率
        if proc['cpu_percent'] > 10.0:  # 超过10% CPU
            alerts.append(f"高CPU使用:{proc['cpu_percent']:.1f}%")
        
        # 长时间运行的高CPU进程
        if proc['cpu_percent'] > 5.0 and proc['run_hours'] > 24:  # 超过24小时且>5% CPU
            alerts.append(f"长时间高CPU:{proc['run_hours']:.1f}小时")
        
        # 高内存使用率
        if proc['memory_percent'] > 5.0:  # 超过5%内存
            alerts.append(f"高内存使用:{proc['memory_percent']:.1f}%")
        
        if alerts:
            performance_issues.append({
                'proc': proc,
                'alerts': alerts
            })
    
    return performance_issues

def main():
    print("🔍 综合进程监控系统")
    print("📊 检查时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("-" * 60)
    
    # 获取进程信息
    processes = get_process_info()
    
    # 检查安全威胁
    security_threats = check_security_threats(processes)
    
    # 检查性能问题
    performance_issues = check_performance_issues(processes)
    
    # 输出安全威胁
    if security_threats:
        print("\n🔴 安全威胁检测:")
        for threat in security_threats:
            proc = threat['proc']
            print(f"   PID: {proc['pid']}")
            print(f"   用户: {proc['username']}")
            print(f"   进程: {proc['name']}")
            print(f"   警报: {' | '.join(threat['alerts'])}")
            print(f"   命令行: {proc['cmdline'][:80]}...")
            print("   ---")
    else:
        print("\n✅ 未发现安全威胁")
    
    # 输出性能问题
    if performance_issues:
        print("\n⚠️  性能问题检测:")
        for issue in performance_issues:
            proc = issue['proc']
            print(f"   PID: {proc['pid']}")
            print(f"   用户: {proc['username']}")
            print(f"   进程: {proc['name']}")
            print(f"   CPU: {proc['cpu_percent']:.1f}%")
            print(f"   内存: {proc['memory_percent']:.1f}%")
            print(f"   运行时间: {proc['run_hours']:.1f}小时")
            print(f"   警报: {' | '.join(issue['alerts'])}")
            print(f"   命令行: {proc['cmdline'][:80]}...")
            print("   ---")
    else:
        print("\n✅ 未发现性能问题")
    
    # 系统负载信息
    try:
        import os
        load_avg = os.getloadavg()
        print(f"\n📊 系统负载: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")
    except:
        print("\n📊 系统负载: 无法获取")
    
    cpu_count = psutil.cpu_count()
    print(f"📊 CPU核心数: {cpu_count}")
    print(f"📊 总进程数: {len(processes)}")
    
    print("\n" + "-" * 60)
    print("🕐 检查完成:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()