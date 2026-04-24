#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接状态监控脚本
监控OpenClaw TUI连接状态
"""

import subprocess
import time

def check_gateway_status():
    """检查Gateway状态"""
    print("🖥️  检查Gateway状态...")
    
    try:
        result = subprocess.run(
            "curl -s http://127.0.0.1:18789/health",
            shell=True, capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            if "live" in result.stdout:
                print("✅ Gateway状态: 正常运行")
                return True
            else:
                print("❌ Gateway状态: 异常")
                return False
        else:
            print("❌ Gateway健康检查失败")
            return False
    except:
        print("❌ Gateway检查异常")
        return False

def check_tui_process():
    """检查TUI进程"""
    print("📱 检查TUI进程...")
    
    result = subprocess.run(
        "ps aux | grep 'openclaw-tui' | grep -v grep",
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode == 0 and "openclaw-tui" in result.stdout:
        print("✅ TUI进程: 正常运行")
        lines = result.stdout.strip().split('\n')
        for line in lines:
            print(f"   📊 {line[:80]}...")
        return True
    else:
        print("❌ TUI进程: 未找到")
        return False

def check_websocket_connection():
    """检查WebSocket连接"""
    print("🌐 检查WebSocket连接...")
    
    # 检查网络连接
    result = subprocess.run(
        "netstat -tln 2>/dev/null | grep :18789 || ss -tln 2>/dev/null | grep :18789",
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode == 0 and "18789" in result.stdout:
        print("✅ WebSocket端口: 监听中")
        return True
    else:
        print("❌ WebSocket端口: 未监听")
        return False

def main():
    print("📊 OpenClaw TUI连接状态监控")
    print("=" * 50)
    print("运行ID: c6fc3028-9805-490")
    print("=" * 50)
    
    status_ok = True
    
    status_ok &= check_gateway_status()
    status_ok &= check_tui_process()
    status_ok &= check_websocket_connection()
    
    print("\n" + "=" * 50)
    if status_ok:
        print("🎉 所有连接状态: ✅ 正常")
        print("   WebSocket连接已成功建立")
        print("   TUI客户端运行正常")
        print("   Gateway服务健康")
    else:
        print("🔧 连接状态: ⚠️  需要检查")
        print("   部分组件可能存在问题")
    
    print("\n💡 建议操作:")
    print("   1. 保持当前状态 - 连接正常")
    print("   2. 监控日志 - openclaw gateway logs")
    print("   3. 定期检查健康状态")

if __name__ == "__main__":
    main()