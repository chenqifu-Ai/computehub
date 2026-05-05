#!/bin/bash
# 验证 primary 指向有效性
# 用法: bash verify_primary.sh
set -e
python3 -c "
import json
with open('/root/.openclaw/openclaw.json') as f:
    config = json.load(f)

primary = config['agents']['defaults']['model']['primary']
parts = primary.split('/', 1)
provider_name = parts[0]
model_id = parts[1] if len(parts) > 1 else ''

provider = config['models']['providers'].get(provider_name)
if provider:
    model_found = any(m['id'] == model_id for m in provider['models'])
    if model_found:
        print(f'✅ primary 验证通过: {primary}')
    else:
        print(f'❌ primary 验证失败: model \"{model_id}\" NOT in provider \"{provider_name}\"!')
        exit(1)
else:
    print(f'❌ primary 验证失败: provider \"{provider_name}\" NOT FOUND!')
    exit(1)
"
