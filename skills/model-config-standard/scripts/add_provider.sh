#!/bin/bash
# 标准化添加 Provider（含验证）
# 用法: bash add_provider.sh <provider_name> <model_id> <alias_name> <baseUrl> <apiKey>
# 例:   bash add_provider.sh qwen-8000 qwen3.6-35b "qwen-8000" "http://58.23.129.98:8000/v1" "sk-xxx"
set -e

if [ $# -lt 5 ]; then
    echo "用法: bash add_provider.sh <provider_name> <model_id> <alias_name> <baseUrl> <apiKey>"
    exit 1
fi

PROVIDER_NAME="$1"
MODEL_ID="$2"
ALIAS_NAME="$3"
BASE_URL="$4"
API_KEY="$5"

python3 -c "
import json, sys

with open('/root/.openclaw/openclaw.json') as f:
    config = json.load(f)

provider_name = '$PROVIDER_NAME'
model_id = '$MODEL_ID'
alias_name = '$ALIAS_NAME'
base_url = '$BASE_URL'
api_key = '$API_KEY'

# 添加/更新 provider
config['models']['providers'][provider_name] = {
    'baseUrl': base_url,
    'apiKey': api_key,
    'api': 'openai-completions',
    'models': [{
        'id': model_id,
        'name': f'{model_id} ({alias_name})',
        'api': 'openai-completions',
        'reasoning': True,
        'input': ['text'],
        'contextWindow': 256000,
        'maxTokens': 8192
    }]
}

# 添加别名
config['agents']['defaults']['models'][f'{provider_name}/{model_id}'] = {
    'alias': alias_name
}

with open('/root/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print(f'✅ Provider \"{provider_name}\" 已添加')
print(f'   baseUrl: {base_url}')
print(f'   model: {model_id}')
print(f'   alias: {alias_name}')
print()
print('⚠️  请运行 verify_links.sh 验证链路！')
"
