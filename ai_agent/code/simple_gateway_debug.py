#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单Gateway调试脚本
设备已安装，只需要调试
"""

import subprocess
import time

def debug_gateway():
    """调试Gateway服务"""
    print("🔧 开始调试Gateway服务...")
    
    # 1. 检查设备在线状态
    print("1. 检查设备连接...")
    result = subprocess.run("ping -c 2 192.168.1.9", shell=True, capture_output=True)
    if result.returncode != 0:
        print("❌ 设备不在线")
        return False
    print("✅ 设备在线")
    
    # 2. 检查Gateway端口
    print("2. 检查Gateway端口(18789)...")
    try:
        result = subprocess.run(
            "timeout 3 bash -c 'echo > /dev/tcp/192.168.1.9/18789'", 
            shell=True, capture_output=True
        )
        if result.returncode == 0:
            print("✅ Gateway端口开放")
            return True
        else:
            print("❌ Gateway端口关闭")
    except:
        print("❌ Gateway端口检查失败")
    
    # 3. 简单调试建议
    print("\n💡 调试建议:")
    print("   - 在192.168.1.9设备上运行: openclaw gateway start")
    print("   - 检查防火墙设置")
    print("   - 确认端口18789未被占用")
    print("   - 查看日志: openclaw gateway logs")
    
    return False

def main():
    print("🚀 Gateway调试工具")
    print("=" * 30)
    
    if debug_gateway():
        print("\n🎉 Gateway服务正常!")
    else:
        print("\n🔧 需要手动调试:")
        print("   1. 连接到192.168.1.9设备")
        print("   2. 执行: openclaw gateway start")
        print("   3. 检查服务状态: openclaw gateway status")

if __name__ == "__main__":
    main()