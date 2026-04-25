#!/usr/bin/env python3
"""deepseek-v4-flash 快速测试 - 不要代码执行"""
import json, time, urllib.request
from datetime import datetime

BASE_URL = "https://ollama.com/v1/chat/completions"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
MODEL = "deepseek-v4-flash"
results = {"test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "provider": "ollama-cloud",
           "model": MODEL, "base_url": BASE_URL, "categories": {}}
total_tests = total_pass = total_fail = 0

def call(messages, max_tokens=1000):
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1}
    req = urllib.request.Request(BASE_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            e = time.time()-t0
            b = json.loads(r.read().decode())
            c = b["choices"][0]["message"]
            content = c.get("content","") or ""
            reason = c.get("reasoning","") or ""
            finish = b["choices"][0].get("finish_reason","")
            tok = b.get("usage",{}).get("total_tokens",0)
            return True, content, reason, tok, e, finish
    except Exception as ex:
        return False, "", "", 0, time.time()-t0, str(ex)[:60]

def record(cat, name, passed, details=""):
    global total_tests, total_pass, total_fail
    total_tests += 1
    status = "✅" if passed else "❌"
    if passed: total_pass += 1
    else: total_fail += 1
    results["categories"].setdefault(cat, []).append({"test":name,"status":status,"details":details})

print(f"  deepseek-v4-flash 快速测试 v5")

# 基础
for q,check in [("hi",""), ("你是谁？10字","deepseek"), ("中国首都？","北京"), ("Capital of Japan?","tokyo")]:
    ok,c,r,tok,el,fr = call([{"role":"user","content":q}], 100)
    a = c or r
    name = q[:15]
    record("基础", name, ok and len(a)>0 and (not check or check.lower() in a.lower()), f"{el:.1f}s")

# 速度
ts=[]
for i in range(3):
    ok,c,r,tok,el,fr = call([{"role":"user","content":"hi"}], 20)
    if ok: ts.append(el)
if ts: record("速度","3次",True,f"{sum(ts)/len(ts):.1f}s")

# 推理
for q,check in [("17×23=？","391"), ("小明>小红>小刚谁最矮","刚"), ("骰子和为7概率？分数","1/6")]:
    ok,c,r,tok,el,fr = call([{"role":"user","content":q}], 200)
    a = c or r
    record("推理", q[:10], ok and check in a, f"{check} in: {('yes' if check in a else 'no')}")

# 代码
for q,check in [("写Python斐波那契递归。只给代码","def"), ("写HTML标题Hello World","html"), ("写Python单例","__new__")]:
    ok,c,r,tok,el,fr = call([{"role":"user","content":q}], 500)
    a = c or r
    record("代码", q[:10], ok and check in a.lower(), f"{check} in: {('yes' if check in a.lower() else 'no')}")

# 多语言+上下文
ok,c,r,tok,el,fr = call([{"role":"user","content":"将'今天天气真好'翻译成英文"}])
record("多语言", "中译英", ok and "weather" in (c or r).lower())
ok,c,r,tok,el,fr = call([{"role":"user","content":"我叫小王"},{"role":"assistant","content":"好的"},{"role":"user","content":"我名字？"}])
record("上下文", "多轮记忆", ok and "小王" in (c or r))

# 输出
print(f"\n  结果: {total_pass}/{total_tests} ({total_pass/total_tests*100:.0f}%)")
for cat,tests in results["categories"].items():
    cp=sum(1 for t in tests if "✅" in t["status"])
    print(f"  {cat}: {cp}/{len(tests)}")
    for t in tests:
        print(f"    {t['status']} {t['test']}: {t['details']}")

path="/root/.openclaw/workspace/ai_agent/results/deepseek_v4_flash_test_v5.json"
with open(path,"w") as f: json.dump(results,f,indent=2,ensure_ascii=False)
print(f"\n📄 {path}")
