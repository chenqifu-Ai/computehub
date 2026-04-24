#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续监控 192.168.2.134 控制状态
确保目标机器保持在控制范围内
"""

import requests
import json
import time
import subprocess
from datetime import datetime

def ping_target():
    """Ping 目标机器检查连通性"""
    try:
        result = subprocess.run(['ping', '-c', '1', '192.168.2.134'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        print(f"Ping failed: {e}")
        return False

def check_ollama_api():
    """检查 Ollama API 是否可用"""
    try:
        response = requests.get('http://192.168.2.134:11434/api/tags', timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Ollama API check failed: {e}")
        return False

def test_ollama_interaction():
    """测试 Ollama 交互能力"""
    try:
        payload = {
            "model": "gemma3:1b",
            "prompt": "Confirm system status: online",
            "stream": False
        }
        response = requests.post('http://192.168.2.134:11434/api/generate', 
                               json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return "online" in result.get('response', '').lower()
        return False
    except Exception as e:
        print(f"Ollama interaction test failed: {e}")
        return False

def monitor_target():
    """主监控循环"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始监控 192.168.2.134")
    
    # 执行一次完整的检查
    ping_ok = ping_target()
    api_ok = check_ollama_api()
    interaction_ok = test_ollama_interaction()
    
    status = {
        'timestamp': datetime.now().isoformat(),
        'ping': ping_ok,
        'ollama_api': api_ok,
        'ollama_interaction': interaction_ok,
        'fully_controlled': ping_ok and api_ok and interaction_ok
    }
    
    print(f"监控结果:")
    print(f"  - Ping 连通性: {'✅' if ping_ok else '❌'}")
    print(f"  - Ollama API: {'✅' if api_ok else '❌'}")
    print(f"  - Ollama 交互: {'✅' if interaction_ok else '❌'}")
    print(f"  - 完全控制: {'✅ YES' if status['fully_controlled'] else '❌ NO'}")
    
    # 保存监控结果
    result_file = f"/root/.openclaw/workspace/ai_agent/results/monitor_134_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump(status, f, indent=2)
    
    print(f"结果已保存: {result_file}")
    return status['fully_controlled']

if __name__ == "__main__":
    success = monitor_target()
    exit(0 if success else 1)