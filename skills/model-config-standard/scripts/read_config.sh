#!/bin/bash
# 读取当前 OpenClaw 模型配置
# 用法: bash read_config.sh
set -e
python3 -c "
import json
with open('/root/.openclaw/openclaw.json') as f:
    config = json.load(f)
providers = config['models']['providers']
aliases = config['agents']['defaults']['models']

print('=== Provider 列表 ===')
for name, prov in sorted(providers.items()):
    models = [m['id'] for m in prov.get('models', [])]
    base = prov.get('baseUrl', 'N/A')
    print(f'  {name:30s} {base:50s} → {models}')

print()
print('=== Alias 列表 ===')
for path, info in sorted(aliases.items()):
    alias = info.get('alias', path)
    print(f'  {alias:30s} → {path}')

print()
print(f'Primary: {config[\"agents\"][\"defaults\"][\"model\"][\"primary\"]}')
"
