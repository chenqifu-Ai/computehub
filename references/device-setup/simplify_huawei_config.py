#!/usr/bin/env python3
"""
简化华为手机上的OpenClaw配置，只保留常用模型
"""
import json
import subprocess

def run_ssh_command(command):
    """执行SSH命令"""
    try:
        result = subprocess.run(
            ["sshpass", "-p", "123", "ssh", "-p", "8022", "-o", "StrictHostKeyChecking=no", 
             "u0_a46@192.168.1.9", command],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_config():
    """获取当前配置"""
    config_cmd = "cat ~/.openclaw/openclaw.json"
    config_json = run_ssh_command(config_cmd)
    try:
        return json.loads(config_json)
    except:
        return None

def simplify_models(config):
    """简化模型配置"""
    if "agents" in config and "defaults" in config["agents"] and "models" in config["agents"]["defaults"]:
        # 只保留几个常用模型
        keep_models = [
            "modelstudio/qwen3.5-flash",    # 轻量级，适合移动设备
            "modelstudio/qwen3.5-plus",     # 标准版
            "ollama-cloud/deepseek-v3.1:671b",  # 深度求索
            "ollama/llama3:latest"          # 本地LLaMA
        ]
        
        # 创建简化后的模型列表
        simplified_models = {}
        for model_id in keep_models:
            if model_id in config["agents"]["defaults"]["models"]:
                simplified_models[model_id] = config["agents"]["defaults"]["models"][model_id]
        
        config["agents"]["defaults"]["models"] = simplified_models
    return config

def main():
    print("🔧 简化华为手机OpenClaw配置...")
    
    # 获取当前配置
    config = get_config()
    if not config:
        print("❌ 无法获取配置")
        return
    
    # 备份原配置
    backup_cmd = "cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.$(date +%Y%m%d_%H%M%S)"
    run_ssh_command(backup_cmd)
    print("✅ 配置已备份")
    
    # 简化配置
    simplified_config = simplify_models(config)
    
    # 保存简化后的配置
    config_str = json.dumps(simplified_config, indent=2, ensure_ascii=False)
    
    # 写入临时文件并传输
    temp_file = "/tmp/simplified_openclaw.json"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(config_str)
    
    # 传输到华为手机
    transfer_cmd = f"sshpass -p '123' scp -P 8022 -o StrictHostKeyChecking=no {temp_file} u0_a46@192.168.1.9:~/.openclaw/openclaw.json"
    subprocess.run(transfer_cmd, shell=True)
    
    print("✅ 配置已简化并传输")
    print("📋 保留的模型:")
    print("  - modelstudio/qwen3.5-flash (默认)")
    print("  - modelstudio/qwen3.5-plus")
    print("  - ollama-cloud/deepseek-v3.1:671b")
    print("  - ollama/llama3:latest")

if __name__ == "__main__":
    main()