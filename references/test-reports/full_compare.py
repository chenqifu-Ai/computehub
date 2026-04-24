import requests
import json
import time

# Configuration
GEMMA_URL = "http://58.23.129.98:8000/v1/chat/completions"
GEMMA_KEY = "sk-vmkohy18-34ga;sjd"
DS_URL = "https://api.ollama.com/v1/chat/completions"
DS_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

# Complex Multi-Dimensional Test Cases
TEST_CASES = [
    {
        "name": "Logical Reasoning & JSON",
        "prompt": "A man has 5 daughters. Each daughter has a brother. How many children does the man have in total? Respond in JSON: {\"answer\": X, \"reasoning\": \"...\"}",
        "type": "logic"
    },
    {
        "name": "Coding & Optimization",
        "prompt": "Write a Python function to find the longest palindromic substring in a string. The solution must be O(n^2) or better. Provide only the code in a markdown block.",
        "type": "code"
    },
    {
        "name": "Nuance & Creativity",
        "prompt": "Explain the concept of 'Quantum Entanglement' to a 5-year-old using a metaphor about two magic socks. Keep it under 100 words.",
        "type": "creative"
    }
]

def call_model(name, url, key, model_id, prompt):
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = {"model": model_id, "messages": [{"role": "user", "content": prompt}], "stream": False}
        start_time = time.time()
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        latency = time.time() - start_time
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "No content")
            return {"status": "success", "content": content, "latency": latency}
        else:
            return {"status": "error", "error": f"HTTP {resp.status_code}", "latency": latency}
    except Exception as e:
        return {"status": "exception", "error": str(e), "latency": 0}

print(f"Starting Comparative Benchmark...\n")

results = {}
for case in TEST_CASES:
    print(f"Running {case['name']}...")
    g_res = call_model("Gemma", GEMMA_URL, GEMMA_KEY, "gemma-4-31b", case['prompt'])
    d_res = call_model("DeepSeek", DS_URL, DS_KEY, "deepseek-v3.1:671b", case['prompt'])
    results[case['name']] = {"Gemma": g_res, "DeepSeek": d_res}

print("\n" + "="*50)
print(f"{'Test Case':<<225} | {'Gemma (31B)':<<220} | {'DeepSeek (671B)':<<220}")
print("-" * 70)
for name, res in results.items():
    g_stat = "✅" if res['Gemma']['status'] == "success" else "❌"
    d_stat = "✅" if res['DeepSeek']['status'] == "success" else "❌"
    g_lat = f"{res['Gemma']['latency']:.2f}s" if res['Gemma']['status'] == "success" else "N/A"
    d_lat = f"{res['DeepSeek']['latency']:.2f}s" if res['DeepSeek']['status'] == "success" else "N/A"
    print(f"{name:<<225} | {g_stat} {g_lat:<<117} | {d_stat} {d_lat:<<117}")

print("\nDetailed Content Analysis:")
for name, res in results.items():
    print(f"\n--- {name} ---")
    print(f"Gemma: {res['Gemma'].get('content', res['Gemma'].get('error'))}")
    print(f"DeepSeek: {res['DeepSeek'].get('content', res['DeepSeek'].get('error'))}")
