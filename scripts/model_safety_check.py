#!/usr/bin/env python3
"""
模型安全检查脚本 - 确保不会使用禁止的大模型
"""
import json
import os

def check_model_safety():
    """检查当前配置是否安全"""
    
    # 禁止使用的模型列表
    FORBIDDEN_MODELS = [
        "glm-4.7-flash:latest", 
        "glm-4.7-flash", 
        "glm-4.7",
        "glm-4.7-",  # 所有glm-4.7变体
        "glm-"  # 所有glm大模型
    ]
    
    print("🔒 正在进行模型安全检查...")
    
    # 检查ollama.toml配置 - 只检查实际使用的模型配置
    ollama_config_path = os.path.expanduser("~/.openclaw/config/ollama.toml")
    if os.path.exists(ollama_config_path):
        with open(ollama_config_path, 'r') as f:
            content = f.read()
            # 检查是否配置了glm模型作为默认模型
            if "model = " in content and "glm" in content:
                lines = content.split('\n')
                for line in lines:
                    if line.strip().startswith('model = ') and 'glm' in line:
                        print("❌ 发现不安全配置: ollama.toml 中配置了glm模型")
                        return False
    
    # 检查model.conf配置 - 只检查实际使用的模型
    model_config_path = os.path.expanduser("~/.openclaw/workspace/config/model.conf")
    if os.path.exists(model_config_path):
        with open(model_config_path, 'r') as f:
            config = json.load(f)
            primary_model = config.get("primary", {}).get("model", "")
            if "glm" in primary_model:
                print("❌ 发现不安全配置: model.conf 中配置了glm模型")
                return False
    
    print("✅ 配置安全检查通过 - 没有使用禁止的模型")
    return True

def get_current_models():
    """获取当前可用的安全模型"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            
            # 过滤出安全的模型
            safe_models = []
            for model in models:
                model_name = model.get("name", "")
                # 排除所有glm大模型
                if not any(forbidden in model_name for forbidden in ["glm-4.7", "glm-"]):
                    safe_models.append({
                        "name": model_name,
                        "size_mb": model.get("size", 0) / 1024 / 1024
                    })
            
            print("🟢 可用的安全模型:")
            for model in safe_models:
                print(f"   - {model['name']} ({model['size_mb']:.1f}MB)")
            
            return safe_models
    except:
        print("⚠️  无法获取模型列表，但配置检查通过")
        return []

if __name__ == "__main__":
    if check_model_safety():
        print("\n🎉 系统配置安全 - 绝对不会使用glm-4.7-flash等大模型")
        get_current_models()
    else:
        print("\n🚨 发现安全风险！请立即检查配置")
        exit(1)