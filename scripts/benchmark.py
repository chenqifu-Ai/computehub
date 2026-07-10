#!/usr/bin/env python3
"""跨平台 CPU/GPU 基准测试"""
import time, sys, platform, json

def cpu_benchmark():
    """质数计算 — 纯 CPU 密集型"""
    t = time.time()
    count, n = 0, 2
    while count < 30000:
        is_prime = True
        i = 2
        while i * i <= n:
            if n % i == 0:
                is_prime = False
                break
            i += 1
        if is_prime:
            count += 1
        n += 1
    return round(time.time() - t, 3)

def math_benchmark():
    """浮点运算 — 10万次开方求和"""
    t = time.time()
    r = 0.0
    for i in range(1, 100001):
        r += i ** 0.5
    return round(time.time() - t, 3)

def memory_benchmark():
    """内存分配 — 500万整数列表"""
    t = time.time()
    data = list(range(5000000))
    _ = sum(data)
    return round(time.time() - t, 3)

def gpu_check():
    """检测 GPU 信息"""
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            return [g.strip() for g in r.stdout.strip().split('\n')]
    except:
        pass
    return None

def main():
    host = platform.node() or "unknown"
    system = platform.system()
    machine = platform.machine()
    print(f"🏁 {host} ({system} {machine})")
    print(f"⏰ {time.strftime('%H:%M:%S')}")
    print()

    # CPU 基准
    cpu_t = cpu_benchmark()
    print(f"⚡ CPU 跑分: 30000个质数 = {cpu_t}s")

    # 数学基准
    math_t = math_benchmark()
    print(f"🧮 数学运算: 10万次开方 = {math_t}s")

    # 内存基准
    mem_t = memory_benchmark()
    print(f"💾 内存分配: 500万元素 = {mem_t}s")

    # 总分 (越低越好)
    total = round(cpu_t + math_t + mem_t, 3)
    score = max(1, int(100 / (total + 0.01)))
    print(f"📊 总耗时: {total}s | 跑分: {score}")

    # GPU 信息
    gpus = gpu_check()
    if gpus:
        print(f"\n🎮 GPU ({len(gpus)}张):")
        for g in gpus:
            print(f"   {g}")
    else:
        print(f"\n🎮 GPU: 未检测到 NVIDIA GPU")

    # JSON 结果
    result = {
        "host": host, "system": system, "machine": machine,
        "cpu_score": cpu_t, "math_score": math_t, "mem_score": mem_t,
        "total_time": total, "score": score,
        "gpus": gpus
    }
    print(f"\n---JSON---\n{json.dumps(result)}")

if __name__ == "__main__":
    main()
