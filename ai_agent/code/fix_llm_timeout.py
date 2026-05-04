#!/usr/bin/env python3
"""
修复LLM请求超时问题的脚本
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

def check_network_connectivity():
    """检查网络连接"""
    print("🔍 检查网络连接...")
    
    # 检查本地Ollama服务器
    try:
        result = subprocess.run(['ping', '-c', '1', '192.168.1.7'], 
                              capture_output=True, timeout=5)
        local_ollama_up = result.returncode == 0
        print(f"本地Ollama服务器 (192.168.1.7): {'✅ 正常' if local_ollama_up else '❌ 离线'}")
    except Exception as e:
        local_ollama_up = False
        print(f"本地Ollama服务器检查失败: {e}")
    
    # 检查互联网连接
    try:
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                              capture_output=True, timeout=5)
        internet_up = result.returncode == 0
        print(f"互联网连接: {'✅ 正常' if internet_up else '❌ 离线'}")
    except Exception as e:
        internet_up = False
        print(f"互联网连接检查失败: {e}")
    
    return local_ollama_up, internet_up

def test_model_endpoints():
    """测试模型端点"""
    print("\n🧪 测试模型端点...")
    
    endpoints = [
        ("本地Ollama", "http://192.168.1.7:11434/api/tags"),
        ("云端Ollama", "https://ollama.com/api/tags"),
    ]
    
    working_endpoints = []
    
    for name, url in endpoints:
        try:
            print(f"测试 {name} ({url})...")
            result = subprocess.run([
                'curl', '-s', '--max-time', '10', url
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and '"models"' in result.stdout:
                print(f"✅ {name}: 可用")
                working_endpoints.append((name, url))
            else:
                print(f"❌ {name}: 不可用")
        except Exception as e:
            print(f"❌ {name}: 测试失败 - {e}")
    
    return working_endpoints

def configure_fallback_model():
    """配置备用模型"""
    print("\n⚙️ 配置备用模型...")
    
    # 创建配置目录
    config_dir = Path("/root/.openclaw/workspace/config")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置文件路径
    model_config_path = config_dir / "model.conf"
    
    # 优先使用云端模型（因为本地服务器离线）
    model_config = {
        "primary": {
            "provider": "modelstudio",
            "model": "qwen3-max",
            "timeout": 60
        },
        "fallback": {
            "provider": "ollama-cloud",
            "base_url": "https://ollama.com",
            "models": ["qwen3.5:397b", "glm-5", "qwen3-next:80b"]
        },
        "timeout_settings": {
            "connect_timeout": 10,
            "read_timeout": 60,
            "total_timeout": 120
        }
    }
    
    with open(model_config_path, 'w') as f:
        json.dump(model_config, f, indent=2)
    
    print(f"✅ 模型配置已保存到: {model_config_path}")

def update_openclaw_config():
    """更新OpenClaw配置"""
    print("\n🔧 更新OpenClaw配置...")
    
    # 设置环境变量
    env_vars = {
        "OPENCLAW_MODEL_TIMEOUT": "120",
        "OPENCLAW_CONNECT_TIMEOUT": "10",
        "OPENCLAW_READ_TIMEOUT": "60"
    }
    
    # 写入环境配置文件
    env_file = Path("/root/.openclaw/workspace/.env")
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"✅ 环境配置已保存到: {env_file}")
    print("请确保在启动OpenClaw时加载此环境文件")

def main():
    """主函数"""
    print("🚀 开始修复LLM请求超时问题...\n")
    
    # 1. 检查网络连接
    local_up, internet_up = check_network_connectivity()
    
    if not internet_up:
        print("\n❌ 互联网连接不可用，请先修复网络连接")
        return False
    
    # 2. 测试模型端点
    working_endpoints = test_model_endpoints()
    
    if not working_endpoints:
        print("\n❌ 所有模型端点都不可用，请检查网络或服务状态")
        return False
    
    # 3. 配置备用模型
    configure_fallback_model()
    
    # 4. 更新OpenClaw配置
    update_openclaw_config()
    
    print("\n✅ LLM请求超时问题修复完成!")
    print("\n📋 建议操作:")
    print("1. 重启OpenClaw以应用新的超时设置")
    print("2. 如果问题持续存在，考虑切换到更小的模型以减少响应时间")
    print("3. 监控本地Ollama服务器 (192.168.1.7) 的状态")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)