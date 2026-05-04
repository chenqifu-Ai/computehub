#!/usr/bin/env python3
"""
同步Ollama配置到华为手机
主要同步Ollama云端账号配置
"""

import json
import subprocess
import tempfile
import os

def get_current_config():
    """获取当前OpenClaw配置"""
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_ollama_config(full_config):
    """提取Ollama相关配置"""
    ollama_config = {
        "auth": {
            "profiles": full_config.get("auth", {}).get("profiles", {})
        },
        "models": {
            "providers": {
                "ollama-cloud": full_config.get("models", {}).get("providers", {}).get("ollama-cloud", {})
            }
        },
        "agents": {
            "defaults": {
                "model": full_config.get("agents", {}).get("defaults", {}).get("model", {}),
                "models": full_config.get("agents", {}).get("defaults", {}).get("models", {})
            }
        }
    }
    return ollama_config

def update_target_config(target_config, ollama_config):
    """更新目标配置中的Ollama设置"""
    # 更新auth profiles
    if "auth" not in target_config:
        target_config["auth"] = {}
    if "profiles" not in target_config["auth"]:
        target_config["auth"]["profiles"] = {}
    
    target_config["auth"]["profiles"].update(ollama_config["auth"]["profiles"])
    
    # 更新models providers
    if "models" not in target_config:
        target_config["models"] = {}
    if "providers" not in target_config["models"]:
        target_config["models"]["providers"] = {}
    
    target_config["models"]["providers"].update(ollama_config["models"]["providers"])
    
    # 更新agents defaults
    if "agents" not in target_config:
        target_config["agents"] = {}
    if "defaults" not in target_config["agents"]:
        target_config["agents"]["defaults"] = {}
    
    if "model" in ollama_config["agents"]["defaults"]:
        target_config["agents"]["defaults"]["model"] = ollama_config["agents"]["defaults"]["model"]
    
    if "models" in ollama_config["agents"]["defaults"]:
        if "models" not in target_config["agents"]["defaults"]:
            target_config["agents"]["defaults"]["models"] = {}
        target_config["agents"]["defaults"]["models"].update(ollama_config["agents"]["defaults"]["models"])
    
    return target_config

def sync_to_huawei():
    """同步配置到华为手机"""
    # 获取当前配置
    current_config = get_current_config()
    ollama_config = extract_ollama_config(current_config)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        json.dump(ollama_config, temp_file, indent=2, ensure_ascii=False)
        temp_path = temp_file.name
    
    try:
        # 先备份目标设备的配置
        print("备份华为手机当前配置...")
        backup_cmd = [
            "sshpass", "-p", "123", "ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022",
            "u0_a46@192.168.2.156", 
            "cd ~/.openclaw && cp openclaw.json openclaw.json.backup.$(date +%Y%m%d_%H%M%S)"
        ]
        subprocess.run(backup_cmd, check=True)
        
        # 获取目标设备的当前配置
        print("获取华为手机当前配置...")
        get_config_cmd = [
            "sshpass", "-p", "123", "ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022",
            "u0_a46@192.168.2.156", "cat ~/.openclaw/openclaw.json"
        ]
        result = subprocess.run(get_config_cmd, capture_output=True, text=True, check=True)
        target_config = json.loads(result.stdout)
        
        # 更新配置
        print("更新Ollama配置...")
        updated_config = update_target_config(target_config, ollama_config)
        
        # 将更新后的配置写回临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as updated_temp:
            json.dump(updated_config, updated_temp, indent=2, ensure_ascii=False)
            updated_temp_path = updated_temp.name
        
        # 传输更新后的配置到目标设备
        print("传输更新后的配置...")
        transfer_cmd = [
            "sshpass", "-p", "123", "scp", "-o", "StrictHostKeyChecking=no", "-P", "8022",
            updated_temp_path, "u0_a46@192.168.2.156:~/.openclaw/openclaw.json"
        ]
        subprocess.run(transfer_cmd, check=True)
        
        # 重启OpenClaw服务使配置生效
        print("重启OpenClaw服务...")
        restart_cmd = [
            "sshpass", "-p", "123", "ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022",
            "u0_a46@192.168.2.156",
            "pkill -f 'openclaw' && sleep 2 && openclaw gateway --port 18789 &"
        ]
        subprocess.run(restart_cmd, check=True)
        
        print("✅ Ollama配置同步完成!")
        print("Ollama云端API Key已同步到华为手机")
        print("所有Ollama Cloud模型配置已更新")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 同步失败: {e}")
        return False
    finally:
        # 清理临时文件
        os.unlink(temp_path)
        if 'updated_temp_path' in locals():
            os.unlink(updated_temp_path)
    
    return True

if __name__ == "__main__":
    sync_to_huawei()