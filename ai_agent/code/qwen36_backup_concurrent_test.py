#!/usr/bin/env python3
"""
qwen36-backup 模型并发测试
端点: http://58.23.129.98:8999/v1
使用 concurrent.futures.ThreadPoolExecutor (标准库)

⚠️ 注意: 此模型 content 字段为 null，内容在 provider_specific_fields.reasoning 中
"""

import json
import time
import statistics
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE_URL = "http://58.23.129.98:8999/v1"
API_KEY = "sk-E_Ta97lGlSDu3HZCSqiZbg"
MODEL = "qwen3.6-35b"

PROMPTS = [
    "请简要介绍量子计算的基本原理，用100字以内回答",
    "写一首关于春天的五言绝句",
    "Python中列表推导式和map哪个更快？为什么？",
    "解释一下HTTP/3相比HTTP/2的改进",
    "用3句话概括《三体》的主要情节",
    "比较React和Vue的核心区别",
    "什么是零信任网络架构？",
    "解释Transformer的注意力机制",
    "Go和Rust在并发模型上的核心差异",
    "用比喻解释区块链是什么",
]

def extract_reply(body: dict) -> str:
    """从响应中提取回复内容（兼容 content=null 的模型）"""
    choice = body.get("choices", [{}])[0] if body.get("choices") else {}
    message = choice.get("message", {})
    
    # 1. 先尝试 content
    content = message.get("content", "")
    if content and content != "null" and content is not None:
        return content
    
    # 2. 尝试 reasoning
    reasoning = message.get("reasoning", "")
    if reasoning:
        return reasoning
    
    # 3. 尝试 provider_specific_fields.reasoning
    psvf = choice.get("provider_specific_fields", {})
    if psvf:
        rs = psvf.get("reasoning", "")
        if rs:
            return rs
        rc = psvf.get("reasoning_content", "")
        if rc:
            return rc
    
    # 4. 尝试 message.reasoning_content (直接嵌套)
    rc = message.get("reasoning_content", "")
    if rc:
        return rc
    
    return ""


def single_request(prompt: str, idx: int) -> dict:
    """发送单个请求"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,
    }).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )
    
    try:
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = time.monotonic() - start
            body = json.loads(resp.read().decode("utf-8"))
            
            reply = extract_reply(body)
            token_count = len(reply) if reply else 0
            
            usage = body.get("usage", {})
            return {
                "success": True,
                "idx": idx,
                "elapsed": elapsed,
                "tokens": token_count,
                "reply_tokens": usage.get("completion_tokens", token_count),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "tps": token_count / elapsed if elapsed > 0 else 0,
                "reply_preview": reply[:80],
            }
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "idx": idx, "elapsed": elapsed, "status": e.code, "error": body[:200]}
    except Exception as e:
        elapsed = time.monotonic() - start
        return {"success": False, "idx": idx, "elapsed": elapsed, "error": str(e)[:200]}


def run_test(concurrency: int, num_requests: int = 10):
    """运行并发测试"""
    prompts_to_use = (PROMPTS * (num_requests // len(PROMPTS) + 1))[:num_requests]
    
    print(f"\n{'='*70}")
    print(f"  qwen36-backup 并发测试  [{datetime.now().strftime('%H:%M:%S')}]")
    print(f"  并发数: {concurrency} | 请求数: {num_requests}")
    print(f"  端点: {BASE_URL}")
    print(f"  模型: qwen3.6-35b")
    print(f"{'='*70}")
    
    total_start = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(single_request, p, i): i
            for i, p in enumerate(prompts_to_use)
        }
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            r = future.result()
            results.append(r)
            if r["success"]:
                status = f"✅ {r['tokens']}tok {r['elapsed']:.2f}s"
            else:
                status = f"❌ {r.get('error','')}"
            print(f"  [{completed}/{num_requests}] #{r['idx']:2d}: {status}")
    
    total_elapsed = time.time() - total_start
    
    success = [r for r in results if r["success"]]
    fails = [r for r in results if not r["success"]]
    elapsed_list = [r["elapsed"] for r in success]
    token_list = [r["tokens"] for r in success]
    
    print(f"\n{'─'*70}")
    print(f"  测试结果")
    print(f"{'─'*70}")
    print(f"  总耗时:       {total_elapsed:.2f}s")
    print(f"  成功:         {len(success)} / {num_requests}")
    print(f"  失败:         {len(fails)}")
    if fails:
        for f in fails[:5]:
            status_code = f.get("status", "?")
            error_msg = f.get("error", "")
            print(f"    #{f['idx']}: HTTP {status_code}: {error_msg[:100]}")
    
    if elapsed_list:
        print(f"\n  延迟统计 (成功请求):")
        avg = statistics.mean(elapsed_list)
        median = statistics.median(elapsed_list)
        print(f"    平均:    {avg:.3f}s")
        print(f"    中位数:  {median:.3f}s")
        print(f"    最快:    {min(elapsed_list):.3f}s")
        print(f"    最慢:    {max(elapsed_list):.3f}s")
        if len(elapsed_list) > 1:
            print(f"    标准差:  {statistics.stdev(elapsed_list):.3f}s")
        
        avg_tokens = statistics.mean(token_list) if token_list else 0
        print(f"\n  输出内容:")
        print(f"    平均长度:  {avg_tokens:.0f} tokens")
        print(f"    总输出:    {sum(token_list)} tokens")
        
        print(f"\n  吞吐量:")
        print(f"    请求吞吐:  {len(success) / total_elapsed:.2f} req/s")
        tps_list = [r["tps"] for r in success]
        print(f"    平均TPS:   {statistics.mean(tps_list):.1f} tokens/s")
        print(f"    总TPS:     {sum(token_list) / total_elapsed:.1f} tokens/s")
        
        # 并发效率
        server_total = sum(elapsed_list)
        efficiency = server_total / total_elapsed if total_elapsed > 0 else 0
        print(f"\n  并发效率:")
        print(f"    服务器总时间: {server_total:.2f}s")
        print(f"    实际耗时:     {total_elapsed:.2f}s")
        print(f"    效率系数:     {efficiency:.2f}x (理论最大值={concurrency}x)")
        
        # 百分位
        sorted_e = sorted(elapsed_list)
        def pct(p):
            i = min(int(len(sorted_e) * p), len(sorted_e) - 1)
            return sorted_e[i]
        print(f"\n  延迟分布:")
        print(f"    P50: {pct(0.50):.3f}s")
        print(f"    P75: {pct(0.75):.3f}s")
        print(f"    P90: {pct(0.90):.3f}s")
        print(f"    P95: {pct(0.95):.3f}s")
        
        # 延迟与输出长度关系
        print(f"\n  延迟 vs 输出长度:")
        for r in sorted(success, key=lambda x: x["elapsed"]):
            bar_len = int(r["elapsed"] / max(elapsed_list) * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            print(f"    {r['elapsed']:6.2f}s {bar} {r['tokens']:3d}tok")
    
    print(f"{'='*70}")
    return {
        "concurrency": concurrency,
        "total": num_requests,
        "success": len(success),
        "fail": len(fails),
        "elapsed": total_elapsed,
        "avg_elapsed": statistics.mean(elapsed_list) if elapsed_list else 0,
        "req_per_sec": len(success) / total_elapsed if total_elapsed > 0 else 0,
        "avg_tps": statistics.mean([r["tps"] for r in success]) if success else 0,
        "avg_tokens": avg_tokens,
    }


def main():
    print(f"\n{'#' * 70}")
    print(f"  qwen3.6-35b (qwen36-backup) 并发压力测试")
    print(f"  服务器: http://58.23.129.98:8999/v1")
    print(f"  ⚠️  注意: content=null, 内容在 provider_specific_fields.reasoning")
    print(f"{'#' * 70}")
    
    results = []
    
    test_cases = [
        ("5并发 × 5请求",  5, 5),
        ("10并发 × 10请求", 10, 10),
        ("20并发 × 10请求", 20, 10),
        ("30并发 × 10请求", 30, 10),
        ("50并发 × 10请求", 50, 10),
        ("100并发 × 10请求", 100, 10),
    ]
    
    for label, conc, num in test_cases:
        r = run_test(conc, num)
        r["label"] = label
        results.append(r)
        time.sleep(0.5)
    
    # 最终汇总
    print(f"\n\n{'='*70}")
    print(f"  📊 汇总报告")
    print(f"{'='*70}")
    print(f"  {'场景':>15} | {'成功/总':>8} | {'总耗时':>8} | {'吞吐':>8} | {'平均延迟':>8} | {'TPS':>8} | {'平均长度':>8}")
    print(f"  {'─'*15} | {'─'*8} | {'─'*8} | {'─'*8} | {'─'*8} | {'─'*8} | {'─'*8}")
    
    for r in results:
        print(f"  {r['label']:>15} | {r['success']}/{r['total']:>6} | {r['elapsed']:>7.2f}s | {r['req_per_sec']:>7.2f}/s | {r['avg_elapsed']:>7.3f}s | {r['avg_tps']:>7.1f} tok/s | {r['avg_tokens']:>7.0f} tok")
    
    best_throughput = max(results, key=lambda r: r['req_per_sec'])
    best_tps = max(results, key=lambda r: r['avg_tps'])
    print(f"\n  最佳请求吞吐: {best_throughput['label']} ({best_throughput['req_per_sec']:.2f} req/s)")
    print(f"  最佳 Token 吞吐: {best_tps['label']} ({best_tps['avg_tps']:.1f} tok/s)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
