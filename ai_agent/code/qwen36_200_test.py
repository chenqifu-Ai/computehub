#!/usr/bin/env python3
"""qwen36-backup 200并发极限测试"""
import json, time, statistics, urllib.request, urllib.error
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

def extract_reply(body):
    choice = body.get("choices", [{}])[0] if body.get("choices") else {}
    message = choice.get("message", {})
    content = message.get("content", "")
    if content and content is not None and content != "null":
        return content
    reasoning = message.get("reasoning", "")
    if reasoning: return reasoning
    psvf = choice.get("provider_specific_fields", {})
    if psvf:
        rs = psvf.get("reasoning", "")
        if rs: return rs
        rc = psvf.get("reasoning_content", "")
        if rc: return rc
    rc = message.get("reasoning_content", "")
    if rc: return rc
    return ""

def single_request(prompt, idx):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512, "temperature": 0.7,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=payload, headers=headers, method="POST")
    try:
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = time.monotonic() - start
            body = json.loads(resp.read().decode("utf-8"))
            reply = extract_reply(body)
            token_count = len(reply)
            usage = body.get("usage", {})
            return {"success": True, "idx": idx, "elapsed": elapsed, "tokens": token_count,
                    "reply_tokens": usage.get("completion_tokens", token_count),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "tps": token_count / elapsed if elapsed > 0 else 0}
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "idx": idx, "elapsed": elapsed, "status": e.code, "error": body[:200]}
    except Exception as e:
        elapsed = time.monotonic() - start
        return {"success": False, "idx": idx, "elapsed": elapsed, "error": str(e)[:200]}

def main():
    print(f"\n{'#' * 70}")
    print(f"  ⚡⚡⚡ qwen3.6-35b 200并发地狱测试  [{datetime.now().strftime('%H:%M:%S')}]")
    print(f"  端点: {BASE_URL}  |  并发: 200  |  请求: 10")
    print(f"{'#' * 70}")
    
    num_requests = 10
    conc = 200
    prompts_to_use = (PROMPTS * (num_requests // len(PROMPTS) + 1))[:num_requests]
    
    total_start = time.time()
    results = []
    errors = []
    
    with ThreadPoolExecutor(max_workers=conc) as executor:
        futures = {executor.submit(single_request, p, i): i for i, p in enumerate(prompts_to_use)}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            r = future.result()
            results.append(r)
            if r["success"]:
                status = f"✅ {r['tokens']}tok {r['elapsed']:.2f}s"
            else:
                status = f"❌ {r.get('error','')}"
                errors.append(r)
            print(f"  [{completed:2d}/{num_requests}] #{r['idx']:2d}: {status}")
    
    total_elapsed = time.time() - total_start
    
    success = [r for r in results if r["success"]]
    fails = [r for r in results if not r["success"]]
    elapsed_list = [r["elapsed"] for r in success]
    token_list = [r["tokens"] for r in success]
    
    print(f"\n{'='*70}")
    print(f"  📊 200并发测试结果")
    print(f"{'='*70}")
    print(f"  总耗时:       {total_elapsed:.2f}s")
    print(f"  成功:         {len(success)} / {num_requests}")
    print(f"  失败:         {len(fails)}")
    if errors:
        for e in errors:
            sc = e.get("status", "?")
            em = e.get("error", "")[:150]
            print(f"    #{e['idx']}: HTTP {sc}: {em}")
    
    if elapsed_list:
        avg = statistics.mean(elapsed_list)
        median = statistics.median(elapsed_list)
        print(f"\n  延迟统计:")
        print(f"    平均:    {avg:.3f}s")
        print(f"    中位数:  {median:.3f}s")
        print(f"    最快:    {min(elapsed_list):.3f}s")
        print(f"    最慢:    {max(elapsed_list):.3f}s")
        if len(elapsed_list) > 1:
            print(f"    标准差:  {statistics.stdev(elapsed_list):.3f}s")
        
        print(f"\n  输出: 平均{statistics.mean(token_list):.0f}tok | 总计{sum(token_list)}tok")
        print(f"\n  吞吐量:")
        print(f"    请求吞吐:  {len(success) / total_elapsed:.2f} req/s")
        print(f"    平均TPS:   {statistics.mean([r['tps'] for r in success]):.1f} tokens/s")
        print(f"    总TPS:     {sum(token_list) / total_elapsed:.1f} tokens/s")
        
        server_total = sum(elapsed_list)
        efficiency = server_total / total_elapsed if total_elapsed > 0 else 0
        print(f"\n  并发效率:")
        print(f"    服务器总时间: {server_total:.2f}s")
        print(f"    实际耗时:     {total_elapsed:.2f}s")
        print(f"    效率系数:     {efficiency:.2f}x (理论最大值=200x)")
        
        sorted_e = sorted(elapsed_list)
        def pct(p):
            i = min(int(len(sorted_e) * p), len(sorted_e) - 1)
            return sorted_e[i]
        print(f"\n  延迟分布: P50={pct(0.50):.3f}s P75={pct(0.75):.3f}s P90={pct(0.90):.3f}s P95={pct(0.95):.3f}s")
    
    # 最终对比表
    print(f"\n{'='*70}")
    print(f"  📈 200并发加入后的完整对比:")
    print(f"{'='*70}")
    print(f"  {'并发':>6} | {'延迟':>8} | {'请求吞吐':>8} | {'总TPS':>10} | {'效率':>8}")
    print(f"  {'─'*6} | {'─'*8} | {'─'*8} | {'─'*10} | {'─'*8}")
    print(f"  {'5':>6} | {'4.445s':>8} | {'1.07/s':>8} | {'1716 tok/s':>10} | {'4.77x':>8}")
    print(f"  {'10':>6} | {'5.292s':>8} | {'1.86/s':>8} | {'3101 tok/s':>10} | {'9.85x':>8}")
    print(f"  {'50':>6} | {'5.379s':>8} | {'1.85/s':>8} | {'3371 tok/s':>10} | {'9.94x':>8}")
    print(f"  {'100':>6} | {'5.444s':>8} | {'1.81/s':>8} | {'3010 tok/s':>10} | {'9.84x':>8}")
    if elapsed_list:
        avg_tps = statistics.mean([r["tps"] for r in success])
        print(f"  {'200':>6} | {f'{avg:.3f}s':>8} | {f'{len(success)/total_elapsed:.2f}/s':>8} | {f'{sum(token_list)/total_elapsed:.0f} tok/s':>10} | {f'{efficiency:.2f}x':>8}")
    print(f"{'='*70}")
    
    if fails > 0:
        print(f"\n  ⚠️  200并发下有 {len(fails)} 个请求失败！")
        print(f"  ⚠️  说明200并发已经压垮了服务端")
    else:
        print(f"\n  ✅ 200并发 10/10 全部成功，服务端仍然稳定")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
