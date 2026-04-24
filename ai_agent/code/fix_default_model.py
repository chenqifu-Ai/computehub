#!/usr/bin/env python3
"""
修复OpenClaw默认模型配置
将默认模型从 modelstudio/qwen3-max 改为 ollama-cloud/deepseek-v3.1:671b
"""

import json
import os

def fix_default_model():
    """修复默认模型配置"""
    config_file = "/root/.openclaw/openclaw.json"
    
    # 读取当前配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("=== 当前配置 ===")
    current_model = config.get('agents', {}).get('defaults', {}).get('model', {}).get('primary')
    print(f"当前默认模型: {current_model}")
    
    # 修改默认模型
    if 'agents' not in config:
        config['agents'] = {}
    if 'defaults' not in config['agents']:
        config['agents']['defaults'] = {}
    if 'model' not in config['agents']['defaults']:
        config['agents']['defaults']['model'] = {}
    
    config['agents']['defaults']['model']['primary'] = "ollama-cloud/deepseek-v3.1:671b"
    
    # 备份原文件
    backup_file = config_file + ".backup"
    os.system(f"cp {config_file} {backup_file}")
    print(f"✅ 已备份原文件到: {backup_file}")
    
    # 写入新配置
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("\n=== 修改后配置 ===")
    new_model = config['agents']['defaults']['model']['primary']
    print(f"新的默认模型: {new_model}")
    print("✅ 默认模型已修改完成！")
    
    return True

def verify_fix():
    """验证修复结果"""
    config_file = "/root/.openclaw/openclaw.json"
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    current_model = config.get('agents', {}).get('defaults', {}).get('model', {}).get('primary')
    
    if current_model == "ollama-cloud/deepseek-v3.1:671b":
        print("✅ 验证通过：默认模型已成功设置为 ollama-cloud/deepseek-v3.1:671b")
        return True
    else:
        print(f"❌ 验证失败：当前模型仍然是 {current_model}")
        return False

def main():
    """主函数"""
    print("开始修复OpenClaw默认模型配置...\n")
    
    # 执行修复
    if fix_default_model():
        print("\n=== 验证修复结果 ===")
        if verify_fix():
            print("\n🎉 修复完成！")
            print("下次启动OpenClaw时，将默认使用 ollama-cloud/deepseek-v3.1:671b")
        else:
            print("\n❌ 修复失败，请检查配置文件")
    else:
        print("❌ 修复过程中出现错误")

if __name__ == "__main__":
    main()