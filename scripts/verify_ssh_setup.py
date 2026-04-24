#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证和修复SSH密钥设置
"""

import subprocess
import os

def check_local_key():
    """检查本地密钥"""
    print("🔍 检查本地SSH密钥...")
    
    key_path = "/root/.ssh/id_openclaw"
    pub_key_path = "/root/.ssh/id_openclaw.pub"
    
    # 检查文件存在性
    if not os.path.exists(key_path):
        print("❌ 私钥文件不存在")
        return False
    
    if not os.path.exists(pub_key_path):
        print("❌ 公钥文件不存在") 
        return False
    
    # 检查权限
    key_mode = os.stat(key_path).st_mode
    if key_mode & 0o777 != 0o600:
        print("⚠️  私钥权限不正确，修复中...")
        os.chmod(key_path, 0o600)
    
    # 读取公钥内容
    with open(pub_key_path, 'r') as f:
        pub_key = f.read().strip()
    
    print(f"✅ 本地密钥正常: {pub_key[:50]}...")
    return True, pub_key

def test_ssh_connection():
    """测试SSH连接"""
    print("\n🌐 测试SSH连接...")
    
    try:
        result = subprocess.run([
            'ssh', '-o', 'BatchMode=yes', 
            '-o', 'ConnectTimeout=5',
            '-i', '/root/.ssh/id_openclaw',
            '-p', '8022',
            'u0_a207@192.168.1.19',
            'echo "连接成功"'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ SSH密钥认证成功!")
            return True
        else:
            print(f"❌ SSH连接失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 连接测试异常: {e}")
        return False

def create_remote_fix_script(pub_key):
    """创建远程修复脚本"""
    print("\n🔧 创建远程修复脚本...")
    
    script_content = f"""#!/bin/bash
# 远程SSH配置修复脚本

echo "🔧 修复远程SSH配置..."

# 1. 确保.ssh目录存在且权限正确
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. 清理并重新添加公钥
echo "清理现有的authorized_keys..."
> ~/.ssh/authorized_keys

# 3. 添加正确的公钥
echo "添加新的公钥..."
echo "{pub_key}" >> ~/.ssh/authorized_keys

# 4. 设置正确的权限
chmod 600 ~/.ssh/authorized_keys

# 5. 验证配置
echo "验证配置..."
ls -la ~/.ssh/
echo "公钥内容:"
cat ~/.ssh/authorized_keys

echo "✅ 远程配置修复完成"
"""
    
    script_path = "/root/.openclaw/workspace/scripts/remote_ssh_fix.sh"
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        print(f"✅ 远程修复脚本创建成功: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"❌ 脚本创建失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔐 SSH密钥配置验证工具")
    print("=" * 60)
    
    # 检查本地密钥
    key_ok, pub_key = check_local_key()
    if not key_ok:
        print("❌ 本地密钥检查失败")
        return
    
    # 测试连接
    if test_ssh_connection():
        print("\n🎉 SSH密钥认证已正常工作!")
        return
    
    # 创建远程修复脚本
    fix_script = create_remote_fix_script(pub_key)
    
    print(f"\n🚀 下一步操作:")
    print(f"1. 手动连接到192.168.1.19")
    print(f"2. 运行修复脚本: bash {fix_script}")
    print(f"3. 或者手动检查 ~/.ssh/authorized_keys 文件")
    print("=" * 60)
    
    # 显示公钥内容以便手动检查
    print(f"\n📋 公钥内容 (用于手动检查):")
    print(pub_key)
    print("=" * 60)

if __name__ == "__main__":
    main()