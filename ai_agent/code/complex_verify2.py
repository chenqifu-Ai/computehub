#!/usr/bin/env python3
"""Complex task test — each node uses native command format"""
import json, time, hashlib, urllib.request

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]
results = {}

def submit_and_wait(cmd, node_id, node_label):
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps({"command": cmd, "node_id": node_id}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    task_id = json.loads(resp.read())["data"]["task_id"]
    for _ in range(30):
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                timeout=10
            )
            detail = json.loads(resp.read())
            if detail["data"]["status"] in ("completed", "failed"):
                return {
                    "node": node_label,
                    "stdout": detail["data"].get("stdout", ""),
                    "stderr": detail["data"].get("stderr", ""),
                    "exit_code": detail["data"].get("exit_code"),
                    "status": detail["data"]["status"]
                }
        except:
            pass
    return {"node": node_label, "error": "timeout", "stdout": ""}

def get_output(stdout, key):
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith(key + "="):
            return line[len(key)+1:].strip()
    return None

# ===== Test 1: Fibonacci(35) =====
print("=" * 60)
print("Test 1: Fibonacci(35) — expected 9227465")
print("=" * 60)

# Use Python on all Linux nodes for consistency (Python is on Fedora + Android)
# Use PowerShell on Windows
fib_commands = {
    "fedora-gpu-01": """
python3 -c "
a, b = 0, 1
for i in range(2, 36): a, b = b, a+b
print('FIB=', b)
"
""".strip(),
    "worker-DESKTOP-BUAUIFL": """
$a = 0; $b = 1
for ($i = 2; $i -le 35; $i++) { $t = $a + $b; $a = $b; $b = $t }
Write-Host "FIB=$b"
""",
    "redmi-1": """
python3 -c "
a, b = 0, 1
for i in range(2, 36): a, b = b, a+b
print('FIB=', b)
"
""".strip()
}

for node, cmd in fib_commands.items():
    result = submit_and_wait(cmd, node, node)
    fib_val = get_output(result["stdout"], "FIB")
    correct = fib_val == "9227465"
    status = "✅" if correct else "❌"
    print(f"  {status} {node}: got={fib_val} (expected=9227465)")
    if not correct:
        print(f"     stdout: {result['stdout'][:200]}")
        print(f"     stderr: {result['stderr'][:200]}")
    results[f"fib_{node}"] = correct

# ===== Test 2: Count primes up to 10000 =====
print("\n" + "=" * 60)
print("Test 2: Prime count up to 10000 — expected 1229")
print("=" * 60)

prime_commands = {
    "fedora-gpu-01": """
python3 -c "
n=10000
is_prime=[True]*n
is_prime[0]=is_prime[1]=False
for i in range(2,int(n**0.5)+1):
    if is_prime[i]:
        for j in range(i*i,n,i): is_prime[j]=False
print('PRIME=', sum(is_prime))
"
""".strip(),
    "worker-DESKTOP-BUAUIFL": """
$limit = 10000
$isPrime = New-Object bool[] $limit
for ($i = 2; $i -lt $limit; $i++) { $isPrime[$i] = $true }
for ($i = 2; $i * $i -lt $limit; $i++) {
    if ($isPrime[$i]) {
        for ($j = $i * $i; $j -lt $limit; $j += $i) { $isPrime[$j] = $false }
    }
}
$primes = 0
for ($i = 2; $i -lt $limit; $i++) { if ($isPrime[$i]) { $primes++ } }
Write-Host "PRIME=$primes"
""",
    "redmi-1": """
python3 -c "
n=10000
is_prime=[True]*n
is_prime[0]=is_prime[1]=False
for i in range(2,int(n**0.5)+1):
    if is_prime[i]:
        for j in range(i*i,n,i): is_prime[j]=False
print('PRIME=', sum(is_prime))
"
""".strip()
}

for node, cmd in prime_commands.items():
    result = submit_and_wait(cmd, node, node)
    prime_val = get_output(result["stdout"], "PRIME")
    correct = prime_val == "1229"
    status = "✅" if correct else "❌"
    print(f"  {status} {node}: got={prime_val} (expected=1229)")
    if not correct:
        print(f"     stdout: {result['stdout'][:200]}")
        print(f"     stderr: {result['stderr'][:200]}")
    results[f"prime_{node}"] = correct

# ===== Test 3: SHA256 of fixed string =====
print("\n" + "=" * 60)
print("Test 3: SHA256 of fixed string")
print("=" * 60)

content = "compute-hub-test-2026"
expected_sha = hashlib.sha256(content.encode()).hexdigest()
print(f"  Content: '{content}'")
print(f"  Expected SHA256: {expected_sha}")

hash_commands = {
    "fedora-gpu-01": f"""
python3 -c "
import hashlib
s = '{content}'
h = hashlib.sha256(s.encode()).hexdigest()
print('SHA256=', h)
"
""".strip(),
    "worker-DESKTOP-BUAUIFL": f"""
$content = "{content}"
$h = [System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($content))).Replace("-", "").ToLower()
Write-Host "SHA256=$h"
""",
    "redmi-1": f"""
python3 -c "
import hashlib
s = '{content}'
h = hashlib.sha256(s.encode()).hexdigest()
print('SHA256=', h)
"
""".strip()
}

for node, cmd in hash_commands.items():
    result = submit_and_wait(cmd, node, node)
    sha_val = get_output(result["stdout"], "SHA256")
    correct = sha_val == expected_sha
    status = "✅" if correct else "❌"
    print(f"  {status} {node}: got={sha_val}")
    if not correct:
        print(f"       expected={expected_sha}")
        print(f"       stdout: {result['stdout'][:200]}")
        print(f"       stderr: {result['stderr'][:200]}")
    results[f"hash_{node}"] = correct

# ===== Summary =====
print("\n" + "=" * 60)
total = len(results)
passed = sum(results.values())
failed = total - passed
print(f"Total: {total} | ✅ {passed} | ❌ {failed}")
if failed == 0:
    print("🎉 ALL COMPLEX TESTS PASSED!")
else:
    print(f"⚠️ {failed} tests failed:")
    for k, v in results.items():
        if not v:
            print(f"   ❌ {k}")
print("=" * 60)
