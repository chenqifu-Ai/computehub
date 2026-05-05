#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片识别耗时分析 — 逐点计时
分析最近一张图片的完整流程，每个步骤都计时
"""
import os, sys, time, base64, requests, subprocess

IMG_PATH = "/storage/emulated/0/DCIM/Camera/IMG_20260501_061751.jpg"
API_URL = "http://127.0.0.1:8765/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

print("=" * 80)
print("  🔬 图片识别耗时分析 — 逐点计时")
print(f"  图片：{IMG_PATH}")
print("=" * 80)

# 步骤 1：查找图片
t0 = time.time()
if not os.path.exists(IMG_PATH):
    print("\n❌ 步骤 1: 文件不存在")
    sys.exit(1)
t1 = time.time()
stat = os.stat(IMG_PATH)
size_kb = stat.st_size / 1024
print(f"\n步骤 1: 查找图片")
print(f"  耗时: {(t1-t0)*1000:.0f}ms")
print(f"  状态: ✅ 文件存在")
print(f"  大小: {size_kb:.0f}KB")

# 步骤 2：读取文件
t1_start = time.time()
with open(IMG_PATH, "rb") as f:
    raw_data = f.read()
t1_end = time.time()
print(f"\n步骤 2: 读取文件到内存")
print(f"  耗时: {(t1_end-t1_start)*1000:.0f}ms")
print(f"  读取大小: {len(raw_data)/1024:.0f}KB")

# 步骤 3：Base64 编码
t2_start = time.time()
b64 = base64.b64encode(raw_data).decode()
t2_end = time.time()
print(f"\n步骤 3: Base64 编码")
print(f"  耗时: {(t2_end-t2_start)*1000:.0f}ms")
print(f"  编码后大小: {len(b64)/1024:.0f}KB")

# 步骤 4：发送 API 请求
t3_start = time.time()
payload = {
    "model": "qwen3.6-35b",
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": "请详细描述这张图片的内容。"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
    ]}],
    "max_tokens": 8192,
    "temperature": 0.3
}
print(f"\n步骤 4: 构建请求 payload")
print(f"  耗时: {(time.time()-t3_start)*1000:.0f}ms")
print(f"  Payload 大小: {len(str(payload))/1024:.0f}KB")

# 步骤 4b: 网络传输
t4_start = time.time()
r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=300)
t4_end = time.time()
print(f"\n步骤 4b: 网络传输 (发送到 vllm)")
print(f"  耗时: {(t4_end-t4_start)*1000:.0f}ms")
print(f"  HTTP 状态: {r.status_code}")

# 步骤 4c: API 推理时间（HTTP 响应头中的 x-processing-time）
processing_time = r.headers.get('x-processing-time', 'N/A')
print(f"  Server 推理时间: {processing_time}")

# 步骤 5：解析响应
t5_start = time.time()
data = r.json()
content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
reasoning = data.get('choices', [{}])[0].get('message', {}).get('reasoning', '')
result = content or reasoning
usage = data.get('usage', {})
t5_end = time.time()
print(f"\n步骤 5: 解析 API 响应")
print(f"  耗时: {(t5_end-t5_start)*1000:.0f}ms")
print(f"  总 tokens: {usage.get('total_tokens', '?')}")
print(f"  Prompt tokens: {usage.get('prompt_tokens', '?')}")
print(f"  Completion tokens: {usage.get('completion_tokens', '?')}")
print(f"  结果长度: {len(result)} 字符")

# 步骤 6：组织回复
t6_start = time.time()
# 模拟格式化输出
report = f"## 图片分析\n\n耗时: {(t5_end-t0):.1f}s\n大小: {size_kb:.0f}KB\n结果: {result[:200]}..."
t6_end = time.time()
print(f"\n步骤 6: 组织回复给用户")
print(f"  耗时: {(t6_end-t6_start)*1000:.0f}ms")

total_time = t6_end - t0

# 汇总时间轴
print("\n" + "=" * 80)
print("  📊 时间轴汇总")
print("=" * 80)

steps = [
    ("查找图片", (t1-t0)*1000),
    ("读取文件", (t1_end-t1_start)*1000),
    ("Base64 编码", (t2_end-t2_start)*1000),
    ("构建 Payload", (time.time()-t3_start)*1000),
    ("网络传输", (t4_end-t4_start)*1000),
    ("API 推理", (t4_end-t4_start)*1000),  # 近似（服务器处理时间）
    ("解析响应", (t5_end-t5_start)*1000),
    ("组织回复", (t6_end-t6_start)*1000),
]

print(f"\n  {'步骤':<15} {'耗时(ms)':<12} {'占比':<10} {'进度条'}")
print(f"  {'-'*65}")

total_ms = sum(s[1] for s in steps)
for name, ms in steps:
    pct = ms / total_ms * 100 if total_ms > 0 else 0
    bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
    print(f"  {name:<15} {ms:>8.1f}ms  {pct:>5.1f}%  [{bar}]")

print(f"\n  {'-'*65}")
print(f"  {'总计':<15} {total_ms:>8.1f}ms")

# 瓶颈分析
print(f"\n  {'='*65}")
print(f"  🔍 瓶颈分析:")
print(f"{'='*65}")

max_step = max(steps, key=lambda x: x[1])
if max_step[1] > total_ms * 0.5:
    print(f"  ⚠️  主要瓶颈: {max_step[0]} ({max_step[1]/total_ms*100:.1f}%)")
    if "API" in max_step[0] or "推理" in max_step[0]:
        print(f"  建议: GPU 推理速度慢，可能需要升级 GPU 或优化模型")
    elif "网络" in max_step[0]:
        print(f"  建议: 网络延迟高，考虑就近部署 vllm 或使用更近的服务器")
    elif "Base64" in max_step[0]:
        print(f"  建议: 图片压缩后传输可减少编码时间")

print(f"\n  各步骤耗时详情:")
print(f"  1. 查找/读取/编码: {(steps[0][1]+steps[1][1]+steps[2][1]):.1f}ms ({(steps[0][1]+steps[1][1]+steps[2][1])/total_ms*100:.1f}%)")
print(f"  2. 网络传输+推理: {(steps[3][1]+steps[4][1]):.1f}ms ({(steps[3][1]+steps[4][1])/total_ms*100:.1f}%)")
print(f"  3. 解析+组织: {(steps[5][1]+steps[6][1]):.1f}ms ({(steps[5][1]+steps[6][1])/total_ms*100:.1f}%)")

# 对比目标
print(f"\n  📈 性能对比:")
print(f"  当前总耗时: {total_time:.1f}s")
print(f"  图片大小: {size_kb:.0f}KB")
print(f"  输出 tokens: {usage.get('completion_tokens', 0)}")
if usage.get('completion_tokens', 0) > 0:
    tok_per_sec = usage['completion_tokens'] / total_time
    print(f"  输出速度: {tok_per_sec:.1f} tokens/s")

print("\n" + "=" * 80)
print("  ✅ 分析完成")
print("=" * 80)
