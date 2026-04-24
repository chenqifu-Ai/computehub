#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速模型测试 - 只测试模型可用性
"""

import subprocess
import json
from datetime import datetime

models = [
    "glm-4.7-flash:latest",
    "qwen:0.5b", 
    "Llama3.1:latest",
    "ministral-3:8b",
    "gemma3:4b",
    "deepseek-coder:6.7b"
]

results = []

print("🚀 快速模型测试开始...")
print(f"测试时间: {datetime.now().isoformat()}")
print("=" * 50)

for model in models:
    print(f"\n🧪 测试: {model}")
    try:
        # 快速测试 - 只检查模型是否响应
        result = subprocess.run([
            "curl", "-s", "-m", "10", "-X", "POST",
            "http://192.168.1.7:11434/api/generate",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "model": model,
                "prompt": "Hi",
                "stream": False
            })
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and "response" in result.stdout:
            print(f"✅ {model} - 可用")
            results.append({"model": model, "status": "可用", "response_time": "< 15s"})
        else:
            print(f"❌ {model} - 不可用")
            results.append({"model": model, "status": "不可用", "error": result.stderr[:100]})
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {model} - 超时")
        results.append({"model": model, "status": "超时"})
    except Exception as e:
        print(f"❌ {model} - 错误: {str(e)}")
        results.append({"model": model, "status": "错误", "error": str(e)})

print("\n" + "=" * 50)
print("📊 测试结果汇总:")
print("=" * 50)

available = [r for r in results if r["status"] == "可用"]
print(f"\n✅ 可用模型: {len(available)}/{len(models)}")

for r in results:
    status_emoji = "✅" if r["status"] == "可用" else "❌"
    print(f"{status_emoji} {r['model']}: {r['status']}")

print(f"\n完成时间: {datetime.now().isoformat()}")