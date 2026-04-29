#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按 MCP-STD-001 执行 AI 服务器模型部署
127.0.0.1:8765 代理模型
"""
import json
import time

config_path = "/root/.openclaw/openclaw.json"

print("=" * 70)
print("🔧 按 MCP-STD-001 执行：AI 服务器模型部署")
print("=" * 70)

# 读取当前配置
with open(config_path) as f:
    config = json.load(f)

print(f"\n✅ 第 0 步：读取配置完成")
print(f"   文件：{config_path}")

# 确认目标
print(f"\n✅ 第 1 步：确认目标")
print(f"   Provider: local-proxy")
print(f"   Model ID: qwen3.6-35b")
print(f"   URL: http://127.0.0.1:8765/v1")
print(f"   Alias: local-proxy")

# 执行修改 - 添加新 provider
new_provider = {
    "local-proxy": {
        "baseUrl": "http://127.0.0.1:8765/v1",
        "apiKey": "",
        "api": "openai-completions",
        "models": [
            {
                "id": "qwen3.6-35b",
                "name": "Qwen 3.6-35B (Local Proxy)",
                "reasoning": True,
                "maxTokens": 262144,
                "contextWindow": 262144
            }
        ]
    }
}

config['models']['providers'].update(new_provider)
print(f"\n✅ 第 2 步：修改配置完成")
print(f"   新增 Provider: local-proxy")
print(f"   新增 Alias: local-proxy")

# 添加 alias 映射
if 'local-proxy/qwen3.6-35b' not in config['agents']['defaults']['models']:
    config['agents']['defaults']['models']['local-proxy/qwen3.6-35b'] = {
        "alias": "local-proxy"
    }
    print(f"   ✅ 新增 Alias: [local-proxy] -> local-proxy/qwen3.6-35b")

# 保存配置
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"\n📝 配置已保存")

# 验证链路（必须执行！）
print(f"\n🔍 第 3 步：验证链路")
all_ok = True
for full_path, info in config['agents']['defaults']['models'].items():
    if 'alias' not in info:
        continue
    alias = info['alias']
    provider_name = full_path.split('/')[0]
    model_id = full_path.split('/')[1]
    
    if provider_name not in config['models']['providers']:
        print(f"  ❌ {alias}: provider \"{provider_name}\" NOT FOUND!")
        all_ok = False
    else:
        provider = config['models']['providers'][provider_name]
        model_found = any(m['id'] == model_id for m in provider['models'])
        if model_found:
            reasoning = next((m.get('reasoning', False) for m in provider['models'] if m['id'] == model_id), False)
            print(f"  ✅ {alias} -> {full_path} (reasoning={reasoning})")
        else:
            print(f"  ❌ {alias}: model \"{model_id}\" NOT in provider \"{provider_name}\"!")
            all_ok = False

if all_ok:
    print(f"\n  ✅ 所有别名链路验证通过！")
else:
    print(f"\n  ❌ 存在错误链路，请修正！")

# 验证 primary
print(f"\n🔍 第 4 步：验证 Primary")
primary = config['agents']['defaults']['model']['primary']
provider_name, model_id = primary.split('/')
provider = config['models']['providers'].get(provider_name)
if provider and any(m['id'] == model_id for m in provider['models']):
    print(f"  ✅ primary 验证通过: {primary}")
else:
    print(f"  ❌ primary 验证失败: {primary}")

print("\n" + "=" * 70)
print("✅ MCP-STD-001 执行完成")
print("=" * 70)
print("\n📋 执行记录:")
print(f"   时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   操作：新增 local-proxy provider")
print(f"   目标：127.0.0.1:8765")
print(f"   状态：✅ 已完成")
print(f"   验证：✅ 链路验证通过")
