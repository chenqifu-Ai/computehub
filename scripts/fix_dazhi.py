import json, os
models_path = "/home/ubuntu/.openclaw/agents/main/agent/models.json"
try:
    with open(models_path) as f:
        config = json.load(f)
except:
    config = {"providers": {}}
config["providers"]["gateway-proxy"] = {
    "baseUrl": "http://127.0.0.1:18789/v1",
    "api": "openai-completions",
    "models": [{"id": "qwen3.6-35b", "name": "qwen3.6-35b", "api": "openai-completions", "reasoning": False, "input": ["text"], "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}, "contextWindow": 128000, "maxTokens": 8192}]
}
config["primary"] = "gateway-proxy/qwen3.6-35b"
with open(models_path, "w") as f:
    json.dump(config, f, indent=2)
print("OK: models.json updated")
print("Primary:", config.get("primary"))
print("Providers:", list(config.get("providers", {}).keys()))
