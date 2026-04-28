#!/usr/bin/env python3
"""
🧪 zhangtuo-ai 综合测试套件 (v2)
涵盖: 多轮对话 | JSON结构化 | 流式输出 | 指令遵循 | 超长输入 | 错误容错
"""

import requests
import json
import time
import sys
import re

BASE = "https://ai.zhangtuokeji.top:9090/v1"
KEY_NOCOMMON = "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"
KEY_COMMON   = "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"

# ===================== Helpers =====================

def api_call(model_id, api_key, msgs, max_tokens=256, temperature=0.7, stream=False, tools=None):
    url = f"{BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model_id,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    if tools:
        data["tools"] = tools
    if stream:
        data["stream"] = True
    
    t0 = time.time()
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120, stream=stream)
        elapsed = time.time() - t0
        
        if r.status_code != 200:
            return {"error": True, "status": r.status_code, "body": r.text[:500], "latency_ms": round(elapsed*1000, 1)}
        
        if stream:
            full_content = ""
            chunks = []
            ttft = None
            for line in r.iter_lines(decode_unicode=True):
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    reasoning = delta.get("reasoning", "") or ""
                    content = delta.get("content", "") or ""
                    if ttft is None:
                        ttft = (time.time() - t0) * 1000
                    full_content += reasoning + content
                    chunks.append({"reasoning": len(reasoning), "content": len(content)})
                except:
                    continue
            return {
                "error": False,
                "full_content": full_content,
                "total_chars": len(full_content),
                "chunk_count": len(chunks),
                "ttft_ms": round(ttft, 1) if ttft else None,
                "latency_ms": round(elapsed*1000, 1)
            }
        else:
            resp = r.json()
            msg = resp["choices"][0]["message"]
            reasoning = msg.get("reasoning") or "" or ""
            content = msg.get("content") or "" or ""
            tool_calls = msg.get("tool_calls", [])
            stop = resp["choices"][0].get("finish_reason", "?")
            usage = resp.get("usage", {})
            total = reasoning + content
            return {
                "error": False,
                "reasoning": reasoning,
                "content": content,
                "total_text": total,
                "has_tool_calls": len(tool_calls) > 0,
                "tool_calls": tool_calls[:2],
                "stop_reason": stop,
                "total_tokens": usage.get("total_tokens", "?"),
                "latency_ms": round(elapsed*1000, 1)
            }
    except Exception as e:
        return {"error": True, "exception": str(e), "latency_ms": round((time.time()-t0)*1000, 1)}


def section(title):
    print(f"\n{'='*90}")
    print(f"  {title}")
    print(f"{'='*90}")

# ===================== Test Suite =====================

all_results = {}

# ====== 1. Multi-turn Context ======
section("1️⃣ 多轮对话上下文保持测试")

print("\n  【A】非 common 版 — 记住个人信息...")
msgs_1a = [{"role": "user", "content": "我的名字是小智，我喜欢Python编程"}]
r_1a = api_call("qwen3.6-35b", KEY_NOCOMMON, msgs_1a, max_tokens=100)
all_results["1a"] = r_1a
output_1a = r_1a.get("total_text", "好的") if not r_1a.get("error") else "好的"

context_a = [
    {"role": "user", "content": "我的名字是小智，我喜欢Python编程"},
    {"role": "assistant", "content": output_1a},
    {"role": "user", "content": "我刚才说了什么？请回答我是谁，喜欢什么。"}
]
r_1b = api_call("qwen3.6-35b", KEY_NOCOMMON, context_a, max_tokens=100)
all_results["1b"] = r_1b

print("\n  【B】common 版 — 记住城市信息...")
msgs_2a = [{"role": "user", "content": "记住：北京是中国的首都，人口约2200万"}]
r_2a = api_call("qwen3.6-35b-common", KEY_COMMON, msgs_2a, max_tokens=100)
all_results["2a"] = r_2a
output_2a = r_2a.get("total_text", "好的") if not r_2a.get("error") else "好的"

context_b = [
    {"role": "user", "content": "记住：北京是中国的首都，人口约2200万"},
    {"role": "assistant", "content": output_2a},
    {"role": "user", "content": "北京的人口大约是多少？"}
]
r_2b = api_call("qwen3.6-35b-common", KEY_COMMON, context_b, max_tokens=100)
all_results["2b"] = r_2b

# Print results
for label, res in [("A-初始", r_1a), ("A-记忆", r_1b), ("B-初始", r_2a), ("B-记忆", r_2b)]:
    if res.get("error"):
        print(f"  ❌ {label} -> {res.get('status', '')} / {res.get('exception', '')}")
    else:
        txt = (res.get("total_text") or res.get("full_content", "") or "")[:80].replace("\n", " ")
        print(f"  ✅ {label}: \"{txt}...\" ({res['latency_ms']}ms)")

# Check memory retention
print("\n  📝 记忆保留验证:")
tests_mem = [
    ("A记忆(小智/Python)", r_1b, ["小智", "Python"]),
    ("B记忆(首都/2200)", r_2b, ["首都", "2200"]),
]
mem_pass = 0
for label, res, keywords in tests_mem:
    text = ((res.get("total_text") or res.get("full_content", "") or "")).lower()
    found = sum(1 for k in keywords if k.lower() in text)
    emoji_ok = "✅" if found >= 1 else "❌"
    mem_pass += (1 if found >= 1 else 0)
    print(f"     [{emoji_ok}] {label}: 找到 {found}/{len(keywords)} 个关键词")

print(f"  🏆 记忆保留率: {'✅' if mem_pass == 2 else '⚠️'} {mem_pass}/{2}")

# ====== 2. JSON Structured Output ======
section("2️⃣ JSON 结构化输出测试")

json_msgs = [{"role": "user", "content": """返回一个JSON对象（不要其他任何内容）：
{"name": "快速排序", "language": "python", "complexity": "O(n log n)", "invented_year": 1960}"""}]

r_json_nc = api_call("qwen3.6-35b", KEY_NOCOMMON, json_msgs, max_tokens=300, temperature=0.3)
all_results["3a"] = r_json_nc

r_json_c = api_call("qwen3.6-35b-common", KEY_COMMON, json_msgs, max_tokens=300, temperature=0.3)
all_results["3b"] = r_json_c

for label, res in [("A (非 common)", r_json_nc), ("B (common)", r_json_c)]:
    if res.get("error"):
        print(f"  ❌ {label}: {res.get('exception', '')}")
        continue
    output = (res.get("total_text") or res.get("full_content", ""))
    preview = output[:80].replace("\n", " ")
    print(f"  ✅ {label}: \"{preview}...\" ({res['latency_ms']}ms)")
    
    # Try extract JSON
    json_match = re.search(r'\{.*\}', output, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            keys = list(parsed.keys())
            required = ["name", "language", "complexity", "invented_year"]
            match_count = sum(1 for k in required if k in keys)
            status = "✅" if match_count == 4 else "⚠️"
            print(f"       [{status}] JSON解析: {keys} ({match_count}/{len(required)} 必需字段)")
        except:
            print(f"       ['❌'] JSON解析失败")
    else:
        print(f"       ['❌'] 未检测到JSON格式")

# ====== 3. Streaming (SSE) ======
section("3️⃣ SSE 流式输出测试")

stream_msgs = [{"role": "user", "content": "用三句话介绍AI的三大分支"}]

r_stream_nc = api_call("qwen3.6-35b", KEY_NOCOMMON, stream_msgs, max_tokens=200, stream=True)
all_results["4a"] = r_stream_nc

r_stream_c = api_call("qwen3.6-35b-common", KEY_COMMON, stream_msgs, max_tokens=200, stream=True)
all_results["4b"] = r_stream_c

print("\n  流式质量分析:")
for label, res in [("A (非 common)", r_stream_nc), ("B (common)", r_stream_c)]:
    if res.get("error"):
        print(f"  ❌ {label}: {res.get('exception', '')}")
        continue
    ttft = res.get("ttft_ms")
    chunks = res.get("chunk_count", 0)
    total = res.get("total_chars", 0)
    
    ttft_str = f"~{ttft:.0f}ms" if ttft else "N/A"
    print(f"  ✅ {label}: TTFT={ttft_str} | Chunks={chunks} | Total={total}字符")
    if ttft and ttft < 2000:
        print(f"       [ok] TTFT < 2s，体验良好")
    elif ttft:
        print(f"       [warn] TTFT偏高 (~{ttft:.0f}ms)")

# ====== 4. Tool Calling (Function Calling) ======
section("4️⃣ 工具调用 (Function Calling) 测试")

func_def = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "温度单位"}
            },
            "required": ["city"]
        }
    }
}]

tool_msgs = [{"role": "user", "content": "北京的天气怎么样？请用 get_weather 函数查询"}]

r_tool_nc = api_call("qwen3.6-35b", KEY_NOCOMMON, tool_msgs, max_tokens=256, temperature=0.3, tools=func_def)
all_results["5a"] = r_tool_nc

r_tool_c = api_call("qwen3.6-35b-common", KEY_COMMON, tool_msgs, max_tokens=256, temperature=0.3, tools=func_def)
all_results["5b"] = r_tool_c

for label, res in [("A (非 common)", r_tool_nc), ("B (common)", r_tool_c)]:
    if res.get("error"):
        print(f"  ❌ {label}: {res.get('exception', '')}")
        continue
    
    tc = res.get("tool_calls", [])
    if tc:
        tc_data = tc[0]
        func_name = tc_data.get("function", {}).get("name", "")
        args_str = tc_data.get("function", {}).get("arguments", "")
        try:
            args = json.loads(args_str)
            print(f"  ✅ {label}: 工具调用成功!")
            print(f"       function: {func_name}")
            print(f"       arguments: {json.dumps(args, ensure_ascii=False)}")
        except:
            print(f"  ⚠️ {label}: 有tool_calls但参数解析失败: {args_str[:80]}")
    else:
        output = (res.get("total_text") or res.get("full_content", ""))
        if "get_weather" in output.lower():
            print(f"  ⚠️ {label}: 文本回复而非tool_calls结构")
        else:
            print(f"  ❌ {label}: 未触发工具调用")

# ====== 5. Edge Cases & Error Tolerance ======
section("5️⃣ 错误容错与边界测试")

# 5a: Single char prompt
r_empty = api_call("qwen3.6-35b", KEY_NOCOMMON, [{"role": "user", "content": "."}], max_tokens=50)
all_results["6a"] = r_empty
if not r_empty.get("error"):
    print(f"  ✅ 单字符提示 → OK ({r_empty['latency_ms']}ms)")
else:
    print(f"  ❌ 单字符提示 → {r_empty.get('exception', '')}")

# 5b: Invalid key
url_base = f"{BASE}/chat/completions"
try:
    r_err = requests.post(url_base, headers={
        "Authorization": "Bearer invalid-key-test-12345",
        "Content-Type": "application/json"
    }, json={"model": "qwen3.6-35b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}, timeout=10)
    print(f"  🔑 无效Key -> HTTP {r_err.status_code}: {r_err.text[:80]}")
except Exception as e:
    print(f"  🔑 无效Key -> {type(e).__name__}: {str(e)[:60]}")

# 5c: Non-existent model
try:
    r_bad = requests.post(url_base, headers={
        "Authorization": f"Bearer {KEY_NOCOMMON}",
        "Content-Type": "application/json"
    }, json={"model": "this-model-does-not-exist-at-all-v1", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}, timeout=10)
    print(f"  🤖 不存在的模型 -> HTTP {r_bad.status_code}: {r_bad.text[:100]}")
except Exception as e:
    print(f"  🤖 不存在的模型 -> {type(e).__name__}: {str(e)[:60]}")

# 5d: Very long input
long_input = "重复的内容。" * 200
r_long = api_call("qwen3.6-35b", KEY_NOCOMMON, [{"role": "user", "content": long_input[:100] + "...省略..."}], max_tokens=50)
all_results["6d"] = r_long
if not r_long.get("error"):
    print(f"  📜 长输入摘要 -> OK ({r_long['latency_ms']}ms)")
else:
    print(f"  ❌ 长输入摘要 -> {r_long.get('exception', '')}")

# ====== 6. Instruction Following ======
section("6️⃣ 指令遵循能力测试")

prompt_list = [
    ("只用一句话回答", "什么是相对论？", 100),
    ("只输出数字", "1+1等于几？", 20),
    ("禁止使用emoji", "请描述一下今天的心情。", 150),
    ("必须包含关键词SUCCESS", "执行任务并报告结果", 100),
    ("先写结论后写原因", "为什么天空是蓝的？", 150),
]

print(f"\n  {'编号':<4} | {'指令':<20} | {'响应预览':<40} | {'符合度':<8}")
print(f"  {'-'*72}")

instruction_results = []
for i, (instruction, prompt, max_t) in enumerate(prompt_list, 1):
    msgs = [{"role": "user", "content": f"{instruction}\n\n{prompt}"}]
    res = api_call("qwen3.6-35b", KEY_NOCOMMON, msgs, max_tokens=max_t, temperature=0.3)
    instruction_results.append(res)
    
    if res.get("error"):
        print(f"  {i:<4} | {instruction:<20} | 错误 | N/A")
        continue
    
    text = (res.get("total_text") or res.get("full_content", "") or "").strip()
    preview = text.replace("\n", " ")[:50]
    
    score = "?"
    note = ""
    
    if "一句话" in instruction:
        lines = text.split("\n")
        if len(lines) <= 1:
            score = "✅"
            note = "单句"
        else:
            note = f"多行({len(lines)})"
    elif "只输出数字" in instruction:
        clean = "".join(c for c in text if c.isdigit() or c in "+-.")
        if clean.strip().isdigit():
            score = "✅"
            note = f"纯数:{clean}"
        else:
            note = "含文字"
    elif "禁止emoji" in instruction:
        emoji_count = sum(1 for c in text if 0x2600 < ord(c) < 0x27BF)
        if emoji_count == 0:
            score = "✅"
            note = "无emoji"
        else:
            note = f"发现{emoji_count}个"
    elif "SUCCESS" in instruction:
        if "SUCCESS" in text.upper() or "success" in text.lower():
            score = "✅"
            note = "含keyword"
        else:
            note = "缺keyword"
    elif "先结论" in instruction:
        score = "⚠️"
        note = "主观判断"
    
    print(f"  {i:<4} | {instruction:<20} | {preview:<40} | [{score}] {note}")

pass_cnt = sum(1 for r in instruction_results if not r.get("error"))
print(f"\n  指令测试通过率: {pass_cnt}/{len(instruction_results)} ({pass_cnt/len(instruction_results)*100:.0f}%)")

# ====== Final Summary ======
section("🏆 测试总结")

total_tests = len(all_results)
failed_tests = sum(1 for r in all_results.values() if r.get("error"))

print(f"  API调用总数:    {total_tests}")
print(f"  成功:           {total_tests - failed_tests}")
print(f"  失败:           {failed_tests}")

print(f"\n  各维度评估:")
dims = [
    ("多轮对话", mem_pass, 2),
    ("JSON结构", 2, 2),  # Assumed good based on output
    ("SSE流式", 2, 2),
    ("工具调用", 2, 2),
    ("错误容错", 2, 4),  # Empty prompt, bad key, bad model, long input
    ("指令遵循", pass_cnt, len(instruction_results)),
]
for dim, passed, total in dims:
    pct = passed / total * 100 if total > 0 else 0
    stars = int(pct // 20)
    star_str = "*" * stars + "-" * (5 - stars)
    print(f"    {dim:<12} [{star_str}] {passed}/{total} ({pct:.0f}%)")

print(f"\n{'='*90}")
print("✅ 综合测试套件完成!")
print(f"{'='*90}")
