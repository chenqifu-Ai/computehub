import json, urllib.request

data = json.dumps({
    model: zhangtuo-ai-main/qwen3.6-35b,
    messages: [{role: user, content: 你好，请用一句话介绍自己}]
}).encode()

req = urllib.request.Request(
    http://127.0.0.1:18789/api/chat/completions,
    data=data,
    headers={Content-Type: application/json},
    method=POST
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(fError: {e})
