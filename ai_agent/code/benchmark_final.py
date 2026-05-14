#!/usr/bin/env python3
"""
ComputeHub Cluster Benchmark Suite
Test all 3 nodes with 5 different tasks to measure cluster capabilities.
"""
import json, time, hashlib, base64, urllib.request, random, string

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]

def win_cmd(ps_script):
    inner = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
    full = f"powershell -EncodedCommand {inner}"
    outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
    return f"cmd /c powershell -EncodedCommand {outer}"

def submit(cmd, node_id):
    try:
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps({"command": cmd, "node_id": node_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())["data"]["task_id"]
    except Exception as e:
        return None

def get_result(task_id, timeout=60):
    for _ in range(timeout // 2):
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                timeout=10
            )
            detail = json.loads(resp.read())
            if detail["data"]["status"] in ("completed", "failed"):
                return {
                    "stdout": detail["data"].get("stdout", "").strip(),
                    "stderr": detail["data"].get("stderr", "").strip(),
                    "exit_code": detail["data"].get("exit_code"),
                    "status": detail["data"]["status"]
                }
        except:
            pass
    return {"stdout": "", "stderr": "", "exit_code": -1, "status": "timeout"}

all_tasks = {}

# ===== TEST 1: Fibonacci =====
print("=" * 70)
print("TEST 1: Fibonacci(34) = 9227465")
print("=" * 70)

for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd("$a=0;$b=1;for($i=0;$i-lt 34;$i++){$t=$a+$b;$a=$b;$b=$t};Write-Host $b")
    else:
        cmd = 'python3 -c "a,b=0,1\nfor _ in range(34):a,b=b,a+b\nprint(b)"'
    tid = submit(cmd, node)
    if tid:
        all_tasks[(node, "fib")] = tid
        print(f"  {node}: ✅ submitted")

# ===== TEST 2: Prime count =====
print("\n" + "=" * 70)
print("TEST 2: Primes(100,000) = 9592")
print("=" * 70)

for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd("$l=100000;$p=New-Object bool[]$l;for($i=2;$i-lt$l;$i++){$p[$i]=$true};for($i=2;$i*$i-lt$l;$i++){if($p[$i]){for($j=$i*$i;$j-lt$l;$j+=$i){$p[$j]=$false}}};$c=0;for($i=2;$i-lt$l;$i++){if($p[$i]){$c++}};Write-Host $c")
    else:
        cmd = 'python3 -c "\nn=100000\np=[True]*n\np[0]=p[1]=False\nfor i in range(2,int(n**0.5)+1):\n  if p[i]:\n    for j in range(i*i,n,i):p[j]=False\nprint(sum(p))\n"'
    tid = submit(cmd, node)
    if tid:
        all_tasks[(node, "primes")] = tid
        print(f"  {node}: ✅ submitted")

# ===== TEST 3: SHA256 =====
print("\n" + "=" * 70)
print("TEST 3: SHA256 of 'compute-hub-test'")
print("=" * 70)

content = "compute-hub-test"
expected = hashlib.sha256(content.encode()).hexdigest()
print(f"  Expected: {expected}")

for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd(f"$c=\"{content}\";$h=[System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($c))).Replace(\"-\",\"\").ToLower();Write-Host $h")
    else:
        cmd = f'python3 -c "import hashlib;print(hashlib.sha256(\'{content}\'.encode()).hexdigest())"'
    tid = submit(cmd, node)
    if tid:
        all_tasks[(node, "hash")] = {"task_id": tid, "expected": expected}
        print(f"  {node}: ✅ submitted")

# ===== TEST 4: File I/O =====
print("\n" + "=" * 70)
print("TEST 4: File I/O (50MB write + 50MB read)")
print("=" * 70)

for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd('$d=New-Object byte[](1048576);[Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($d);$sw=[System.Diagnostics.Stopwatch]::StartNew();$s=[System.IO.File]::OpenWrite("D:\\bench.bin");for($i=0;$i-lt 50;$i++){$s.Write($d,0,$d.Length)};$s.Close();$w=$sw.ElapsedMilliseconds;$sw.Reset();$sw.Start();$rs=[System.IO.File]::OpenRead("D:\\bench.bin");$b=New-Object byte[](1048576);$t=0;while($true){$r=$rs.Read($b,0,$b.Length);if($r-eq 0){break};$t+=$r};$rs.Close();$sw.Stop();$r=$sw.ElapsedMilliseconds;Remove-Item D:\\bench.bin -Force;Write-Host "WRITE_MS=$w";Write-Host "READ_MS=$r"')
    else:
        cmd = 'python3 -c "\nimport time,os\nf=\'/tmp/b.bin\'\nd=bytes(1048576)\ns=time.time()\nwith open(f,\'wb\') as fh:\n  for _ in range(50):fh.write(d)\nw=int((time.time()-s)*1000)\ns=time.time()\nt=0\nwith open(f,\'rb\') as fh:\n  while True:\n    c=fh.read(1048576)\n    if not c:break\n    t+=len(c)\nr=int((time.time()-s)*1000)\nos.remove(f)\nprint(\'WRITE_MS=\'+str(w))\nprint(\'READ_MS=\'+str(r))\nprint(\'TOTAL_BYTES=\'+str(t))\n"'
    tid = submit(cmd, node)
    if tid:
        all_tasks[(node, "fileio")] = tid
        print(f"  {node}: ✅ submitted")

# ===== TEST 5: CPU Stress =====
print("\n" + "=" * 70)
print("TEST 5: CPU Stress (10M iterations)")
print("=" * 70)

for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd('$sw=[System.Diagnostics.Stopwatch]::StartNew();$x=0;for($i=0;$i-lt 10000000;$i++){$x+=$i};$sw.Stop();Write-Host "MS=$($sw.ElapsedMilliseconds)"')
    else:
        cmd = 'python3 -c "\nimport time\ns=time.time()\nx=0\nfor i in range(10000000):x+=i\nprint(int((time.time()-s)*1000))\n"'
    tid = submit(cmd, node)
    if tid:
        all_tasks[(node, "cpu")] = tid
        print(f"  {node}: ✅ submitted")

# ===== WAIT AND RESULTS =====
print("\n" + "=" * 70)
print("Waiting for completion...")
print("=" * 70)

wait_start = time.time()
completed = {}

for attempt in range(120):
    for key, tid in all_tasks.items():
        if isinstance(tid, dict):
            tid = tid["task_id"]
        if tid in completed:
            continue
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={tid}"),
                timeout=10
            )
            detail = json.loads(resp.read())
            if detail["data"]["status"] in ("completed", "failed"):
                res = {
                    "stdout": detail["data"].get("stdout", "").strip(),
                    "stderr": detail["data"].get("stderr", "").strip(),
                    "exit_code": detail["data"].get("exit_code"),
                    "status": detail["data"]["status"],
                    "key": key
                }
                completed[tid] = res
        except:
            pass
    
    if len(completed) == len(all_tasks):
        break
    
    if attempt % 10 == 0:
        print(f"  [{attempt+1}/120] {len(completed)}/{len(all_tasks)}")
        time.sleep(1)

total_time = time.time() - wait_start
print(f"Completed: {len(completed)}/{len(all_tasks)} in {total_time:.1f}s")

# ===== PRINT RESULTS =====
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

tests = [("fib", "Fibonacci(34)"), ("primes", "Primes(100k)"), ("hash", "SHA256"), ("fileio", "File I/O"), ("cpu", "CPU Stress")]
for test_key, test_name in tests:
    print(f"\n--- {test_name} ---")
    for node in NODES:
        key = (node, test_key)
        tid = all_tasks.get(key)
        if isinstance(tid, dict):
            tid = tid["task_id"]
        
        if tid not in completed:
            print(f"  {node:20s}: TIMEOUT")
            continue
        
        res = completed[tid]
        if res["status"] != "completed":
            print(f"  {node:20s}: FAILED (exit={res['exit_code']})")
            if res.get("stderr", ""):
                print(f"    {res['stderr'][:120]}")
            continue
        
        stdout = res["stdout"]
        
        if test_key == "fib":
            print(f"  {node:20s}: {stdout}")
        elif test_key == "primes":
            print(f"  {node:20s}: {stdout}")
        elif test_key == "hash":
            expected = all_tasks[(node, "hash")]["expected"]
            ok = "✅" if stdout == expected else "❌"
            print(f"  {node:20s}: {ok} {stdout[:32]}...")
        elif test_key == "fileio":
            for line in stdout.split("\n"):
                if "WRITE_MS" in line:
                    print(f"  {node:20s}: Write 50MB = {line.split('=')[1]}ms")
                elif "READ_MS" in line:
                    print(f"  {node:20s}: Read 50MB = {line.split('=')[1]}ms")
        elif test_key == "cpu":
            print(f"  {node:20s}: 10M iters = {stdout}ms")

# ===== SUMMARY =====
print("\n" + "=" * 70)
print("CLUSTER SUMMARY")
print("=" * 70)
total = len(all_tasks)
done = len(completed)
success = sum(1 for r in completed.values() if r["status"] == "completed")
print(f"Tasks: {total} | ✅ Success: {success} | ❌ Failed: {done-success}")
print(f"Time: {total_time:.1f}s | Throughput: {done/total_time:.1f} tasks/sec")
print(f"\nPer-node:")
for node in NODES:
    count = sum(1 for r in completed.values() if r["key"][0] == node)
    print(f"  {node:20s}: {count} tasks")
print("=" * 70)
