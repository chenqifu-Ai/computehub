#!/usr/bin/env python3
"""
基于实际配置文件的模型配置审计
"""

import os
import json
import subprocess
from pathlib import Path

def test_endpoint(url, timeout=10):
    """测试端点连通性"""
    try:
        cmd = ["curl", "-s", "-f", f"-m {timeout}", url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def main():
    print("🔍 基于实际配置文件的模型审计")
    print("=" * 50)
    
    # 从 ollama.toml 提取配置
    config_file = Path("/root/.openclaw/config/ollama.toml")
    if not config_file.exists():
        print("❌ 未找到 ollama.toml 配置文件")
        return
    
    # 手动解析配置（因为没有 TOML 解析器）
    configs = {}
    current_section = None
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                # Section header
                section = line[1:-1].strip()
                current_section = section
                configs[section] = {}
            elif '=' in line and current_section:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                configs[current_section][key] = value
    
    print(f"📊 找到 {len(configs)} 个配置段:")
    for section in configs:
        print(f"  - {section}")
    
    # 测试每个配置
    results = {}
    
    for section, config in configs.items():
        if 'url' not in config:
            continue
            
        url = config['url']
        print(f"\n🧪 测试 {section}: {url}")
        
        # 对于 Ollama API，测试 tags 端点
        if 'ollama.com' in url:
            test_url = f"{url}/api/tags"
        elif '11434' in url:
            test_url = f"{url}/api/tags"
        elif '/v1' in url:
            test_url = url + "/models"
        else:
            test_url = url
        
        is_available = test_endpoint(test_url, timeout=8)
        results[section] = {
            "url": url,
            "test_url": test_url,
            "available": is_available,
            "config": config
        }
        
        status = "✅ 可用" if is_available else "❌ 不可用"
        print(f"   状态: {status}")
    
    # 生成报告
    unavailable = [name for name, result in results.items() if not result["available"]]
    
    print(f"\n" + "=" * 50)
    print(f"📋 审计结果:")
    print(f"不可用的配置 ({len(unavailable)}):")
    for name in unavailable:
        print(f"  - {name}: {results[name]['url']}")
    
    # 保存报告
    report_path = "/root/.openclaw/workspace/ai_agent/results/actual_config_audit.json"
    with open(report_path, 'w') as f:
        json.dump({
            "timestamp": "2026-04-25 21:25:00",
            "results": results,
            "unavailable": unavailable
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 报告已保存到: {report_path}")
    
    # 生成清理建议
    if unavailable:
        print(f"\n🧹 清理建议:")
        print("建议更新 /root/.openclaw/config/ollama.toml 文件，移除或注释以下不可用配置:")
        for name in unavailable:
            print(f"  [{name}]")
            for key, value in results[name]["config"].items():
                print(f"  {key} = \"{value}\"")

if __name__ == "__main__":
    main()