#!/usr/bin/env python3
"""Execute a PowerShell -EncodedCommand on a Windows worker node"""
import json, urllib.request, sys, time, base64

GW = "http://36.250.122.43:8282"

def encode_ps(cmd):
    """PowerShell -EncodedCommand via UTF-16LE base64"""
    return base64.b64encode(cmd.encode("utf-16le")).decode()

def submit(node_id, command, timeout=120):
    task = {"node_id": node_id, "command": command, "timeout": timeout, "priority": 10}
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps(task).encode(),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def get_detail(task_id):
    try:
        with urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={task_id}", timeout=10) as resp:
            return json.loads(resp.read())
    except:
        return None

node = sys.argv[1] if len(sys.argv) > 1 else "windows-home-01"
ps_cmd = sys.argv[2] if len(sys.argv) > 2 else "Write-Host hello"

# Use -EncodedCommand to avoid cmd & escaping issues
encoded = encode_ps(ps_cmd)
cmd = f"powershell -EncodedCommand {encoded}"

print(f"🚀 Submitting PS to {node}...")
result = submit(node, cmd, timeout=120)

if result.get("success"):
    task_id = result["data"]["task_id"]
    print(f"✅ Task: {task_id}")
    
    for i in range(40):
        time.sleep(3)
        d = get_detail(task_id)
        if d and d.get("success") and d.get("data"):
            status = d["data"].get("status", "?")
            print(f"  [{i+1}] {status}", flush=True)
            if status in ("completed", "failed"):
                print(f"\n{'='*60}")
                print(f"Exit: {d['data'].get('exit_code', '?')}")
                so = d["data"].get("stdout", "")
                se = d["data"].get("stderr", "")
                if so: print(f"Stdout:\n{so[:1000]}")
                if se: print(f"Stderr:\n{se[:500]}")
                print(f"{'='*60}")
                sys.exit(0 if d["data"].get("success") else 1)
    print("⚠️  Timeout")
    sys.exit(1)
else:
    print(f"❌ {result}")
    sys.exit(1)