#!/usr/bin/env python3
"""
deepseek-v4-flash 全面测试报告 v3
- max_tokens=2000 防止截断
- 回答在 reasoning 字段
- 修正校验：搜索推理文本中的答案关键词
"""
import json, re, time, urllib.request
from datetime import datetime

BASE_URL = "https://ollama.com/v1/chat/completions"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
MODEL = "deepseek-v4-flash"
MAX_T = 4000

results = {"test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "provider": "ollama-cloud",
           "model": MODEL, "base_url": BASE_URL, "categories": {}}
total_tests = total_pass = total_fail = 0

def call_api(messages, max_tokens=MAX_T, temperature=1.0):
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}, method="POST")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = time.time() - start
            body = json.loads(resp.read().decode("utf-8"))
            choice = body.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content", "")
            reasoning = msg.get("reasoning", "")
            actual = reasoning if reasoning else content
            finish = choice.get("finish_reason", "")
            tokens = body.get("usage", {}).get("total_tokens", 0)
            return True, actual, content, reasoning, tokens, elapsed, finish, body
    except Exception as e:
        return False, str(e), "", "", 0, time.time()-start, "", {}

def record(cat, name, passed, details=""):
    global total_tests, total_pass, total_fail
    total_tests += 1
    status = "✅ PASS" if passed else "❌ FAIL"
    if passed: total_pass += 1
    else: total_fail += 1
    results["categories"].setdefault(cat, []).append({"test": name, "status": status, "details": details})

def extract_answer(text, patterns):
    """从推理文本中提取答案（最后一个匹配）"""
    for pat in patterns:
        m = re.findall(pat, text, re.IGNORECASE)
        if m:
            return m[-1]
    return text.strip()[:80]

print("=" * 60)
print(f"  deepseek-v4-flash v3 测试 (max_tokens={MAX_T})")
print(f"  时间: {results['test_time']}")
print("=" * 60)

# 1. 连通性
print("\n[1/8] 连通性...")
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"hi"}], 50)
record("连通性", "基础连通", ok and len(text)>0, f"耗时{el:.1f}s, tokens:{tok}")

# 2. 基础功能
print("[2/8] 基础功能...")
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"你是谁？回答不超过10个字"}])
# 搜索回答模式
answer = extract_answer(text, [r'(?:答案|我是|是)[：:"]([\w\u4e00-\u9fff]+)', r'(?<=我)[是："]([\w\u4e00-\u9fff\u0041-\u005a]{0,15})(?:。|。|。|"|\s|$)'])
has_deepseek = "deepseek" in text.lower() or "深度" in text
passed = ok and has_deepseek
record("基础功能", "自我介绍", passed, f"含DeepSeek:{has_deepseek}, 答案:{text[:60]}")

ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"中国的首都是哪里？"}])
passed = ok and ("北京" in text or "beijing" in text.lower())
record("基础功能", "中文理解", passed, f"{text[:60]}")

ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"Capital of Japan? One word."}])
passed = ok and "tokyo" in text.lower()
record("基础功能", "英文理解", passed, f"{text[:60]}")

# 3. 速度
print("[3/8] 响应速度...")
times = []
for i in range(5):
    ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"Say hi"}], 10)
    if ok: times.append(el)
if times:
    avg = sum(times)/len(times)
    record("响应速度", "5次平均", True, f"平均{avg:.1f}s, 最快{min(times):.1f}s, 最慢{max(times):.1f}s")

# 4. 推理
print("[4/8] 推理能力...")
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"17×23=? 只回答数字"}])
# 搜索答案模式：答案：xxx / 等于xxx / =xxx
answer = extract_answer(text, [r'(?:答案|等于|结果为|所以)[：:=]?\s*(\d+)', r'(\d{2,4})\s*(?:等于|是|是\d*)'])
try:
    ans = int(answer.split()[0])
    passed = ans == 391
except:
    # 直接搜索391
    passed = ok and ("391" in text)
record("推理", "数学计算", passed, f"期望391, 含391:{('391' in text)}, 提取:{answer[:40]}")

ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"小明比小红高，小红比小刚高。谁最矮？"}])
passed = ok and ("刚" in text and ("矮" in text or "最" in text))
record("推理", "逻辑推理", passed, f"含刚:{('刚' in text)}, 含矮:{('矮' in text)}, {text[:60]}")

ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"水的化学式是什么？"}])
passed = ok and ("H2O" in text or "H₂O" in text)
record("推理", "常识推理", passed, f"含H2O:{('H2O' in text)}, {text[:60]}")

# 5. 代码
print("[5/8] 代码能力...")
ok, text, c, r, tok, el, fr, raw = call_api([
    {"role":"user","content":"写一个Python函数计算斐波那契数列第n项，用递归。只给代码不要解释"}
])
# 搜索代码模式
has_def = "def " in text or "def(" in text
has_return = "return " in text or "return(" in text
has_fib = "fib" in text.lower()
# 也可能输出代码块
has_code_block = "```python" in text or "```py" in text
passed = ok and (has_def and has_return) or (has_code_block and ("def" in text and "return" in text))
record("代码", "Python递归", passed, f"含def:{has_def}, 含return:{has_return}, 代码块:{has_code_block}")

ok, text, c, r, tok, el, fr, raw = call_api([
    {"role":"user","content":"写一个HTML页面标题Hello World。只给代码"}
])
passed = ok and ("<html" in text.lower() or "<!doctype" in text.lower()) and "Hello World" in text
record("代码", "HTML页面", passed, f"含html:{('html' in text.lower())}, Hello World:{('Hello World' in text)}")

# 6. 多语言
print("[6/8] 多语言...")
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"将'今天天气真好'翻译成英文"}])
passed = ok and ("weather" in text.lower() and ("nice" in text.lower() or "good" in text.lower()))
record("多语言", "中译英", passed, f"{text[:60]}")

ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"Translate 'Good morning' to Chinese"}])
passed = ok and ("早安" in text or "早上好" in text or "good morning" in text.lower())
record("多语言", "英译中", passed, f"{text[:60]}")

# 7. 创作
print("[7/8] 文本创作...")
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"写一首关于月亮的七言绝句"}])
# 搜索诗句模式（七言：每句7字，共4句）
lines = [l.strip() for l in text.split("\n") if len(l.strip()) == 7 and len(l.strip()) > 3]
has_poem = len(lines) >= 3  # 至少3行七言
# 或者搜索诗中常见意象
moon_words = "月" in text and ("光" in text or "影" in text or "明" in text)
passed = ok and (has_poem or moon_words) and len(text.strip()) >= 20
record("创作", "古诗创作", passed, f"诗行:{len(lines)}, 月意象:{moon_words}, 字数:{len(text.strip())}")

ok, text, c, r, tok, el, fr, raw = call_api([
    {"role":"user","content":"用一句话总结：AI是计算机科学分支研究智能本质"}
])
# 搜索总结模式
summary = extract_answer(text, [r'(?:总结|概括|简言之|一句话|精简为)[：:"](.{5,50})', r'(?:是)[：:"](.{5,50})'])
passed = ok and len(summary) < 60
record("创作", "文本摘要", passed, f"提取摘要长度:{len(summary)}, 摘要:{summary[:60]}")

# 8. 格式/上下文
print("[8/8] 格式与上下文...")
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"hi"}], 20)
record("响应格式", "content字段", bool(c), f"content空={'是' if not c else '否'}")
record("响应格式", "reasoning字段", bool(r), f"reasoning空={'是' if not r else '否'}")
record("响应格式", "finish_reason", True, f"{fr}")
record("响应格式", "token统计", True, f"total:{tok}")

ok, text, c, r, tok, el, fr, raw = call_api([
    {"role":"user","content":"我叫小王"},
    {"role":"assistant","content":"好的小王"},
    {"role":"user","content":"我名字是什么？"}
])
passed = ok and "小王" in text
record("上下文", "多轮记忆", passed, f"含小王:{('小王' in text)}, {text[:60]}")

# 特殊字符
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"测试!@#$%^&*()_+{}"}])
record("边界", "特殊字符", ok, f"回复长度:{len(text)}")

# 中文排版
ok, text, c, r, tok, el, fr, raw = call_api([{"role":"user","content":"请写一段中文，不要包含英文或数字"}])
passed = ok and len(text) >= 10 and not any(c.isdigit() for c in text)
record("边界", "纯中文输出", passed, f"长度:{len(text)}, 含数字:{any(c.isdigit() for c in text)}")

# ==================== 输出 ====================
print("\n" + "=" * 60)
print(f"  测试结果: {total_pass}/{total_tests} 通过 ({total_pass/total_tests*100:.0f}%)")
print("=" * 60)

for cat, tests in results["categories"].items():
    cp = sum(1 for t in tests if "✅" in t["status"])
    ct = len(tests)
    print(f"\n📁 {cat}: {cp}/{ct}")
    for t in tests:
        icon = "✅" if "✅" in t["status"] else "❌"
        print(f"  {icon} {t['test']}: {t['details']}")

path = "/root/.openclaw/workspace/ai_agent/results/deepseek_v4_flash_test_v3.json"
with open(path, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n📄 报告: {path}")
