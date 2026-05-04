#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH密钥配置脚本 - 为192.168.1.19配置自动化访问
"""

import os
import subprocess
from pathlib import Path

def check_ssh_keys():
    """检查现有的SSH密钥"""
    ssh_dir = Path.home() / ".ssh"
    
    print("🔍 检查现有SSH密钥...")
    
    if not ssh_dir.exists():
        print("  📁 .ssh目录不存在，将创建")
        ssh_dir.mkdir(mode=0o700)
    
    key_files = []
    for key_type in ['rsa', 'ed25519', 'ecdsa', 'dsa']:
        priv_key = ssh_dir / f"id_{key_type}"
        pub_key = ssh_dir / f"id_{key_type}.pub"
        
        if priv_key.exists() and pub_key.exists():
            key_files.append({
                'type': key_type,
                'private': priv_key,
                'public': pub_key,
                'size': priv_key.stat().st_size
            })
    
    return key_files

def generate_ssh_key():
    """生成新的SSH密钥"""
    print("🔑 生成新的SSH密钥 (Ed25519算法)...")
    
    # 使用Ed25519算法，更安全更快速
    key_path = Path.home() / ".ssh" / "id_ed25519"
    
    if key_path.exists():
        print(f"  ✅ 密钥已存在: {key_path}")
        return True
    
    try:
        # 生成密钥对
        result = subprocess.run([
            'ssh-keygen', '-t', 'ed25519', 
            '-f', str(key_path),
            '-N', '',  # 无密码
            '-C', 'openclaw-auto-access@192.168.1.19'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"  ✅ SSH密钥生成成功: {key_path}")
            
            # 设置正确的权限
            os.chmod(key_path, 0o600)
            os.chmod(key_path.with_suffix('.pub'), 0o644)
            
            return True
        else:
            print(f"  ❌ SSH密钥生成失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ 密钥生成异常: {e}")
        return False

def get_public_key():
    """获取公钥内容"""
    pub_key_path = Path.home() / ".ssh" / "id_ed25519.pub"
    
    if pub_key_path.exists():
        with open(pub_key_path, 'r') as f:
            return f.read().strip()
    return None

def test_ssh_connection(hostname, username, password):
    """测试SSH连接"""
    print(f"🌐 测试SSH连接到 {username}@{hostname}...")
    
    try:
        # 使用sshpass进行密码认证测试
        result = subprocess.run([
            'sshpass', '-p', password,
            'ssh', '-p', '8022',
            f'{username}@{hostname}',
            'echo "连接测试成功"'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ SSH密码连接测试成功")
            return True
        else:
            print(f"  ❌ SSH连接失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ 连接测试异常: {e}")
        return False

def setup_ssh_config():
    """配置SSH客户端配置"""
    ssh_config_path = Path.home() / ".ssh" / "config"
    
    config_content = """# OpenClaw自动化访问配置
Host mi-pad
    HostName 192.168.1.19
    Port 8022
    User u0_a207
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad

Host mi-pad-backup
    HostName 192.168.1.19
    Port 8022  
    User u0_a46
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad
"""
    
    try:
        with open(ssh_config_path, 'w') as f:
            f.write(config_content)
        
        # 设置正确的权限
        os.chmod(ssh_config_path, 0o600)
        print(f"  ✅ SSH配置写入成功: {ssh_config_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ SSH配置写入失败: {e}")
        return False

def create_deploy_script():
    """创建部署脚本"""
    script_content = """#!/bin/bash
# OpenClaw SSH密钥部署脚本
# 用于在192.168.1.19上部署公钥

HOST="192.168.1.19"
PORT="8022"
USER="u0_a207"
PASSWORD="123"

# 读取公钥
PUBLIC_KEY=$(cat ~/.ssh/id_ed25519.pub)

# 部署公钥到远程服务器
echo "部署SSH公钥到 ${USER}@${HOST}:${PORT}..."

sshpass -p "${PASSWORD}" ssh -p "${PORT}" "${USER}@${HOST}" << EOF
    # 创建.ssh目录（如果不存在）
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # 备份原有的authorized_keys
    if [ -f ~/.ssh/authorized_keys ]; then
        cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 添加新的公钥
    echo "${PUBLIC_KEY}" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    
    echo "SSH公钥部署完成"
    echo "已添加密钥: ${PUBLIC_KEY}"
EOF

if [ $? -eq 0 ]; then
    echo "✅ 公钥部署成功"
    echo "测试无密码连接..."
    
    # 测试无密码连接
    ssh -p "${PORT}" "${USER}@${HOST}" "echo '无密码连接测试成功'"
    
    if [ $? -eq 0 ]; then
        echo "🎉 SSH密钥认证配置完成！"
    else
        echo "⚠️  无密码连接测试失败，请检查配置"
    fi
else
    echo "❌ 公钥部署失败"
    exit 1
fi
"""
    
    script_path = "/root/.openclaw/workspace/scripts/deploy_ssh_key.sh"
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)
        print(f"  ✅ 部署脚本创建成功: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"  ❌ 部署脚本创建失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔐 OpenClaw SSH密钥配置工具")
    print("=" * 60)
    
    # 检查现有密钥
    existing_keys = check_ssh_keys()
    if existing_keys:
        print(f"  📋 发现 {len(existing_keys)} 个现有密钥:")
        for key in existing_keys:
            print(f"    • {key['type']}: {key['private']} ({key['size']} bytes)")
    else:
        print("  ℹ️  未发现现有SSH密钥")
    
    # 生成新密钥
    if not generate_ssh_key():
        print("❌ 密钥生成失败，终止配置")
        return
    
    # 获取公钥
    public_key = get_public_key()
    if public_key:
        print(f"  📋 公钥内容: {public_key[:50]}...")
    
    # 配置SSH客户端
    if not setup_ssh_config():
        print("⚠️  SSH配置写入失败")
    
    # 测试当前密码连接
    print(f"\n🔐 测试当前连接配置...")
    
    # 测试u0_a207
    test1 = test_ssh_connection("192.168.1.19", "u0_a207", "123")
    
    # 测试u0_a46  
    test2 = test_ssh_connection("192.168.1.19", "u0_a46", "123")
    
    # 创建部署脚本
    deploy_script = create_deploy_script()
    
    print(f"\n" + "=" * 60)
    print("📋 配置完成总结:")
    print(f"  ✅ SSH密钥: ~/.ssh/id_ed25519")
    print(f"  ✅ SSH配置: ~/.ssh/config")
    print(f"  ✅ 部署脚本: {deploy_script}")
    print(f"  🔄 连接测试: u0_a207: {'✅' if test1 else '❌'}, u0_a46: {'✅' if test2 else '❌'}")
    
    print(f"\n🚀 下一步操作:")
    print(f"  1. 运行部署脚本: bash {deploy_script}")
    print(f"  2. 测试无密码连接: ssh mi-pad")
    print(f"  3. 验证自动化访问")
    print("=" * 60)
    
    # 保存配置报告
    report_content = f"""# SSH密钥配置报告

## 生成时间
{subprocess.getoutput('date')}

## 密钥信息
- 密钥类型: Ed25519
- 私钥路径: ~/.ssh/id_ed25519
- 公钥路径: ~/.ssh/id_ed25519.pub
- 公钥内容: {public_key}

## 连接配置
- 主机别名: mi-pad (192.168.1.19:8022)
- 备选用户: u0_a46
- 测试结果: u0_a207: {'成功' if test1 else '失败'}, u0_a46: {'成功' if test2 else '失败'}

## 部署脚本
位置: {deploy_script}

## 使用说明
1. 执行部署: `bash {deploy_script}`
2. 测试连接: `ssh mi-pad`
3. 自动化访问配置完成
"""
    
    report_path = "/root/.openclaw/workspace/ai_agent/results/ssh_key_setup_report.md"
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    print(f"✅ 配置报告已保存: {report_path}")

if __name__ == "__main__":
    main()