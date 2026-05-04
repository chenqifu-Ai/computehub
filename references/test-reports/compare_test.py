import requests
import json

# Configuration
GEMMA_URL = "http://58.23.129.98:8000/v1/chat/completions"
GEMMA_KEY = "sk-vmkohy18-34ga;sjd"
DS_URL = "https://api.ollama.com/v1/chat/completions"
DS_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

PROMPT = "Solve this puzzle: There are three boxes. One contains gold, one contains silver, and one is empty. Box 1 says: 'The gold is in Box 2.' Box 2 says: 'This box is empty.' Box 3 says: 'The gold is in this box.' Only one statement is true. Which box contains the gold? Respond strictly in JSON format: {\"answer\": \"Box X\", \"reasoning\": \"...\"}"

def test_model(name, url, key, model_id):
    print(f"Testing {name}...")
    try:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = {"model": model_id, "messages": [{"role": "user", "content": PROMPT}], "stream": False}
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "No content")
    except Exception as e:
        return f"Error: {str(e)}"

gemma_res = test_model("Gemma-4-31B", GEMMA_URL, GEMMA_KEY, "gemma-4-31b")
ds_res = test_model("DeepSeek-V3.1", DS_URL, DS_KEY, "deepseek-v3.1:671b")

print("\n=== RESULTS ===")
print(f"GEMMA-4-31B:\n{gemma_res}\n")
print(f"DEEPSEEK-V3.1:\n{ds_res}")
