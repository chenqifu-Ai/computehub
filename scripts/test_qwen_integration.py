#!/usr/bin/env python3
"""
测试qwen2.5:0.5b模型集成到OpenClaw
"""

import requests
import json

def test_local_qwen():
    """测试本地qwen模型"""
    print("🧪 测试本地qwen2.5:0.5b模型...")
    
    try:
        # 测试模型列表
        response = requests.get("http://192.168.1.19:11434/api/tags")
        models = response.json()
        print(f"✅ 模型列表: {[m['name'] for m in models.get('models', [])]}")
        
        # 测试模型推理
        response = requests.post(
            "http://192.168.1.19:11434/api/generate",
            json={
                "model": "qwen2.5:0.5b",
                "prompt": "你好，测试集成是否成功",
                "stream": False
            }
        )
        result = response.json()
        print(f"✅ 推理测试成功: {result['response'][:50]}...")
        print(f"📊 响应时间: {result['total_duration']/1e9:.2f}秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_openclaw_config():
    """测试OpenClaw配置"""
    print("\n🔧 检查OpenClaw配置...")
    
    try:
        with open('/root/.openclaw/agents/main/agent/models.json', 'r') as f:
            config = json.load(f)
        
        ollama_config = config['providers']['ollama']
        print(f"✅ Ollama地址: {ollama_config['baseUrl']}")
        
        models = [m['id'] for m in ollama_config['models']]
        print(f"✅ 配置模型: {models}")
        
        if 'qwen2.5:0.5b' in models:
            print("✅ qwen2.5:0.5b 已成功集成到OpenClaw")
            return True
        else:
            print("❌ qwen2.5:0.5b 未在配置中找到")
            return False
            
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试qwen2.5:0.5b集成...")
    
    # 测试本地模型
    model_ok = test_local_qwen()
    
    # 测试配置
    config_ok = test_openclaw_config()
    
    # 总结
    print("\n" + "="*50)
    if model_ok and config_ok:
        print("🎉 集成测试完全成功！")
        print("📋 下一步: 重启OpenClaw网关使配置生效")
        print("💡 使用: openclaw gateway restart")
    else:
        print("⚠️  集成测试部分失败，请检查配置")
    print("="*50)