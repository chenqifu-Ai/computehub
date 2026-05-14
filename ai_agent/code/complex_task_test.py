#!/usr/bin/env python3
"""
Complex task test:
- Each node runs different calculation (sorting, math, file processing)
- Submit results to Gateway for verification
- Test: computation + result integrity
"""

import json
import time
import base64
import urllib.request
import hashlib
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]

results = {}

# ===== Test 1: Fibonacci (CPU intensive) =====
def fib_test():
    """Each node computes fib(35) and returns the number"""
    print("\n--- Test 1: Fibonacci(35) ---")
    # fib(35) = 9227465
    expected = 9227465
    
    tasks = {}
    for node in NODES:
        if node == "worker-DESKTOP-BUAUIFL":
            cmd = """
function fib($n) {
    if ($n -le 1) { return $n }
    $a = 0; $b = 1
    for ($i = 2; $i -le $n; $i++) {
        $temp = $a + $b; $a = $b; $b = $temp
    }
    return $b
}
Write-Host "FIB_RESULT=" (fib 35)
"""
            b64 = base64.b64encode(cmd.encode('utf-16-le')).decode('ascii')
            cmd = f"powershell -EncodedCommand {b64}"
        else:
            cmd = """
fib() {
    local n=$1 a=0 b=1
    if [ $n -le 1 ]; then echo $n; return; fi
    for ((i=2; i<=n; i++)); do
        t=$((a+b)); a=$b; b=$t
    done
    echo $b
}
echo "FIB_RESULT=$(fib 35)"
"""
        
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps({"command": cmd, "node_id": node}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        task_id = json.loads(resp.read())["data"]["task_id"]
        tasks[task_id] = {"node": node, "type": "fib", "expected": expected}
    
    # Wait and check
    fib_results = {}
    for attempt in range(30):
        for task_id, info in tasks.items():
            if task_id in fib_results:
                continue
            try:
                resp = urllib.request.urlopen(
                    urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                    timeout=10
                )
                detail = json.loads(resp.read())
                if detail["data"]["status"] in ("completed", "failed"):
                    stdout = detail["data"].get("stdout", "")
                    fib_results[task_id] = {"node": info["node"], "stdout": stdout, "expected": info["expected"]}
            except:
                pass
        
        if len(fib_results) == len(NODES):
            break
        time.sleep(2)
    
    # Verify results
    for task_id, info in fib_results.items():
        stdout = info["stdout"].strip()
        match = False
        for line in stdout.split("\n"):
            if "FIB_RESULT=" in line:
                got = line.split("=")[1].strip()
                match = str(info["expected"]) == got
                break
        
        status = "✅" if match else "❌"
        print(f"  {status} {info['node']}: got {stdout.strip().split('=')[1].strip()}, expected {info['expected']}")
        results[f"fib_{info['node']}"] = match


# ===== Test 2: Prime number counting =====
def prime_test():
    """Count primes up to 10000 on each node"""
    print("\n--- Test 2: Count primes up to 10000 ---")
    # Sieve of Eratosthenes: 1229 primes up to 10000
    expected = 1229
    
    tasks = {}
    for node in NODES:
        if node == "worker-DESKTOP-BUAUIFL":
            cmd = """
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
Write-Host "PRIME_COUNT=$primes"
"""
            b64 = base64.b64encode(cmd.encode('utf-16-le')).decode('ascii')
            cmd = f"powershell -EncodedCommand {b64}"
        else:
            cmd = """
limit=10000
is_prime=[True]*limit
is_prime[0]=is_prime[1]=False
for i in range(2,int(limit**0.5)+1):
    if is_prime[i]:
        for j in range(i*i,limit,i):
            is_prime[j]=False
count=sum(is_prime)
echo "PRIME_COUNT=$count"
"""
        
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps({"command": cmd, "node_id": node}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        task_id = json.loads(resp.read())["data"]["task_id"]
        tasks[task_id] = {"node": node, "type": "prime", "expected": expected}
    
    # Wait and verify
    prime_results = {}
    for attempt in range(30):
        for task_id, info in tasks.items():
            if task_id in prime_results:
                continue
            try:
                resp = urllib.request.urlopen(
                    urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                    timeout=10
                )
                detail = json.loads(resp.read())
                if detail["data"]["status"] in ("completed", "failed"):
                    stdout = detail["data"].get("stdout", "")
                    prime_results[task_id] = {"node": info["node"], "stdout": stdout, "expected": info["expected"]}
            except:
                pass
        
        if len(prime_results) == len(NODES):
            break
        time.sleep(2)
    
    for task_id, info in prime_results.items():
        stdout = info["stdout"].strip()
        match = False
        for line in stdout.split("\n"):
            if "PRIME_COUNT=" in line:
                got = line.split("=")[1].strip()
                match = str(info["expected"]) == got
                break
        
        status = "✅" if match else "❌"
        print(f"  {status} {info['node']}: got {stdout.strip().split('=')[1].strip()}, expected {info['expected']}")
        results[f"prime_{info['node']}"] = match


# ===== Test 3: SHA256 hash (file processing) =====
def hash_test():
    """Each node generates a file, compute SHA256, verify"""
    print("\n--- Test 3: SHA256 hash verification ---")
    
    # Generate fixed content
    content = "Hello from ComputeHub on " + time.strftime("%Y%m%d")
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    
    tasks = {}
    for node in NODES:
        if node == "worker-DESKTOP-BUAUIFL":
            cmd = f"""
$content = "{content}"
$content | Out-File -FilePath D:\\hash_test.txt -Encoding utf8
$hash = (Get-FileHash D:\\hash_test.txt -Algorithm SHA256).Hash
Remove-Item D:\\hash_test.txt
Write-Host "HASH=$hash"
"""
            b64 = base64.b64encode(cmd.encode('utf-16-le')).decode('ascii')
            cmd = f"powershell -EncodedCommand {b64}"
        else:
            cmd = f"""
echo "{content}" > /tmp/hash_test.txt
echo "HASH=$(sha256sum /tmp/hash_test.txt | cut -d' ' -f1)"
rm /tmp/hash_test.txt
"""
        
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps({"command": cmd, "node_id": node}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        task_id = json.loads(resp.read())["data"]["task_id"]
        tasks[task_id] = {"node": node, "type": "hash", "expected": expected_hash}
    
    # Wait and verify
    hash_results = {}
    for attempt in range(30):
        for task_id, info in tasks.items():
            if task_id in hash_results:
                continue
            try:
                resp = urllib.request.urlopen(
                    urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                    timeout=10
                )
                detail = json.loads(resp.read())
                if detail["data"]["status"] in ("completed", "failed"):
                    stdout = detail["data"].get("stdout", "")
                    hash_results[task_id] = {"node": info["node"], "stdout": stdout, "expected": info["expected"]}
            except:
                pass
        
        if len(hash_results) == len(NODES):
            break
        time.sleep(2)
    
    for task_id, info in hash_results.items():
        stdout = info["stdout"].strip()
        match = False
        for line in stdout.split("\n"):
            if "HASH=" in line:
                got = line.split("=")[1].strip()
                match = info["expected"] == got
                break
        
        status = "✅" if match else "❌"
        got = stdout.strip().split("=")[1].strip()
        print(f"  {status} {info['node']}: {got[:32]}...")
        if not match:
            print(f"       expected: {info['expected'][:32]}...")
        results[f"hash_{info['node']}"] = match


if __name__ == "__main__":
    print("=" * 60)
    print("COMPLEX TASK TEST WITH RESULT VERIFICATION")
    print("=" * 60)
    
    start = time.time()
    
    fib_test()
    prime_test()
    hash_test()
    
    elapsed = time.time() - start
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"Total checks: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    print(f"Time: {elapsed:.1f}s")
    
    if failed == 0:
        print("\n🎉 ALL COMPLEX TESTS PASSED!")
    else:
        print(f"\n⚠️ {failed} tests failed")
    
    print("=" * 60)
