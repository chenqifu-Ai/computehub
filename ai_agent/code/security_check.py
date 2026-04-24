#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全配置检查脚本
解决webhook被阻止的问题
"""

import subprocess
import json
import os

def check_security_settings():
    """检查安全设置"""
    print("🔒 检查安全配置...")
    
    # 检查配置文件位置
    config_paths = [
        "/root/.openclaw/config.json",
        "/root/.openclaw/workspace/config.json",
        "/data/data/com.termux/files/usr/etc/openclaw/config.json"
    ]
    
    config_found = False
    for path in config_paths:
        if os.path.exists(path):
            print(f"✅ 找到配置文件: {path}")
            config_found = True
            
            # 尝试读取配置
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    if 'security' in config:
                        print(f"  安全设置: {config['security']}")
                    else:
                        print("  使用默认安全设置")
            except:
                print("  无法读取配置文件")
            break
    
    if not config_found:
        print("❌ 未找到配置文件，使用默认设置")
    
    return config_found

def check_webhook_access():
    """检查webhook访问"""
    print("\n🌐 检查webhook访问...")
    
    # 测试localhost访问
    tests = [
        ("http://localhost:18789/health", "健康检查"),
        ("http://127.0.0.1:18789/health", "127.0.0.1健康检查"),
        ("http://0.0.0.0:18789/health", "0.0.0.0健康检查")
    ]
    
    for url, desc in tests:
        try:
            result = subprocess.run(
                f"curl -s {url}", 
                shell=True, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"✅ {desc}: 成功")
                print(f"   响应: {result.stdout[:100]}...")
            else:
                print(f"❌ {desc}: 失败 - {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"⏰ {desc}: 超时")
        except Exception as e:
            print(f"⚠️  {desc}: 错误 - {e}")

def main():
    print("🛡️  OpenClaw安全配置诊断")
    print("=" * 50)
    print("问题: webhook到localhost被安全策略阻止")
    print("=" * 50)
    
    check_security_settings()
    check_webhook_access()
    
    print("\n💡 解决方案:")
    print("1. 检查安全策略配置")
    print("2. 允许localhost访问（如果需要）")
    print("3. 使用127.0.0.1代替localhost")
    print("4. 调整webhook目标URL")
    
    print("\n🔧 临时解决方案:")
    print("   修改webhook URL为: http://127.0.0.1:18789/webhook/pulse")

if __name__ == "__main__":
    main()