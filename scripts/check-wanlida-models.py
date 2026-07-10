import json
d = json.load(open('/home/ubuntu/.openclaw/agents/main/agent/models.json'))
for p in ['gateway-proxy','zhangtuo-ai-main']:
    if p in d.get('providers',{}):
        models = d['providers'][p].get('models',[])
        print(f'{p}: {[m["id"] for m in models[:5]]}')
