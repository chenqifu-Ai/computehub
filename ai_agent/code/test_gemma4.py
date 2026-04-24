import requests
import time
import json

API_URL = "http://58.23.129.98:8000/v1/chat/completions"
API_KEY = "sk-vmkohy18-34ga;sjd"
MODEL = "gemma-4-31b"

TEST_CASES = {
    "Logical Reasoning": {
        "prompt": "如果所有的 A 都是 B，并且有些 B 是 C，那么是否能得出结论：有些 A 必然是 C？请详细分析并给出结论。",
        "metric": "Correctness & Step-by-step analysis"
    },
    "Coding Ability": {
        "prompt": "请用 Python 实现一个简单的 LRU (Least Recently Used) 缓存类，要求 get 和 put 操作的时间复杂度均为 O(1)。请附带详细注释。",
        "metric": "Time Complexity & Syntax"
    },
    "Instruction Following": {
        "prompt": "请将以下信息转换为 JSON 格式：'小智是一个 AI 助手，爱好是学习，目前在上海工作'。要求：键名必须为英文 (name, hobby, location)，且不能包含任何解释性文字，只能输出 JSON 块。",
        "metric": "Format Accuracy"
    },
    "Creative Writing": {
        "prompt": "想象一个世界，在那里时间是可以用货币购买的，但代价是失去一段随机的记忆。请写一段 200 字左右的短篇小说片段，描述一个穷人决定买一小时时间的情景。",
        "metric": "Literary Quality"
    },
    "Summarization": {
        "prompt": "请总结量子纠缠的核心概念，要求面向非专业人士，使用比喻，且字数在 100 字以内。",
        "metric": "Clarity & Conciseness"
    }
}

def call_api(prompt):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        end_time = time.time()
        result = response.json()
        content = result['choices'][0]['message']['content']
        latency = end_time - start_time
        return content, latency
    except Exception as e:
        return f"Error: {str(e)}", 0

def main():
    results = []
    print(f"🚀 Starting comprehensive test for {MODEL}...")
    
    for dim, data in TEST_CASES.items():
        print(f"Testing {dim}...", end=" ", flush=True)
        content, latency = call_api(data['prompt'])
        results.append({
            "dimension": dim,
            "prompt": data['prompt'],
            "response": content,
            "latency": latency,
            "metric": data['metric']
        })
        print(f"Done ({latency:.2f}s)")

    # Save results to file
    output_path = "/root/.openclaw/workspace/ai_agent/results/gemma4_bench.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Gemma-4-31B Comprehensive Benchmark\n\n")
        f.write(f"- **Model**: {MODEL}\n")
        f.write(f"- **API**: {API_URL}\n")
        f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for r in results:
            f.write(f"## 📌 {r['dimension']}\n")
            f.write(f"**Prompt**: {r['prompt']}\n\n")
            f.write(f"**Metric**: {r['metric']} | **Latency**: {r['latency']:.2f}s\n\n")
            f.write(f"### Response:\n{r['response']}\n\n")
            f.write("---\n\n")
    
    print(f"✅ Test complete. Results saved to {output_path}")

if __name__ == "__main__":
    main()
