import json
d = json.load(open('/home/ubuntu/.openclaw/agents/main/agent/models.json'))
gw = d.get('providers',{}).get('gateway-proxy',{})
print('gateway-proxy models:')
for m in gw.get('models',[]):
    print(f'  {m["id"]}')
print()
print('zhangtuo-ai-main models:')
zm = d.get('providers',{}).get('zhangtuo-ai-main',{})
for m in zm.get('models',[]):
    print(f'  {m["id"]}')
