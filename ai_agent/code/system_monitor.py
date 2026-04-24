#!/usr/bin/env python3
"""
实时系统监控脚本 - 小智技能演示
"""

import psutil
import time
import os

def get_system_status():
    """获取系统状态信息"""
    # CPU负载
    try:
        load_avg = os.getloadavg()
    except AttributeError:
        # 在某些环境下可能不支持getloadavg
        load_avg = (0, 0, 0)
    
    # 内存使用
    mem = psutil.virtual_memory()
    
    # 磁盘使用
    disk = psutil.disk_usage('/')
    
    # 进程数量
    processes = len(psutil.pids())
    
    return {
        'load_avg': load_avg,
        'memory_used': mem.used / (1024**3),  # GB
        'memory_total': mem.total / (1024**3),  # GB
        'memory_percent': mem.percent,
        'disk_used': disk.used / (1024**3),  # GB
        'disk_total': disk.total / (1024**3),  # GB
        'disk_percent': disk.percent,
        'processes': processes
    }

def format_status(status):
    """格式化状态信息"""
    output = "🔍 实时系统监控报告\n"
    output += "=" * 50 + "\n"
    
    # 负载状态
    load_emoji = "🟢" if status['load_avg'][0] < 5 else "🟡" if status['load_avg'][0] < 15 else "🔴"
    output += f"{load_emoji} 系统负载: {status['load_avg'][0]:.1f}, {status['load_avg'][1]:.1f}, {status['load_avg'][2]:.1f}\n"
    
    # 内存状态
    mem_emoji = "🟢" if status['memory_percent'] < 70 else "🟡" if status['memory_percent'] < 85 else "🔴"
    output += f"{mem_emoji} 内存使用: {status['memory_used']:.1f}G/{status['memory_total']:.1f}G ({status['memory_percent']:.1f}%)\n"
    
    # 磁盘状态
    disk_emoji = "🟢" if status['disk_percent'] < 70 else "🟡" if status['disk_percent'] < 85 else "🔴"
    output += f"{disk_emoji} 磁盘使用: {status['disk_used']:.1f}G/{status['disk_total']:.1f}G ({status['disk_percent']:.1f}%)\n"
    
    # 进程数量
    output += f"📊 运行进程: {status['processes']} 个\n"
    
    # 建议
    output += "\n💡 优化建议:\n"
    if status['load_avg'][0] > 15:
        output += "  - 重启高负载服务\n"
    if status['memory_percent'] > 80:
        output += "  - 清理内存缓存\n"
    if status['disk_percent'] > 80:
        output += "  - 清理磁盘空间\n"
    
    return output

if __name__ == "__main__":
    print("🚀 小智系统监控技能演示")
    print("=" * 50)
    
    # 获取并显示系统状态
    status = get_system_status()
    report = format_status(status)
    print(report)
    
    print("✅ 监控脚本执行完成！")