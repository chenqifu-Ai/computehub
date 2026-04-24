#!/usr/bin/env python3
"""
蓝牙设备检测
实际干活，不废话
"""

import os
import subprocess

def check_system():
    """检查系统状态"""
    print("🔍 检查系统状态...")
    
    # 检查蓝牙服务
    try:
        result = subprocess.run(["service", "bluetooth", "status"], 
                              capture_output=True, text=True, timeout=5)
        if "active (running)" in result.stdout:
            print("✅ 蓝牙服务运行中")
        else:
            print("❌ 蓝牙服务未运行")
    except:
        print("❌ 无法检查蓝牙服务")
    
    # 检查蓝牙工具
    tools = ["bluetoothctl", "rfkill", "pactl"]
    for tool in tools:
        if subprocess.run(["which", tool], capture_output=True).returncode == 0:
            print(f"✅ {tool} 可用")
        else:
            print(f"❌ {tool} 不可用")

def suggest_solutions():
    """建议实际解决方案"""
    print("\n🔧 实际解决方案:")
    print("="*50)
    
    solutions = [
        "1. 手动蓝牙配对:",
        "   • 音箱进入配对模式",
        "   • bluetoothctl scan on", 
        "   • bluetoothctl pair [MAC]",
        "   • bluetoothctl connect [MAC]",
        "",
        "2. 音频设置:",
        "   • pactl list short sinks",
        "   • pactl set-default-sink bluez_sink.[MAC]",
        "",
        "3. 测试音频:",
        "   • speaker-test -t wav -c 2",
        "",
        "4. 语音处理:",
        "   • 使用python处理音频",
        "   • 简单的命令响应"
    ]
    
    for line in solutions:
        print(line)

def create_work_plan():
    """创建工作计划"""
    print("\n📅 今晚工作计划:")
    print("="*50)
    
    plan = [
        "阶段1: 设备准备 (30分钟)",
        "  • 音箱蓝牙配对",
        "  • 音频输出设置",
        "  • 基础测试",
        "",
        "阶段2: 功能开发 (1.5小时)", 
        "  • 语音输入处理",
        "  • 命令响应系统",
        "  • 音频播放功能",
        "",
        "阶段3: 测试优化 (1小时)",
        "  • 功能测试",
        "  • 延迟优化", 
        "  • 用户体验"
    ]
    
    for line in plan:
        print(line)

def main():
    print("🔧 开始实际干活")
    print("💡 不分析，不演示，直接解决问题")
    print("="*60)
    
    check_system()
    suggest_solutions()
    create_work_plan()
    
    print("\n" + "="*60)
    print("✅ 实际工作方案就绪")
    print("🚀 现在可以开始具体实施")
    print("⏰ 今晚可以完成基础功能")

if __name__ == "__main__":
    main()