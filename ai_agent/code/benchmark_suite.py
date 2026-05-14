#!/usr/bin/env python3
"""
ComputeHub Cluster Benchmark Suite
Test all 3 nodes with diverse tasks to measure cluster capabilities.
"""
import json, time, hashlib, base64, urllib.request, random, string
from concurrent.futures import ThreadPoolExecutor, as_completed

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]
tasks_submitted = []

def win_cmd(ps_script):
    """Encode PowerShell script for Windows worker (double base64)"""
    inner = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
    full = f"powershell -EncodedCommand {inner}"
    outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
    return f"cmd /c powershell -EncodedCommand {outer}"

def get_output(stdout, key):
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith(key + "="):
            return line[len(key)+1:].strip()
    return None

# Build all tasks
all_tasks = []

for i, node in enumerate(NODES):
    # Test 1: Fibonacci
    if node == "worker-DESKTOP-BUAUIFL":
        all_tasks.append((
            win_cmd(
                "$a=0;$b=1\nfor($i=0;$i-lt 34;$i++){$t=$a+$b;$a=$b;$b=$t}\n"
                'Write-Host "RESULT=$b"\n'
            ),
            node, "fibonacci", i
        ))
    else:
        all_tasks.append((
            'python3 -c "\na,b=0,1\nfor _ in range(34):a,b=b,a+b\nprint(\"RESULT=\"+str(b))\n"\n',
            node, "fibonacci", i
        ))

for i, node in enumerate(NODES):
    # Test 2: Prime counting 100k
    if node == "worker-DESKTOP-BUAUIFL":
        all_tasks.append((
            win_cmd(
                "$l=100000;$p=New-Object bool[]$l\nfor($i=2;$i-lt$l;$i++){$p[$i]=$true}\n"
                "for($i=2;$i*$i-lt$l;$i++){if($p[$i]){for($j=$i*$i;$j-lt$l;$j+=$i){$p[$j]=$false}}}\n"
                "$c=0;for($i=2;$i-lt$l;$i++){if($p[$i]){$c++}}\n"
                'Write-Host "RESULT=$c"\n'
            ),
            node, "primes", i
        ))
    else:
        all_tasks.append((
            'python3 -c "\nn=100000\np=[True]*n;p[0]=p[1]=False\nfor i in range(2,int(n**0.5)+1):\n  if p[i]:[p.__setitem__(j,False) for j in range(i*i,n,i)]\nprint(\"RESULT=\"+str(sum(p)))\n"\n',
            node, "primes", i
        ))

for i, node in enumerate(NODES):
    # Test 3: SHA256 of 1MB random data
    content = "compute-hub-" + "".join(random.choices(string.ascii_letters, k=1000000))
    if node == "worker-DESKTOP-BUAUIFL":
        safe = content.replace('"', "'")
        all_tasks.append((
            win_cmd(
                "$c=\"" + safe + "\"\n"
                "$h=[System.BitConverter]::ToString((New-Object System.Security.Cryptography.SHA256Managed).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($c))).Replace(\"-\",\"\").ToLower()\n"
                'Write-Host "RESULT=$h"\n'
            ),
            node, "hash", i
        ))
    else:
        safe = content.replace("'", "\\'")
        all_tasks.append((
            f'python3 -c "import hashlib;print(\"RESULT=\"+hashlib.sha256(\\"{safe}\\".encode()).hexdigest())"\n',
            node, "hash", i
        ))

for i, node in enumerate(NODES):
    # Test 4: File I/O
    if node == "worker-DESKTOP-BUAUIFL":
        all_tasks.append((
            win_cmd(
                '$d=New-Object byte[](1048576);[Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($d)\n'
                '$sw=[System.Diagnostics.Stopwatch]::StartNew()\n'
                '$s=[System.IO.File]::OpenWrite("D:\\bench.bin")\n'
                'for($i=0;$i-lt 50;$i++){$s.Write($d,0,$d.Length)};$s.Close()\n'
                '$w=$sw.ElapsedMilliseconds;$sw.Reset()\n'
                '$sw.Start()\n'
                '$rs=[System.IO.File]::OpenRead("D:\\bench.bin")\n'
                '$b=New-Object byte[](1048576);$t=0\n'
                'while($true){$r=$rs.Read($b,0,$b.Length);if($r-eq 0){break};$t+=$r}\n'
                '$rs.Close();$sw.Stop();$r=$sw.ElapsedMilliseconds\n'
                'Remove-Item D:\\bench.bin -Force\n'
                'Write-Host "WRITE_MS=$w"\n'
                'Write-Host "READ_MS=$r"\n'
                'Write-Host "TOTAL_BYTES=$t"\n'
            ),
            node, "fileio", i
        ))
    else:
        all_tasks.append((
            'python3 -c "\nimport time\nf=\'/tmp/b.bin\'\nd=bytes(1048576)\ns=time.time()\nwith open(f,\'wb\') as fh:\n  for _ in range(50):fh.write(d)\nw=int((time.time()-s)*1000)\ns=time.time()\nt=0\nwith open(f,\'rb\') as fh:\n  while True:\n    c=fh.read(1048576)\n    if not c:break\n    t+=len(c)\nr=int((time.time()-s)*1000)\nimport os;os.remove(f)\nprint(\'WRITE_MS=\'+str(w))\nprint(\'READ_MS=\'+str(r))\nprint(\'TOTAL_BYTES=\'+str(t))\n"\n',
            node, "fileio", i
        ))

for i, node in enumerate(NODES):
    # Test 5: CPU stress 10M iterations
    if node == "worker-DESKTOP-BUAUIFL":
        all_tasks.append((
            win_cmd(
                '$sw=[System.Diagnostics.Stopwatch]::StartNew()\n$x=0\nfor($i=0;$i-lt 10000000;$i++){$x+=$i}\n$sw.Stop()\n'
                'Write-Host "MS=$($sw.ElapsedMilliseconds)"\n'
                'Write-Host "RESULT=$x"\n'
            ),
            node, "cpu_stress", i
        ))
    else:
        all_tasks.append((
            'python3 -c "\nimport time\ns=time.time()\nx=0\nfor i in range(10000000):x+=i\nprint(\'MS=\'+str(int((time.time()-s)*1000)))\nprint(\'RESULT=\'+str(x))\n"\n',
            node, "cpu_stress", i
        ))

print("=" * 70)
print(f"BENCHMARK SUITE: {len(all_tasks)} tasks across {len(NODES)} nodes")
print(f"Tests: fibonacci | primes | hash | fileio | cpu_stress")
print("=" * 70)

# Submit all tasks concurrently
submit_start = time.time()
submit_results = {}

def do_submit(task_info):
    cmd, node, test, idx = task_info
    try:
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps({"command": cmd, "node_id": node}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        task_id = json.loads(resp.read())["data"]["task_id"]
        return (task_id, node, test, idx, None)
    except Exception as e:
        return (None, node, test, idx, str(e))

with ThreadPoolExecutor(max_workers=15) as pool:
    submit_results_list = list(pool.map(do_submit, all_tasks))

for task_id, node, test, idx, err in submit_results_list:
    submit_results[(node, test)] = {"task_id": task_id, "error": err}

submit_time = time.time() - submit_start
print(f"\nSubmitted {len([t for t in submit_results.values() if t['task_id']])}/{len(all_tasks)} tasks in {submit_time*1000:.0f}ms")

# Wait for all
print(f"\nWaiting for completion...")
wait_start = time.time()
completed = {}

for attempt in range(120):
    for (node, test), info in submit_results.items():
        task_id = info["task_id"]
        if not task_id or task_id in completed:
            continue
        
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"),
                timeout=10
            )
            detail = json.loads(resp.read())
            completed[(node, test)] = {
                "stdout": detail["data"].get("stdout", ""),
                "stderr": detail["data"].get("stderr", ""),
                "exit_code": detail["data"].get("exit_code"),
                "status": detail["data"]["status"]
            }
        except:
            pass
    
    if len(completed) == len(submit_results):
        break
    
    if attempt % 10 == 0:
        print(f"  [{attempt+1}/120] {len(completed)}/{len(submit_results)}")
        time.sleep(1)

total_time = time.time() - wait_start
print(f"All completed in {total_time:.1f}s")

# Print results
print("\n" + "=" * 70)
print("BENCHMARK RESULTS")
print("=" * 70)

tests = ["fibonacci", "primes", "hash", "fileio", "cpu_stress"]
for test in tests:
    print(f"\n--- {test.upper()} ---")
    for node in NODES:
        key = (node, test)
        if key not in completed:
            if key in submit_results and submit_results[key]["error"]:
                print(f"  {node}: SUBMIT FAILED ({submit_results[key]['error']})")
            else:
                print(f"  {node}: TIMEOUT")
            continue
        
        res = completed[key]
        if res["exit_code"] != 0:
            print(f"  {node}: FAILED (exit={res['exit_code']})")
            if res.get("stderr", "").strip():
                print(f"    {res['stderr'][:120]}")
            continue
        
        stdout = res["stdout"].strip()
        
        if test == "fibonacci":
            val = get_output(stdout, "RESULT")
            print(f"  {node}: F(34)={val}")
        elif test == "primes":
            val = get_output(stdout, "RESULT")
            print(f"  {node}: primes(100k)={val}")
        elif test == "hash":
            val = get_output(stdout, "RESULT")
            print(f"  {node}: SHA256({val[:32]}...)")
        elif test == "fileio":
            for line in stdout.split("\n"):
                if "WRITE_MS" in line:
                    print(f"  {node}: Write 50MB = {line.split('=')[1]}ms")
                elif "READ_MS" in line:
                    print(f"  {node}: Read 50MB = {line.split('=')[1]}ms")
                elif "TOTAL_BYTES" in line:
                    mb = int(line.split('=')[1]) / (1024*1024)
                    print(f"  {node}: Read {mb:.0f}MB")
        elif test == "cpu_stress":
            for line in stdout.split("\n"):
                if line.startswith("MS="):
                    print(f"  {node}: 10M iters = {line.split('=')[1]}ms")

# Summary
print("\n" + "=" * 70)
print("CLUSTER CAPABILITY SUMMARY")
print("=" * 70)
total = len(submit_results)
done = len(completed)
print(f"Tasks submitted: {total}")
print(f"Tasks completed: {done}/{total}")
print(f"Throughput: {done/total_time:.1f} tasks/sec")
print(f"\nNodes:")
for node in NODES:
    count = sum(1 for k in completed if k[0] == node)
    print(f"  {node}: {count} tasks completed")
print("=" * 70)
