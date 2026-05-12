#!/usr/bin/env python3
"""
qwen36-backup/qwen3.6-35b 模型测试脚本
目标: http://58.23.129.98:8999/v1
Key: sk-E_Ta97lGlSDu3HZCSqiZbg
"""

import json
import time
import sys
from datetime import datetime

API_BASE = "http://58.23.129.98:8999/v1"
API_KEY = "sk-E_Ta97lGlSDu3HZCSqiZbg"
MODEL = "qwen3.6-35b"

HEADER = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

results = []

def run_test(name, messages, max_tokens=1024, temperature=0.7):
    """执行单轮对话测试"""
    url = f"{API_BASE}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    print(f"\n{'='*60}")
    print(f"📝 测试: {name}")
    print(f"{'='*60}")
    print(f"❓ 问题: {messages[-1]['content'][:100]}...")
    
    start = time.time()
    try:
        import http.client
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port if parsed.port else 80, timeout=120)
        conn.request("POST", parsed.path, body=json.dumps(payload), headers=HEADER)
        resp = conn.getresponse()
        data = resp.read().decode()
        elapsed = time.time() - start
        
        if resp.status == 200:
            result = json.loads(data)
            choice = result.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content", None)
            reasoning = msg.get("reasoning_content", "") or msg.get("reasoning", "")
            # qwen3.6-35b 备用：content 永远为 null，所有输出在 reasoning_content
            response_text = content if content else reasoning
            if not response_text:
                # 再试试 provider_specific_fields
                psf = msg.get("provider_specific_fields", {})
                response_text = psf.get("reasoning") or psf.get("reasoning_content", "")
            
            used_tokens = result.get("usage", {})
            input_tokens = used_tokens.get("prompt_tokens", 0)
            output_tokens = used_tokens.get("completion_tokens", 0)
            
            test_result = {
                "name": name,
                "status": "PASS",
                "response_time_s": round(elapsed, 2),
                "output_tokens": output_tokens,
                "has_content": bool(response_text.strip()),
                "has_reasoning": bool(reasoning.strip()),
                "response_preview": (response_text[:200].replace("\n", " ")) if response_text else "",
                "reasoning_preview": (reasoning[:300].replace("\n", " ")) if reasoning else "",
                "error": None,
            }
            
            print(f"\n✅ 状态: PASS")
            print(f"⏱ 耗时: {elapsed:.2f}s")
            print(f"📊 Tokens: 输入={input_tokens}, 输出={output_tokens}")
            print(f"🧠 有推理: {'是' if reasoning.strip() else '否'}")
            print(f"📝 回复预览: {test_result['response_preview'][:200]}")
            if reasoning.strip():
                print(f"💭 推理预览: {test_result['reasoning_preview'][:300]}")
        else:
            test_result = {
                "name": name,
                "status": f"FAIL_HTTP_{resp.status}",
                "response_time_s": round(elapsed, 2),
                "output_tokens": 0,
                "has_content": False,
                "has_reasoning": False,
                "response_preview": "",
                "reasoning_preview": "",
                "error": data[:200],
            }
            print(f"\n❌ 状态: FAIL (HTTP {resp.status})")
            print(f"⏱ 耗时: {elapsed:.2f}s")
            print(f"💥 错误: {data[:200]}")
            
    except Exception as e:
        elapsed = time.time() - start
        test_result = {
            "name": name,
            "status": f"FAIL_EXCEPTION",
            "response_time_s": round(elapsed, 2),
            "output_tokens": 0,
            "has_content": False,
            "has_reasoning": False,
            "response_preview": "",
            "reasoning_preview": "",
            "error": str(e),
        }
        print(f"\n❌ 状态: FAIL")
        print(f"⏱ 耗时: {elapsed:.2f}s")
        print(f"💥 异常: {e}")
    
    results.append(test_result)
    return test_result


# ==================== 测试用例 ====================

print("╔══════════════════════════════════════════════════╗")
print("║  qwen3.6-35b (备用) 模型测试报告               ║")
print(f"║  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("╚══════════════════════════════════════════════════╝")

# 1. 连通性测试
print("\n" + "🔌" * 30)
print("测试 1/7: 连通性 (模型列表)")
try:
    import http.client
    from urllib.parse import urlparse
    parsed = urlparse(f"{API_BASE}/models")
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port if parsed.port else 80, timeout=10)
    conn.request("GET", parsed.path, headers={"Authorization": f"Bearer {API_KEY}"})
    resp = conn.getresponse()
    data = resp.read().decode()
    elapsed = time.time() - time.time()
    models = json.loads(data)
    print(f"✅ 连通 OK - 发现 {len(models.get('data',[]))} 个模型")
    for m in models.get("data", []):
        print(f"   - {m['id']} (owner: {m.get('owned_by','?')})")
except Exception as e:
    print(f"❌ 连通失败: {e}")

# 2. 基础常识
run_test(
    "基础常识",
    [{"role": "user", "content": "中国的首都是哪里？请简短回答。"}],
    max_tokens=50,
    temperature=0.3,
)

# 3. 数学计算
run_test(
    "数学计算",
    [{"role": "user", "content": "17 × 23 = ? 请展示计算过程。"}],
    max_tokens=200,
    temperature=0.3,
)

# 4. 代码生成
run_test(
    "代码生成 (Python)",
    [{"role": "user", "content": "写一个 Python 函数，用快速排序算法排序一个整数列表，要求有注释。"}],
    max_tokens=500,
    temperature=0.3,
)

# 5. 长文本摘要
long_text = f"""{datetime.now().strftime('%Y-%m-%d')} 工作记录：\n\n""" + "\n".join([
    f"上午 9:00 - 11:00: 完成了 ComputeHub v0.7.5 版本的全平台编译（5 平台 × 3 组件 = 15 个二进制），"
    f"包括 linux-amd64、linux-arm64、darwin-amd64、darwin-arm64、windows-amd64。"
    f"Gateway 和 Worker 组件编译全部通过，但 TUI 组件在 proot 环境下出现 SIGSYS 崩溃（seccomp 限制）。",
    f"下午 14:00 - 16:00: 在 192.168.2.140 上测试了 ComputeHub 集群（3 节点：fedora-node-140、cqf-worker-22、worker-189-1）。"
    f"发现 worker-189-1 运行在 Termux proot 环境下，导致 TUI 编译任务失败。"
    f"编写了《多平台节点能力管理规划》文档，提出三层方案解决此问题。",
    f"晚上 18:00 - 19:00: 与老大讨论了节点能力感知调度方案，计划分三个 sprint 实施。"
    f"完成了 v0.7.5 版本的代码提交（3 个 commit）。",
    f"\n系统状态：磁盘 90G 剩余，内存使用正常，模型切换正常。",
]) * 15  # 扩展成较长文本

run_test(
    "长文本摘要",
    [{"role": "user", "content": f"请总结以下工作记录的主要内容，包括：1) 上午完成了什么 2) 下午做了什么 3) 遇到了什么问题 4) 当前系统状态\n\n{long_text}"}],
    max_tokens=300,
    temperature=0.7,
)

# 6. 创意写作
run_test(
    "创意写作",
    [{"role": "user", "content": "用两句话写一个关于 AI 和人类的微型科幻故事。"}],
    max_tokens=200,
    temperature=0.9,
)

# 7. 中文理解
run_test(
    "中文理解",
    [{"role": "user", "content": "请解释成语 '胸有成竹' 的含义，并举一个日常生活中的例子。"}],
    max_tokens=300,
    temperature=0.7,
)

# ==================== 汇总报告 ====================
print("\n\n")
print("╔══════════════════════════════════════════════════╗")
print("║                    测试总结                      ║")
print("╚══════════════════════════════════════════════════╝")

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] != "PASS")
total_time = sum(r["response_time_s"] for r in results)

print(f"\n📊 测试总数: {len(results)}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"⏱ 总耗时: {total_time:.2f}s")
print(f"⚡ 平均响应: {total_time/len(results):.2f}s")

print(f"\n{'─'*60}")
print(f"{'序号':<4} {'测试名称':<20} {'结果':<10} {'耗时':>8}")
print(f"{'─'*60}")
for i, r in enumerate(results, 1):
    status_icon = "✅" if r["status"] == "PASS" else "❌"
    print(f"{i:<4} {r['name']:<20} {status_icon} {r['status']:<15} {r['response_time_s']:>6.2f}s")
print(f"{'─'*60}")

for r in results:
    print(f"\n📝 {r['name']}:")
    print(f"   状态: {r['status']}")
    print(f"   耗时: {r['response_time_s']}s")
    print(f"   输出: {r['output_tokens']} tokens")
    if r["status"] == "PASS":
        print(f"   有推理: {'是' if r['has_reasoning'] else '否'}")
        if r["has_reasoning"]:
            print(f"   推理: {r['reasoning_preview'][:200]}")
        print(f"   回复: {r['response_preview'][:200]}")
    else:
        print(f"   错误: {r['error'][:200]}")

# 保存报告
report = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "model": MODEL,
    "api_base": API_BASE,
    "total": len(results),
    "passed": passed,
    "failed": failed,
    "total_time_s": round(total_time, 2),
    "avg_response_s": round(total_time / len(results), 2),
    "tests": results,
}

report_path = "/root/.openclaw/workspace/ai_agent/results/qwen36_backup_test_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"\n📄 报告已保存: {report_path}")

# 如果测试成功，输出一个总结给 AI 用
if passed == len(results):
    print("\n🎉 全部测试通过！")
else:
    print(f"\n⚠️ 有 {failed} 项失败，详情见上方。")
