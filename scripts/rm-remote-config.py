import json
path = '/home/ubuntu/.openclaw/openclaw.json'
with open(path) as f:
    d = json.load(f)
gw = d.get('gateway', {})
if 'remote' in gw:
    del gw['remote']
    d['gateway'] = gw
    with open(path, 'w') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print('REMOVED gateway.remote')
else:
    print('already removed')
