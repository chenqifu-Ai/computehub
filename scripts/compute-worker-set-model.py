import json
path = '/home/ubuntu/.openclaw/openclaw.json'
with open(path) as f:
    d = json.load(f)
d.setdefault('agent', {})['model'] = 'zhangtuo-ai-main/qwen3.6-35b'
with open(path, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print('Model set OK')
