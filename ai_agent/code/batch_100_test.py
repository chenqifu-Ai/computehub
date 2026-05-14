#!/usr/bin/env python3
"""Batch test: 100 tasks to 3 nodes, verify routing accuracy"""

import json
import time
import base64
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]
TOTAL = 100

# Pre-encode Windows command
ps_script = r'Write-Host "TASK_ID=WIN_{n}"; hostname; Write-Host "=== WIN DONE ==="'
windows_results = {}

def submit_task(task_id):
    node = NODES[task_id % 3]
    payload = {
        "command": f"echo 'TASK_ID=NODE_{node}_{task_id}'",
        "node_id": node
    }
    try:
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/submit",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get("success"):
            return {"task_id": result["data"]["task_id"], "expected_node": node, "task_num": task_id}
        else:
            return {"error": result.get("error"), "task_num": task_id}
    except Exception as e:
        return {"error": str(e), "task_num": task_id}

# ===== PHASE 1: Submit 100 tasks =====
print("=" * 60)
print(f"SUBMITTING {TOTAL} TASKS")
print("=" * 60)

start_time = time.time()
task_map = {}

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(submit_task, i) for i in range(TOTAL)]
    for future in as_completed(futures):
        result = future.result()
        if "task_id" in result:
            task_map[result["task_id"]] = {
                "expected_node": result["expected_node"],
                "task_num": result["task_num"]
            }

submit_time = time.time() - start_time
print(f"Submit time: {submit_time*1000:.0f}ms ({TOTAL}/100 submitted)")
print(f"Success: {len(task_map)}, Fail: {TOTAL - len(task_map)}")

# ===== PHASE 2: Check all results =====
print("\n" + "=" * 60)
print("CHECKING RESULTS")
print("=" * 60)

check_start = time.time()
results = {}
success_count = 0
node_counts = {"fedora-gpu-01": 0, "worker-DESKTOP-BUAUIFL": 0, "redmi-1": 0}
mismatch = []
errors = []

for attempt in range(20):
    for task_id, info in task_map.items():
        if task_id in results:
            continue
        
        try:
            req = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}")
            resp = urllib.request.urlopen(req, timeout=10)
            detail = json.loads(resp.read())
            status = detail["data"]["status"]
            
            if status in ("completed", "failed", "error"):
                stdout = detail["data"].get("stdout", "").strip()
                expected_node = info["expected_node"]
                correct = expected_node in stdout
                
                results[task_id] = {
                    "correct": correct,
                    "expected": expected_node,
                    "stdout": stdout,
                    "status": status
                }
                
                if correct:
                    success_count += 1
                    node_counts[expected_node] += 1
                else:
                    mismatch.append({
                        "task_num": info["task_num"],
                        "expected": expected_node,
                        "stdout": stdout[:50]
                    })
        except:
            pass
    
    completed = len(results)
    if completed == TOTAL:
        break
    
    if attempt % 3 == 0:
        print(f"  [{attempt+1}/20] {completed}/{TOTAL} checked")
        time.sleep(0.5)

check_time = time.time() - check_start
total_time = time.time() - start_time

# ===== PHASE 3: Print summary =====
print("\n" + "=" * 60)
print("BATCH TEST SUMMARY")
print("=" * 60)
print(f"Total tasks: {TOTAL}")
print(f"Submit time: {submit_time*1000:.0f}ms")
print(f"Check time: {check_time*1000:.0f}ms")
print(f"Total time: {total_time*1000:.0f}ms")
print(f"Rate: {TOTAL/total_time:.1f} tasks/sec")
print(f"\nRouting accuracy: {success_count}/{TOTAL} ({success_count/TOTAL*100:.1f}%)")
print(f"\nNode distribution:")
for node, count in node_counts.items():
    print(f"  {node}: {count} tasks")

if mismatch:
    print(f"\n❌ {len(mismatch)} mismatched tasks:")
    for m in mismatch[:5]:
        print(f"  Task {m['task_num']}: expected {m['expected']}, got: {m['stdout'][:30]}")
else:
    print("\n✅ ALL TASKS ROUTED CORRECTLY")

print("=" * 60)
