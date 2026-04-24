#!/usr/bin/env python3
"""
修复OpenClaw模型配置问题
将默认模型固定为 ollama-cloud/deepseek-v3.1:671b
"""

import os
import json
import glob
from pathlib import Path

def find_openclaw_config_files():
    """查找所有可能的OpenClaw配置文件"""
    config_locations = [
        "/root/.openclaw",
        "/root/.openclaw/agents/main/agent",
        "/root/.openclaw/workspace/config",
        "/root/.openclaw/gateway",
    ]
    
    config_files = []
    for location in config_locations:
        if os.path.exists(location):
            for root, dirs, files in os.walk(location):
                for file in files:
                    if file.endswith(('.json', '.yaml', '.yml', '.toml', '.conf')):
                        full_path = os.path.join(root, file)
                        config_files.append(full_path)
    
    return config_files

def check_file_for_model_config(file_path):
    """检查文件是否包含模型配置"""
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
            # 检查是否包含模型相关配置
            model_keywords = ['model', 'models', 'defaultModel', 'agent', 'provider']
            content_str = json.dumps(content, ensure_ascii=False).lower()
            
            for keyword in model_keywords:
                if keyword in content_str:
                    return True, content
        
        elif file_path.endswith(('.yaml', '.yml', '.toml')):
            # 简单检查文本内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
            model_keywords = ['model', 'models', 'defaultmodel', 'agent', 'provider']
            for keyword in model_keywords:
                if keyword in content:
                    return True, content
                    
    except Exception as e:
        return False, f"Error reading {file_path}: {e}"
    
    return False, None

def analyze_current_model_config():
    """分析当前模型配置状态"""
    print("=== 当前模型配置分析 ===")
    
    # 1. 检查已知的模型配置文件
    models_json = "/root/.openclaw/agents/main/agent/models.json"
    if os.path.exists(models_json):
        print(f"✅ 找到模型配置文件: {models_json}")
        with open(models_json, 'r') as f:
            models_config = json.load(f)
        
        print("\n当前配置的模型提供商:")
        for provider in models_config.get('providers', {}):
            print(f"  - {provider}")
    else:
        print("❌ 未找到模型配置文件")
    
    # 2. 查找其他可能的配置文件
    print("\n=== 搜索其他配置文件 ===")
    config_files = find_openclaw_config_files()
    print(f"找到 {len(config_files)} 个配置文件")
    
    model_configs = []
    for file_path in config_files[:20]:  # 检查前20个文件
        has_model, content = check_file_for_model_config(file_path)
        if has_model:
            model_configs.append(file_path)
            print(f"✅ 包含模型配置: {file_path}")
    
    return model_configs

def main():
    """主函数"""
    print("开始分析OpenClaw模型配置问题...\n")
    
    # 分析当前配置
    model_configs = analyze_current_model_config()
    
    print("\n=== 问题诊断 ===")
    print("问题：模型老是切换到 modelstudio/qwen3-max")
    print("目标：固定为 ollama-cloud/deepseek-v3.1:671b")
    
    if model_configs:
        print("\n=== 解决方案 ===")
        print("1. 需要修改默认模型配置")
        print("2. 设置 ollama-cloud/deepseek-v3.1:671b 为默认")
        print("3. 禁用 modelstudio 提供商的自动选择")
        
        print("\n需要修改的文件:")
        for config_file in model_configs:
            print(f"  - {config_file}")
    else:
        print("\n❌ 未找到明确的模型配置文件")
        print("可能需要检查OpenClaw的系统级配置")

if __name__ == "__main__":
    main()