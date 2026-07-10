import json
d=json.load(open("/home/ubuntu/.openclaw/agents/main/agent/models.json"))
zm=d.get("providers",{}).get("zhangtuo-ai-main",{})
d.setdefault("providers",{})["gateway-proxy"]={"baseUrl":zm.get("baseUrl","https://ai.zhangtuokeji.top:9090/v1"),"apiKey":zm.get("apiKey",""),"api":"openai-completions","models":[{"id":"qwen3.6-35b","name":"qwen3.6-35b","reasoning":True}]}
json.dump(d,open("/home/ubuntu/.openclaw/agents/main/agent/models.json","w"),indent=2)
print("OK")
