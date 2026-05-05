#!/bin/bash
# 验证所有别名链路完整性
# 用法: bash verify_links.sh
set -e
python3 -c "
import json
with open('/root/.openclaw/openclaw.json') as f:
    config = json.load(f)

all_ok = True
print('=== 别名链路验证 ===')
for full_path, info in config['agents']['defaults']['models'].items():
    if 'alias' not in info:
        continue
    alias = info['alias']
    parts = full_path.split('/')
    provider_name = parts[0]
    model_id = '/'.join(parts[1:])  # handle colons in model ids
    
    if provider_name not in config['models']['providers']:
        print(f'  ❌ {alias}: provider \"{provider_name}\" NOT FOUND!')
        all_ok = False
    else:
        provider = config['models']['providers'][provider_name]
        model_found = any(m['id'] == model_id for m in provider['models'])
        if model_found:
            reasoning = next((m.get('reasoning', False) for m in provider['models'] if m['id'] == model_id), False)
            print(f'  ✅ {alias:30s} → {full_path} (reasoning={reasoning})')
        else:
            print(f'  ❌ {alias}: model \"{model_id}\" NOT in provider \"{provider_name}\"!')
            all_ok = False

print()
if all_ok:
    print('✅ 所有别名链路验证通过！')
else:
    print('❌ 存在错误链路，请修正！')
    exit(1)
"
