#!/usr/bin/env python3
"""
deepseek-v4-flash 全面测试报告
Provider: ollama-cloud | Model: deepseek-v4-flash
Base URL: https://ollama.com/v1 (注意：api.ollama.com 会 301)
"""
import json, time, urllib.request, urllib.error
from datetime import datetime

BASE_URL = "https://ollama.com/v1/chat/completions"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
MODEL = "deepseek-v4-flash"

results = {
    "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "provider": "ollama-cloud",
    "model": MODEL,
    "base_url": BASE_URL,
    "categories": {},
    "global_findings": []
}
total_tests = 0
total_pass = 0
total_fail = 0

def call_api(messages, max_tokens=200, temperature=1.0):
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}, method="POST")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.time() - start
            body = json.loads(resp.read().decode("utf-8"))
            choice = body.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content", "")
            reasoning = msg.get("reasoning", "")
            # deepseek-v4-flash 把回答放在 reasoning 字段！
            actual_text = reasoning if reasoning else content
            finish_reason = choice.get("finish_reason", "")
            usage = body.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            return True, actual_text, content, reasoning, total_tokens, elapsed, finish_reason, body
    except Exception as e:
        elapsed = time.time() - start
        return False, str(e), "", "", 0, elapsed, "", {}

def record(cat, name, passed, details=""):
    global total_tests, total_pass, total_fail
    total_tests += 1
    status = "✅ PASS" if passed else "❌ FAIL"
    if passed: total_pass += 1
    else: total_fail += 1
    results["categories"].setdefault(cat, []).append({"test": name, "status": status, "details": details})

print("=" * 60)
print("  deepseek-v4-flash 全面测试报告")
print(f"  时间: {results['test_time']}")
print("=" * 60)

# ==================== 1. 连通性 ====================
print("\n[1/8] 连通性与基础功能...")

ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "hi"}], max_tokens=50
)
passed = ok and len(text) > 0
record("连通性", "基础连通", passed, f"耗时 {elapsed:.1f}s")
if not ok:
    print(f"  ❌ 失败: {text}")
    with open("/root/.openclaw/workspace/ai_agent/results/deepseek_v4_flash_test.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("报告已保存（仅连通性测试）")
    exit(0)

# 基础对话
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "你是谁？回答不超过15个字"}], max_tokens=30
)
passed = ok and len(text.strip()) <= 20
record("基础功能", "自我介绍", passed, f"长度:{len(text.strip())}, 回复: {text[:100]}")

# 中文理解
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "中国的首都是哪里？"}], max_tokens=30
)
passed = ok and "北京" in text
record("基础功能", "中文理解", passed, f"{text[:100]}")

# 英文理解
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "Capital of France?"}], max_tokens=20
)
passed = ok and "paris" in text.lower()
record("基础功能", "英文理解", passed, f"{text[:100]}")

# ==================== 2. 响应速度 ====================
print("\n[2/8] 响应速度...")
times = []
for i in range(5):
    ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
        [{"role": "user", "content": "Say hi in 3 words"}], max_tokens=15
    )
    if ok: times.append(elapsed)

if times:
    avg = sum(times)/len(times)
    record("响应速度", "5次平均", True, f"平均{avg:.1f}s, 最快{min(times):.1f}s, 最慢{max(times):.1f}s")
else:
    record("响应速度", "5次平均", False, "全部失败")

# ==================== 3. 推理能力 ====================
print("\n[3/8] 推理能力...")

# 数学
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "17×23=? 只回答数字"}], max_tokens=15
)
try:
    answer = int(text.strip().split()[0])
    passed = answer == 391
except: passed = False
record("推理", "数学计算", passed, f"期望391, 得到: {text.strip()[:30]}")

# 逻辑
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "小明比小红高，小红比小刚高。谁最矮？"}], max_tokens=30
)
passed = ok and "刚" in text
record("推理", "逻辑推理", passed, f"{text[:100]}")

# 常识
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "太阳从哪个方向升起？"}], max_tokens=20
)
passed = ok and "东" in text
record("推理", "常识推理", passed, f"{text[:100]}")

# ==================== 4. 代码能力 ====================
print("\n[4/8] 代码能力...")

# Python
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "写一个Python函数计算斐波那契数列第n项，用递归。只给代码，不要解释"}], max_tokens=250
)
passed = ok and "def" in text and "return" in text
record("代码", "Python递归", passed, f"长度:{len(text)}, 前80字:{text[:80]}")

# HTML
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "写一个最简单的HTML页面，标题Hello World。只给代码"}], max_tokens=150
)
passed = ok and "<html" in text.lower() and "Hello World" in text
record("代码", "HTML页面", passed, f"长度:{len(text)}")

# ==================== 5. 多语言 ====================
print("\n[5/8] 多语言...")

# 中译英
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "将'今天天气真好'翻译成英文"}], max_tokens=40
)
passed = ok and ("weather" in text.lower() or "fine" in text.lower())
record("多语言", "中译英", passed, f"{text[:100]}")

# 英文翻译
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "Translate 'Hello World' to Chinese"}], max_tokens=20
)
passed = ok and "你好" in text
record("多语言", "英译中", passed, f"{text[:100]}")

# ==================== 6. 文本创作 ====================
print("\n[6/8] 文本创作...")

# 诗歌
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "写一首关于春天的五言绝句"}], max_tokens=80
)
passed = ok and len(text.strip()) >= 10
record("创作", "古诗创作", passed, f"前80字:{text[:80]}")

# 摘要
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "用一句话总结：AI是计算机科学分支，研究智能本质并制造智能机器。"}], max_tokens=40
)
passed = ok and len(text.strip()) < 40
record("创作", "文本摘要", passed, f"{text[:100]}")

# ==================== 7. 响应格式 ====================
print("\n[7/8] 响应格式分析...")

ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "hi"}], max_tokens=10
)

# content字段检查
has_content = bool(content)
record("响应格式", "content字段", has_content, f"content为空={'否' if has_content else '是'}")

# reasoning字段检查
has_reasoning = bool(reason)
record("响应格式", "reasoning字段", has_reasoning, f"有推理内容={'是' if has_reasoning else '否'}")
if not has_reasoning and not has_content:
    results["global_findings"].append("⚠️ 核心问题: content和reasoning都为空，可能API返回格式异常")

# finish_reason
record("响应格式", "finish_reason", True, f"finish_reason: {finish}")

# 总tokens
record("响应格式", "token统计", True, f"total:{tokens}")

# ==================== 8. 上下文 ====================
print("\n[8/8] 上下文记忆...")

ok, text, content, reason, tokens, elapsed, finish, raw = call_api([
    {"role": "user", "content": "我叫小明"},
    {"role": "assistant", "content": "你好小明！"},
    {"role": "user", "content": "我刚才说了我叫什么？"}
], max_tokens=20)
passed = ok and "小明" in text
record("上下文", "多轮记忆", passed, f"{text[:100]}")

# 特殊字符
ok, text, content, reason, tokens, elapsed, finish, raw = call_api(
    [{"role": "user", "content": "测试特殊字符!@#$%^&*()_+"}], max_tokens=20
)
passed = ok
record("边界", "特殊字符", passed, f"回复: {text[:100]}")

# ==================== 输出报告 ====================
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

# 保存报告
report_path = "/root/.openclaw/workspace/ai_agent/results/deepseek_v4_flash_test.json"
with open(report_path, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n📄 JSON报告: {report_path}")
