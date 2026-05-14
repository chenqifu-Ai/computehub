#!/usr/bin/env python3
"""
Cluster benchmark - proper approach using Python scripts as files
"""
import json, time, hashlib, base64, urllib.request, random, string, os

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]

def submit_and_wait(cmd, node_id):
    """Submit and wait for result"""
    try:
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps({"command": cmd, "node_id": node_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        task_id = json.loads(resp.read())["data"]["task_id"]
    except Exception as e:
        return None, None

    # Wait
    for _ in range(60):
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                timeout=10
            )
            detail = json.loads(resp.read())
            if detail["data"]["status"] in ("completed", "failed"):
                return detail["data"].get("stdout", "").strip(), detail["data"].get("stderr", "").strip()
        except:
            pass
    return None, None

def create_script_cmd(script_content, is_windows=False):
    """
    Write script to temp file, then execute it.
    This avoids ARG_MAX limit.
    """
    if is_windows:
        # Windows: write to file, then execute
        return (
            f'echo "{base64.b64encode(script_content.encode()).decode()}" | base64 -d > C:\\temp.ps1 && '
            f'powershell -ExecutionPolicy Bypass -File C:\\temp.ps1 && '
            f'rm C:\\temp.ps1'
        )
    else:
        # Linux/Android: write to file, then execute
        return (
            f'echo "{base64.b64encode(script_content.encode()).decode()}" | base64 -d > /tmp/temp_script.py && '
            f'python3 /tmp/temp_script.py && '
            f'rm /tmp/temp_script.py'
        )

# ===== BENCHMARK 1: Fibonacci =====
print("=" * 70)
print("BENCHMARK 1: Fibonacci(34) = 9227465")
print("=" * 70)

fib_script = """
a, b = 0, 1
for _ in range(34):
    a, b = b, a + b
print(b)
"""

results_fib = {}
for node in NODES:
    is_win = (node == "worker-DESKTOP-BUAUIFL")
    cmd = create_script_cmd(fib_script, is_windows=is_win)
    stdout, stderr = submit_and_wait(cmd, node)
    if stdout and stdout.strip().isdigit():
        print(f"  {node}: F(34) = {stdout.strip()}")
        results_fib[node] = stdout.strip() == "9227465"
    else:
        print(f"  {node}: ❌ {stderr[:100] if stderr else 'timeout'}")

# ===== BENCHMARK 2: Prime Counting =====
print("\n" + "=" * 70)
print("BENCHMARK 2: Primes(100,000) = 9592")
print("=" * 70)

prime_script = """
n = 100000
p = [True] * n
p[0] = p[1] = False
for i in range(2, int(n**0.5) + 1):
    if p[i]:
        for j in range(i*i, n, i):
            p[j] = False
print(sum(p))
"""

results_primes = {}
for node in NODES:
    is_win = (node == "worker-DESKTOP-BUAUIFL")
    cmd = create_script_cmd(prime_script, is_windows=is_win)
    stdout, stderr = submit_and_wait(cmd, node)
    if stdout and stdout.strip().isdigit():
        print(f"  {node}: primes(100k) = {stdout.strip()}")
        results_primes[node] = stdout.strip() == "9592"
    else:
        print(f"  {node}: ❌ {stderr[:100] if stderr else 'timeout'}")

# ===== BENCHMARK 3: SHA256 Hashing =====
print("\n" + "=" * 70)
print("BENCHMARK 3: SHA256 of 10KB data")
print("=" * 70)

# Use smaller data to test, but still meaningful
content = "compute-hub-benchmark-" + "".join(random.choices(string.ascii_letters, k=10000))
expected_sha = hashlib.sha256(content.encode()).hexdigest()
print(f"  Content length: {len(content)} bytes")
print(f"  Expected SHA256: {expected_sha}")

hash_script = f"""
import hashlib
content = "{content}"
h = hashlib.sha256(content.encode()).hexdigest()
print(h)
"""

results_hash = {}
for node in NODES:
    is_win = (node == "worker-DESKTOP-BUAUIFL")
    cmd = create_script_cmd(hash_script, is_windows=is_win)
    stdout, stderr = submit_and_wait(cmd, node)
    if stdout == expected_sha:
        print(f"  {node}: ✅ {stdout[:32]}...")
        results_hash[node] = True
    else:
        print(f"  {node}: ❌ got={stdout[:32]}... expected={expected_sha[:32]}...")
        results_hash[node] = False

# ===== BENCHMARK 4: File I/O =====
print("\n" + "=" * 70)
print("BENCHMARK 4: File I/O (50MB write + 50MB read)")
print("=" * 70)

fileio_script = """
import time, os

f = '/tmp/bench.bin'
data = bytes(1048576)  # 1MB

# Write 50MB
start = time.time()
with open(f, 'wb') as fh:
    for _ in range(50):
        fh.write(data)
write_ms = int((time.time() - start) * 1000)

# Read 50MB
start = time.time()
t = 0
with open(f, 'rb') as fh:
    while True:
        c = fh.read(1048576)
        if not c:
            break
        t += len(c)
read_ms = int((time.time() - start) * 1000)

os.remove(f)

print(f"WRITE_MS={write_ms}")
print(f"READ_MS={read_ms}")
print(f"TOTAL_BYTES={t}")
"""

results_fileio = {}
for node in NODES:
    is_win = (node == "worker-DESKTOP-BUAUIFL")
    cmd = create_script_cmd(fileio_script, is_windows=is_win)
    stdout, stderr = submit_and_wait(cmd, node)
    if stdout:
        for line in stdout.split('\n'):
            if "WRITE_MS" in line:
                print(f"  {node}: Write 50MB = {line.split('=')[1]}ms")
            elif "READ_MS" in line:
                print(f"  {node}: Read 50MB = {line.split('=')[1]}ms")
        results_fileio[node] = True
    else:
        print(f"  {node}: ❌ {stderr[:100] if stderr else 'timeout'}")

# ===== BENCHMARK 5: CPU Stress =====
print("\n" + "=" * 70)
print("BENCHMARK 5: CPU Stress (10M iterations)")
print("=" * 70)

cpu_script = """
import time

start = time.time()
x = 0
for i in range(10000000):
    x += i
print(int((time.time() - start) * 1000))
"""

results_cpu = {}
for node in NODES:
    is_win = (node == "worker-DESKTOP-BUAUIFL")
    cmd = create_script_cmd(cpu_script, is_windows=is_win)
    stdout, stderr = submit_and_wait(cmd, node)
    if stdout and stdout.strip().isdigit():
        print(f"  {node}: 10M iterations = {stdout.strip()}ms")
        results_cpu[node] = True
    else:
        print(f"  {node}: ❌ {stderr[:100] if stderr else 'timeout'}")

# ===== SUMMARY =====
print("\n" + "=" * 70)
print("CLUSTER CAPABILITY SUMMARY")
print("=" * 70)

print(f"\n📊 Test Results:")
print(f"  {'Test':<20} {'Fedora':<15} {'Windows':<15} {'Redmi':<15}")
print(f"  {'─'*20} {'─'*15} {'─'*15} {'─'*15}")

tests = [
    ("Fibonacci(34)", results_fib),
    ("Primes(100k)", results_primes),
    ("SHA256", results_hash),
    ("File I/O", results_fileio),
    ("CPU Stress", results_cpu),
]

for test_name, results in tests:
    line = f"  {test_name:<20} "
    for node in NODES:
        if results.get(node):
            line += "✅ "
        else:
            line += "❌ "
    print(line)

# Speed comparison
print(f"\n⚡ Speed Comparison:")
for test_name, results in tests:
    if test_name == "File I/O":
        print(f"  {test_name}:")
        for node in NODES:
            if node in results_fileio:
                # Would need to extract actual times here
                pass

print("\n" + "=" * 70)
