#!/usr/bin/env python3
"""
配置同步脚本 - 将本机配置同步到华为手机(192.168.1.9)
注意：不升级OpenClaw，只同步配置和Ollama账户
"""

import os
import subprocess
import json
import shutil
from pathlib import Path

def run_command(cmd, description):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 成功: {description}")
            return True, result.stdout
        else:
            print(f"❌ 失败: {description}")
            print(f"错误输出: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ 超时: {description}")
        return False, "命令执行超时"
    except Exception as e:
        print(f"💥 异常: {description} - {str(e)}")
        return False, str(e)

def sync_config_files():
    """同步配置文件"""
    print("\n📁 开始同步配置文件...")
    
    # 本地配置文件目录
    local_config_dir = "/root/.openclaw/workspace/config"
    
    # 目标设备信息
    target_host = "192.168.1.9"
    target_port = "8022"
    target_user = "u0_a46"
    target_password = "123"
    target_config_dir = "/data/data/com.termux/files/home/.openclaw/workspace/config"
    
    # 检查本地配置目录是否存在
    if not os.path.exists(local_config_dir):
        print("❌ 本地配置目录不存在")
        return False
    
    # 创建目标配置目录（如果不存在）
    mkdir_cmd = f"sshpass -p {target_password} ssh -p {target_port} -o StrictHostKeyChecking=no {target_user}@{target_host} 'mkdir -p {target_config_dir}'"
    success, _ = run_command(mkdir_cmd, "创建目标配置目录")
    if not success:
        return False
    
    # 同步所有配置文件
    sync_cmd = f"cd {local_config_dir} && tar czf - . | sshpass -p {target_password} ssh -p {target_port} -o StrictHostKeyChecking=no {target_user}@{target_host} 'cd {target_config_dir} && tar xzf -'"
    success, _ = run_command(sync_cmd, "同步配置文件")
    
    return success

def sync_ollama_account():
    """同步Ollama账户信息"""
    print("\n🤖 开始同步Ollama账户信息...")
    
    # Ollama账户信息
    ollama_account_info = {
        "server": "https://ollama.com",
        "api_key": "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii",
        "account": "19525456@qq.com"
    }
    
    # 目标设备信息
    target_host = "192.168.1.9"
    target_port = "8022"
    target_user = "u0_a46"
    target_password = "123"
    target_ollama_dir = "/data/data/com.termux/files/home/.ollama"
    
    # 创建Ollama配置目录
    mkdir_cmd = f"sshpass -p {target_password} ssh -p {target_port} -o StrictHostKeyChecking=no {target_user}@{target_host} 'mkdir -p {target_ollama_dir}'"
    success, _ = run_command(mkdir_cmd, "创建Ollama配置目录")
    if not success:
        return False
    
    # 创建Ollama账户配置文件
    ollama_config_content = f"""# Ollama云端配置
server = {ollama_account_info['server']}
api_key = {ollama_account_info['api_key']}
account = {ollama_account_info['account']}
"""
    
    # 临时写入本地文件
    temp_file = "/tmp/ollama_account.conf"
    with open(temp_file, 'w') as f:
        f.write(ollama_config_content)
    
    # 传输到目标设备
    transfer_cmd = f"sshpass -p {target_password} scp -P {target_port} -o StrictHostKeyChecking=no {temp_file} {target_user}@{target_host}:{target_ollama_dir}/account.conf"
    success, _ = run_command(transfer_cmd, "传输Ollama账户配置")
    
    # 清理临时文件
    os.remove(temp_file)
    
    return success

def verify_sync():
    """验证同步结果"""
    print("\n🔍 开始验证同步结果...")
    
    target_host = "192.168.1.9"
    target_port = "8022"
    target_user = "u0_a46"
    target_password = "123"
    
    # 验证配置文件
    verify_config_cmd = f"sshpass -p {target_password} ssh -p {target_port} -o StrictHostKeyChecking=no {target_user}@{target_host} 'ls -la /data/data/com.termux/files/home/.openclaw/workspace/config/'"
    success, output = run_command(verify_config_cmd, "验证配置文件同步")
    
    # 验证Ollama配置
    verify_ollama_cmd = f"sshpass -p {target_password} ssh -p {target_port} -o StrictHostKeyChecking=no {target_user}@{target_host} 'cat /data/data/com.termux/files/home/.ollama/account.conf'"
    success2, output2 = run_command(verify_ollama_cmd, "验证Ollama配置同步")
    
    return success and success2

def main():
    """主函数"""
    print("=" * 60)
    print("🤖 华为手机配置同步工具")
    print("📱 目标设备: 192.168.1.9 (华为手机)")
    print("🎯 任务: 同步配置 + Ollama账户 (不升级OpenClaw)")
    print("=" * 60)
    
    # 执行同步
    config_success = sync_config_files()
    ollama_success = sync_ollama_account()
    
    # 验证结果
    if config_success and ollama_success:
        verify_success = verify_sync()
        if verify_success:
            print("\n🎉 同步完成！配置和Ollama账户已成功同步到华为手机")
            print("📋 同步内容:")
            print("   - 所有配置文件 (config/目录)")
            print("   - Ollama云端账户信息")
            print("   - 邮件配置 (email.conf)")
            print("   - 模型配置 (model.conf)")
            print("   - 股票监控配置")
            print("\n⚠️ 注意: OpenClaw版本保持不变，仅同步配置")
            return True
        else:
            print("\n❌ 同步完成但验证失败，请手动检查")
            return False
    else:
        print("\n❌ 同步失败")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)