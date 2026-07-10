import json, urllib.request
data = json.dumps({
    "content": "WANLIDA-GTW-001: wanlida-ubuntu Gateway修复经验。根因：ubuntu用户的models.json缺少gateway-proxy provider。修复：通过ComputeHub 8282提交base64编码Python脚本写入models.json，pkill重启Gateway。关键教训：多节点models.json必须同步，Gateway重启才能生效，wanlida-ubuntu只能通过8282中继管理。",
    "tags": ["gateway","wanlida-ubuntu","models.json","gateway-proxy","修复经验"],
    "source": "端智-阶段小结"
}).encode()
req = urllib.request.Request("http://127.0.0.1:8383/api/v1/memory/knowledge", data=data, headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=10)
print(resp.status, resp.read().decode()[:300])
