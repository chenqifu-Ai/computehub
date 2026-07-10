import json, os

# 下载 ECS 配置
import urllib.request
resp = urllib.request.urlopen('http://36.250.122.43:8282/api/v1/download?file=compute-worker-config.json')
ecs_config = json.loads(resp.read())

# 读取现有配置
oc_path = '/home/ubuntu/.openclaw/openclaw.json'
with open(oc_path) as f:
    local_config = json.load(f)

# 合并 models 和 auth
local_config['models'] = ecs_config['models']
local_config['auth'] = ecs_config['auth']

# 写回
with open(oc_path, 'w') as f:
    json.dump(local_config, f, indent=2, ensure_ascii=False)

print('Config merged OK')
