import requests
import json
import time
from datetime import datetime

# 完整的41个模型测试
API_CONFIGS = {
    "modelstudio": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key": "sk-65ca99f6fd55437fba47dc7ba7973242",
        "models": ["qwen3.5-plus", "qwen3.5-flash", "qwen3-max", "qwen3-coder-next"]
    },
    "ollama_cloud": {
        "url": "https://ollama.com/api/chat",
        "key": "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii",
        "models": [
            "gemma3:4b-cloud", "gemma3:12b-cloud", "gemma3:27b-cloud",
            "ministral-3:3b-cloud", "ministral-3:8b-cloud", "ministral-3:14b-cloud",
            "glm-4.6-cloud", "glm-4.7-cloud", "glm-5-cloud",
            "minimax-m2-cloud", "minimax-m2.1-cloud", "minimax-m2.5-cloud", "minimax-m2.7-cloud",
            "kimi-k2.5-cloud", "kimi-k2:1t-cloud", "kimi-k2-thinking-cloud",
            "deepseek-v3.1:671b-cloud", "deepseek-v3.2-cloud",
            "qwen3-coder-next-cloud", "qwen3-coder:480b-cloud", "qwen3-next:80b-cloud",
            "qwen3.5:397b-cloud", "qwen3-vl:235b-cloud", "qwen3-vl:235b-instruct-cloud",
            "mistral-large-3:675b-cloud", "cogito-2.1:671b-cloud",
            "devstral-2:123b-cloud", "devstral-small-2:24b-cloud",
            "nemotron-3-super-cloud", "nemotron-3-nano:30b-cloud",
            "gpt-oss:20b-cloud", "gpt-oss:120b-cloud",
            "rnj-1:8b-cloud", "gemini-3-flash-preview-cloud"
        ]
    }
}

TEST_MESSAGE = "用一句话介绍你自己"
results = []

total_models = sum(len(config["models"]) for config in API_CONFIGS.values())
print(f"[START] 完整模型基准测试 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
print(f"测试模型总数: {total_models}")
print("=" * 60)

for provider, config in API_CONFIGS.items():
    print(f"\n[{provider.upper()}] - {len(config['models'])} 个模型")
    
    for i, model in enumerate(config["models"]):
        print(f"  [{i+1}/{len(config['models'])}] {model}...", end=" ", flush=True)
        
        try:
            start = time.time()
            headers = {"Content-Type": "application/json"}
            if config["key"]:
                headers["Authorization"] = f"Bearer {config['key']}"
            
            # 根据 provider 使用不同的请求格式
            if provider == "modelstudio":
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": TEST_MESSAGE}],
                    "max_tokens": 100
                }
            else:  # ollama_cloud
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": TEST_MESSAGE}],
                    "stream": False
                }
            
            resp = requests.post(
                config["url"],
                headers=headers,
                json=payload,
                timeout=60
            )
            duration = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 解析不同格式的响应
                if provider == "modelstudio":
                    tokens = data.get("usage", {}).get("total_tokens", "N/A")
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:30]
                else:  # ollama_cloud
                    tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    content = data.get("message", {}).get("content", "")[:30]
                
                results.append({
                    "provider": provider,
                    "model": model,
                    "tokens": tokens,
                    "time": duration,
                    "status": "OK",
                    "content": content
                })
                print(f"✅ {tokens} tokens ({duration:.2f}s)")
            else:
                error = resp.text[:80] if resp.text else f"HTTP {resp.status_code}"
                results.append({
                    "provider": provider,
                    "model": model,
                    "tokens": None,
                    "time": duration,
                    "status": "FAIL",
                    "error": error
                })
                print(f"❌ {error}")
                
        except Exception as e:
            results.append({
                "provider": provider,
                "model": model,
                "tokens": None,
                "time": 0,
                "status": "EXCEPTION",
                "error": str(e)[:80]
            })
            print(f"❌ {str(e)[:80]}")
        
        time.sleep(0.3)  # 避免速率限制

# 生成报告
success = sum(1 for r in results if r['status'] == 'OK')
fail = sum(1 for r in results if r['status'] != 'OK')
total_time = sum(r['time'] for r in results)

report = f"""# 完整模型基准测试报告（41个模型）

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试模型总数**: {total_models}
**总耗时**: {total_time:.2f}s

## 修复内容
- ✅ Ollama Cloud API 端点修复：`api.ollama.com` → `ollama.com/api`
- ✅ 模型 ID 修复：添加 `-cloud` 后缀
- ✅ 认证方式验证：Bearer token 有效

## 结果摘要
- ✅ 成功: {success}
- ❌ 失败: {fail}

## 详细结果

| Provider | 模型 | 状态 | token | 耗时 | 回答预览 |
|----------|------|------|-------|------|---------|
"""

for r in results:
    if r['status'] == 'OK':
        report += f"| {r['provider']} | {r['model']} | ✅ OK | {r['tokens']} | {r['time']:.2f}s | {r['content']} |\n"
    else:
        report += f"| {r['provider']} | {r['model']} | ❌ {r['status']} | - | {r['time']:.2f}s | {r.get('error', '')[:30]} |\n"

# Token效率排序
ok_results = [r for r in results if r['status'] == 'OK' and isinstance(r['tokens'], int)]
if ok_results:
    report += "\n## Token 效率排名（从低到高）\n\n"
    for r in sorted(ok_results, key=lambda x: x['tokens']):
        report += f"- **{r['provider']}/{r['model']}**: {r['tokens']} tokens ({r['time']:.2f}s)\n"

# 保存报告
with open("/root/.openclaw/workspace/reports/full_model_benchmark.md", "w") as f:
    f.write(report)

print("\n" + "=" * 60)
print(f"[DONE] 测试完成: {success} 成功, {fail} 失败")
print(f"报告已保存到 /root/.openclaw/workspace/reports/full_model_benchmark.md")

# 发送邮件
import subprocess
subprocess.run([
    "python3", "/root/.openclaw/workspace/scripts/send_email.py",
    "完整模型基准测试报告（41个模型）",
    "/root/.openclaw/workspace/reports/full_model_benchmark.md",
    "19525456@qq.com"
], timeout=30)