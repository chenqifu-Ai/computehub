#!/usr/bin/env python3
"""
Ollama模型迁移脚本 - 将本地模型迁移到远程服务器
目标主机: 172.24.4.71
"""

import os
import subprocess
import json
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """执行shell命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"错误: {result.stderr}")
        return None
    return result

def get_local_models():
    """获取本地模型列表"""
    result = run_command("ollama list")
    if not result:
        return []
    
    models = []
    lines = result.stdout.strip().split('\n')
    for line in lines[1:]:  # 跳过标题行
        if line.strip():
            parts = line.split()
            model_name = parts[0]
            model_size = parts[2]
            models.append({"name": model_name, "size": model_size})
    return models

def check_remote_ollama(host):
    """检查远程服务器Ollama状态"""
    print(f"检查远程服务器 {host} 的Ollama状态...")
    
    # 检查Ollama是否安装
    result = run_command(f"ssh {host} 'which ollama'", check=False)
    if result and result.returncode == 0:
        print("✅ 远程服务器已安装Ollama")
        
        # 检查Ollama服务状态
        service_status = run_command(f"ssh {host} 'ps aux | grep ollama | grep -v grep'", check=False)
        if service_status and service_status.stdout.strip():
            print("✅ 远程Ollama服务正在运行")
        else:
            print("⚠️ 远程Ollama服务未运行，尝试启动...")
            run_command(f"ssh {host} 'nohup ollama serve > /dev/null 2>&1 &'")
            
        # 检查远程模型
        remote_models = run_command(f"ssh {host} 'ollama list'", check=False)
        if remote_models:
            print("远程现有模型:")
            print(remote_models.stdout)
        else:
            print("远程服务器暂无模型")
        return True
    else:
        print("❌ 远程服务器未安装Ollama")
        return False

def migrate_model(model_name, host):
    """迁移单个模型到远程服务器"""
    print(f"\n🚀 开始迁移模型: {model_name}")
    
    # 方法1: 使用ollama pull直接拉取（推荐）
    print(f"方法1: 在远程服务器直接拉取模型 {model_name}")
    result = run_command(f"ssh {host} 'ollama pull {model_name}'", check=False)
    
    if result and result.returncode == 0:
        print(f"✅ 模型 {model_name} 迁移成功")
        return True
    else:
        print(f"❌ 直接拉取失败，尝试方法2...")
        
        # 方法2: 手动传输模型文件
        print(f"方法2: 手动传输模型文件 {model_name}")
        
        # 获取模型文件路径
        model_path = f"/root/.ollama/models/manifests/registry.ollama.ai/library/{model_name.replace(':', '/')}"
        if os.path.exists(model_path):
            # 创建远程目录
            run_command(f"ssh {host} 'mkdir -p ~/.ollama/models/manifests/registry.ollama.ai/library/{model_name.split(':')[0]}'")
            
            # 传输文件
            run_command(f"scp -r {model_path} {host}:~/.ollama/models/manifests/registry.ollama.ai/library/{model_name.replace(':', '/')}")
            print(f"✅ 模型文件传输完成")
            return True
        else:
            print(f"❌ 找不到模型文件: {model_path}")
            return False

def main():
    target_host = "172.24.4.71"
    
    print("=" * 60)
    print("🤖 Ollama模型迁移工具")
    print("=" * 60)
    
    # 检查本地模型
    print("📊 本地模型列表:")
    local_models = get_local_models()
    for model in local_models:
        print(f"  - {model['name']} ({model['size']})")
    
    if not local_models:
        print("❌ 没有找到本地模型")
        return
    
    # 检查远程服务器
    if not check_remote_ollama(target_host):
        print("\n❌ 请先在远程服务器安装Ollama:")
        print("curl -fsSL https://ollama.com/install.sh | sh")
        return
    
    # 开始迁移
    print(f"\n🔄 开始迁移模型到 {target_host}")
    
    success_count = 0
    for model in local_models:
        if migrate_model(model['name'], target_host):
            success_count += 1
    
    # 验证迁移结果
    print(f"\n📋 迁移完成:")
    print(f"✅ 成功迁移: {success_count}/{len(local_models)} 个模型")
    
    # 检查最终状态
    print(f"\n🔍 最终验证:")
    remote_result = run_command(f"ssh {target_host} 'ollama list'", check=False)
    if remote_result:
        print("远程服务器模型列表:")
        print(remote_result.stdout)
    
    print("\n🎉 迁移完成！")

if __name__ == "__main__":
    main()