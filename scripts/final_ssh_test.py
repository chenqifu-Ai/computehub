#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终SSH连接测试和验证
"""

import subprocess
import os

def test_ssh_with_details():
    """详细测试SSH连接"""
    print("🔍 详细SSH连接测试...")
    
    cmd = [
        'ssh', '-v',
        '-i', '/root/.ssh/id_openclaw',
        '-p', '8022',
        'openclaw-tui@192.168.1.19',
        'echo "连接测试"'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        print("📋 SSH客户端输出:")
        print("=" * 50)
        
        # 分析输出
        lines = result.stderr.split('\n')
        
        key_offered = False
        auth_success = False
        
        for line in lines:
            if "Offering public key" in line and "id_openclaw" in line:
                print(f"✅ {line}")
                key_offered = True
            elif "Authentication succeeded" in line:
                print(f"🎉 {line}")
                auth_success = True
            elif "Permission denied" in line:
                print(f"❌ {line}")
            elif "debug1" in line and ("publickey" in line or "authenticat" in line):
                print(f"🔍 {line}")
        
        print("=" * 50)
        
        if key_offered and not auth_success:
            print("\n⚠️  问题分析: 密钥被提供但认证失败")
            print("可能原因:")
            print("1. 远程服务器 authorized_keys 文件权限问题")
            print("2. 公钥格式不正确")
            print("3. SSH服务器配置限制")
            print("4. 用户目录权限问题")
            
        elif auth_success:
            print("\n🎉 SSH密钥认证成功!")
            return True
            
        else:
            print("\n❌ 密钥未被正确提供")
            
        return False
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def create_connection_helper():
    """创建连接帮助脚本"""
    content = """#!/bin/bash
# OpenClaw SSH连接助手

echo "🔧 SSH连接问题诊断"
echo "===================="

# 1. 测试网络连通性
echo "1. 网络测试:"
ping -c 2 192.168.1.19 &>/dev/null && echo "  ✅ 网络通畅" || echo "  ❌ 网络问题"

# 2. 测试端口
echo "2. 端口测试:"
nc -z -w 2 192.168.1.19 8022 &>/dev/null && echo "  ✅ 端口8022开放" || echo "  ❌ 端口不可达"

# 3. 显示密钥信息
echo "3. 密钥信息:"
echo "   私钥: ~/.ssh/id_openclaw"
echo "   公钥: $(cat ~/.ssh/id_openclaw.pub | cut -d' ' -f1-2)"

# 4. 测试连接
echo "4. 连接测试:"
ssh -o BatchMode=yes -o ConnectTimeout=5 -i ~/.ssh/id_openclaw -p 8022 openclaw-tui@192.168.1.19 "echo 测试" &>/dev/null

if [ $? -eq 0 ]; then
    echo "  ✅ SSH密钥认证成功"
else
    echo "  ❌ SSH认证失败"
    echo ""
    echo "💡 解决方案:"
    echo "  在192.168.1.19上检查:"
    echo "  - ~/.ssh/authorized_keys 文件权限 (应为600)"
    echo "  - ~/.ssh/ 目录权限 (应为700)" 
    echo "  - 公钥内容是否匹配"
    echo "  - 运行: ls -la ~/.ssh/"
fi

echo "===================="
"""
    
    script_path = "/root/.openclaw/workspace/scripts/ssh_connection_helper.sh"
    
    with open(script_path, 'w') as f:
        f.write(content)
    
    os.chmod(script_path, 0o755)
    print(f"✅ 连接帮助脚本创建: {script_path}")
    return script_path

def main():
    """主函数"""
    print("=" * 60)
    print("🔐 最终SSH连接验证")
    print("=" * 60)
    
    # 测试连接
    success = test_ssh_with_details()
    
    if not success:
        print("\n🛠️  创建诊断工具...")
        helper_script = create_connection_helper()
        
        print(f"\n📋 公钥内容 (用于验证):")
        with open('/root/.ssh/id_openclaw.pub', 'r') as f:
            print(f.read().strip())
        
        print(f"\n🚀 运行诊断脚本:")
        print(f"bash {helper_script}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()