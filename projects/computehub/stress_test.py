#!/usr/bin/env python3
"""
ComputeHub Stress Test Script
- Submit N tasks concurrently
- Track completion rate, latency, errors
"""
import sys
import time
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

GW = "http://localhost:8282"

def log(msg):
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] {msg}")

def submit_task(task_id, cmd, node_id=None, priority=5):
    """Submit a single task to Gateway."""
    data = {
        "task_id": task_id,
        "command": cmd,
        "source_type": "stress-test",
        "priority": priority,
        "max_retries": 1,
        "timeout": 300,
    }
    if node_id:
        data["assigned_node"] = node_id
    payload = json.dumps(data).encode()
    url = f"{GW}/api/v1/tasks/submit"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read())
        elapsed = time.time() - start
        success = body.get("success", False)
        return {
            "task_id": task_id,
            "success": success,
            "elapsed_submit": round(elapsed, 3),
            "error": body.get("error", ""),
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "task_id": task_id,
            "success": False,
            "elapsed_submit": round(elapsed, 3),
            "error": str(e),
        }

def poll_progress(task_id, timeout=120):
    """Poll for task result."""
    url = f"{GW}/api/v1/tasks/progress?task_id={task_id}"
    deadline = time.time() + timeout
    last_output = ""
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            body = json.loads(resp.read())
            if body.get("success") and body.get("data"):
                d = body["data"]
                if d.get("stdout") != last_output:
                    last_output = d["stdout"]
                if not d.get("running") or d.get("exit_code") is not None:
                    return {
                        "completed": True,
                        "exit_code": d.get("exit_code", -1),
                        "stdout": d.get("stdout", "")[:200],
                        "stderr": d.get("stderr", "")[:200],
                        "duration": d.get("duration", ""),
                        "running": d.get("running", False),
                    }
        except:
            pass
        time.sleep(0.5)
    return {"completed": False, "timeout": True}

def run_phase(phase_num, count, cmds, node_id=None):
    """Phase: submit N tasks, collect results."""
    log(f"Phase {phase_num}: Submitting {count} tasks...")
    tasks = []
    for i in range(count):
        cmd = cmds[i % len(cmds)]
        tid = f"st-{phase_num}-{i+1:03d}"
        tasks.append((tid, cmd, node_id))

    results = []
    with ThreadPoolExecutor(max_workers=min(count, 20)) as pool:
        futs = {pool.submit(submit_task, tid, cmd, nid): (tid, i) for tid, cmd, nid in tasks}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            if not r["success"]:
                log(f"  ❌ {r['task_id']}: {r['error']}")

    success_count = sum(1 for r in results if r["success"])
    avg_submit = sum(r["elapsed_submit"] for r in results) / len(results) if results else 0
    log(f"  ✅ Submit: {success_count}/{count}  avg={avg_submit:.3f}s")

    # Poll all results
    if success_count > 0:
        log(f"  🔄 Polling {success_count} task results...")
        polled = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            futs = {pool.submit(poll_progress, r["task_id"]): r["task_id"] for r in results if r["success"]}
            for fut in as_completed(futs):
                polled.append(fut.result())

        completed = sum(1 for p in polled if p.get("completed"))
        timed_out = sum(1 for p in polled if p.get("timeout"))
        errors = sum(1 for p in polled if not p.get("completed") and not p.get("timeout"))
        avg_dur = 0
        durations = []
        for p in polled:
            if p.get("completed") and p.get("duration"):
                try:
                    d = p["duration"]
                    if "h" in d:
                        durations.append(float(d.replace("h",""))*3600)
                    elif "m" in d:
                        durations.append(float(d.replace("m",""))*60)
                    elif "s" in d:
                        durations.append(float(d.replace("s","")))
                    else:
                        durations.append(0)
                except:
                    pass
        if durations:
            avg_dur = sum(durations) / len(durations)

        log(f"  📊 Complete: {completed} ✅  Timeout: {timed_out} ⏰  Errors: {errors}")
        if durations:
            log(f"  ⏱  Avg exec duration: {avg_dur:.2f}s")

    return {
        "phase": phase_num,
        "total": count,
        "submitted_success": success_count,
        "submitted_fail": count - success_count,
        "avg_submit_latency": avg_submit,
        "polled_results": len(polled) if success_count > 0 else 0,
        "completed": completed if success_count > 0 else 0,
        "timed_out": timed_out if success_count > 0 else 0,
    }

def check_health():
    """Check gateway health."""
    try:
        resp = urllib.request.urlopen(f"{GW}/api/v2/health", timeout=5)
        body = json.loads(resp.read())
        return body
    except Exception as e:
        return {"error": str(e)}

def print_report(phases):
    """Print summary report."""
    print()
    print("=" * 70)
    print("  📊 STRESS TEST REPORT")
    print("=" * 70)
    total_tasks = sum(p["total"] for p in phases)
    total_success = sum(p["submitted_success"] for p in phases)
    total_completed = sum(p["completed"] for p in phases)
    print(f"  Total tasks submitted:  {total_tasks}")
    print(f"  Submit success rate:    {total_success}/{total_tasks} ({total_success/total_tasks*100:.1f}%)")
    print(f"  Tasks completed:        {total_completed}")
    print(f"  Complete rate:          {total_completed}/{total_success} ({total_completed/total_success*100:.1f}%)" if total_success > 0 else "  Complete rate:  N/A")
    if phases:
        avg_submit = sum(p["avg_submit_latency"] * p["total"] for p in phases) / total_tasks
        print(f"  Avg submit latency:     {avg_submit:.3f}s")
    print("=" * 70)
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: stress_test.py <phase1_count> [phase2_count] ...")
        print("Example: stress_test.py 10 50 100 200")
        print("Example: stress_test.py 50 --node worker-localhost")
        print("Example: stress_test.py 100 --full (10, 50, 100, 200)")
        sys.exit(1)

    args = sys.argv[1:]
    node_id = None
    full_mode = False

    if "--node" in args:
        idx = args.index("--node")
        if idx + 1 < len(args):
            node_id = args[idx + 1]
            args = args[:idx] + args[idx+2:]

    if "--full" in args:
        full_mode = True
        args = [a for a in args if a != "--full"]

    if full_mode or len(args) == 1:
        if full_mode:
            counts = [10, 50, 100, 200]
        else:
            counts = [int(args[0])]
    else:
        counts = [int(a) for a in args]

    cmds = [
        "echo hello-world",
        "python3 -c 'print(42)'",
        "uname -a",
        "df -h / | tail -1",
        "nproc",
        "echo 'stress-test ok'",
    ]

    print()
    print("=" * 70)
    print("  ComputeHub Stress Test")
    print(f"  Gateway: {GW}")
    print(f"  Node: {node_id or 'auto'}")
    print(f"  Phases: {counts}")
    print("=" * 70)
    print()

    # Pre-flight health check
    print("🔍 Pre-flight health check...")
    health = check_health()
    if "error" in health:
        log(f"  ❌ Gateway unreachable: {health['error']}")
        sys.exit(1)
    log(f"  ✅ Gateway healthy — nodes: {health.get('online_nodes', '?')}, gpu: {health.get('total_gpus', '?')}")

    phases = []
    for i, count in enumerate(counts, 1):
        print()
        phase_start = time.time()
        result = run_phase(i, count, cmds, node_id)
        phase_elapsed = time.time() - phase_start
        result["phase_elapsed"] = round(phase_elapsed, 2)
        log(f"  ⏱  Phase {i} took {phase_elapsed:.1f}s")
        phases.append(result)

    print_report(phases)

    # Final health check
    print("🔍 Post-test health check...")
    health = check_health()
    if "error" not in health:
        log(f"  ✅ Gateway still healthy — nodes: {health.get('online_nodes', '?')}, gpu: {health.get('total_gpus', '?')}")
    else:
        log(f"  ⚠️  Gateway unhealthy: {health['error']}")

if __name__ == "__main__":
    main()
