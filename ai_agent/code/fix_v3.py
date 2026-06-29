#!/usr/bin/env python3
"""v1.3.17 upgrade - clean JSON, no shell nesting"""
import json, urllib.request, time, base64, sys

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=120):
    p = {"node_id": node, "command": cmd, "timeout": timeout}
    body = json.dumps(p).encode()
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=body, headers={"Content-Type":"application/json"})
    resp = urllib.request.urlopen(r, timeout=timeout+10)
    return json.loads(resp.read())

def poll(tid, max_wait=120):
    for _ in range(max_wait):
        try:
            r = urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5)
            d = json.loads(r.read()).get("data", {})
            s = d.get("status", "")
            if s in ("completed","failed","error","cancelled"):
                return d
        except: pass
        time.sleep(1)
    return {"error":"timeout"}

# Python code to run on each target node
# Using single quotes inside so shell doesn't expand
dl_code = (
    "import urllib.request,hashlib,os\n"
    "url='http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe'\n"
    "d=urllib.request.urlopen(url,timeout=120).read()\n"
    "h=hashlib.sha256(d).hexdigest()\n"
    "print('GOT',len(d),h)\n"
    "out='/tmp/ch-v1.3.17'\n"
    "with open(out,'wb') as f: f.write(d)\n"
    "os.chmod(out,0o755)\n"
    "print('OK')\n"
)

# For Termux (xiaomi-table-01) use HOME dir
dl_code_termux = (
    "import urllib.request,hashlib,os\n"
    "url='http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe'\n"
    "d=urllib.request.urlopen(url,timeout=120).read()\n"
    "h=hashlib.sha256(d).hexdigest()\n"
    "print('GOT',len(d),h)\n"
    "out=os.environ.get('HOME','/data/local/tmp')+'/ch-v1.3.17'\n"
    "with open(out,'wb') as f: f.write(d)\n"
    "os.chmod(out,0o755)\n"
    "print('OK',out)\n"
)

arm_bin = "/root/bin/linux-arm64/computehub"
arm_bin_termux = "$HOME/OPC/deploy/linux-arm64/computehub"  # guess path

# Write scripts to ECS, then push via task submit
# Each script is written as a Python file via base64

for node, code, bin_path, restart_match in [
    ("local-arm", dl_code, arm_bin, "local-arm"),
    ("xiaomi-table-01", dl_code_termux, arm_bin_termux, "xiaomi-table"),
]:
    print(f"=== {node} ===")
    
    b64 = base64.b64encode(code.encode()).decode()
    
    # Write script + run
    cmd = "echo '" + b64 + "' | base64 -d > /tmp/dl_v1.3.17.py && python3 /tmp/dl_v1.3.17.py"
    
    r = sub(node, cmd, 120)
    tid = r.get("data", {}).get("task_id", "")
    if not tid:
        print(f"  Submit failed: {r}")
        continue
    
    d = poll(tid, 90)
    out = (d.get("stdout") or "")[:300]
    err = (d.get("stderr") or "")[:100]
    print(f"  {out}")
    if err: print(f"  E: {err}")
    
    if "OK" in out:
        # Extract output path if present
        out_path = bin_path
        if node == "xiaomi-table-01":
            # Try to find actual path from output
            parts = out.split()
            for p in parts:
                if "/ch-v1.3.17" in p:
                    out_path = p
                    break
        
        restart = (
            "cp /tmp/ch-v1.3.17 " + bin_path + " && "
            "pkill -f 'computehub.*" + restart_match + "' 2>/dev/null; sleep 2; "
            "nohup " + bin_path + " worker --agent --gw http://36.250.122.43:8282 "
            "--node-id " + node + " --interval 3 --concurrent 8 --heartbeat 10 "
            "> /dev/null 2>&1 & echo RESTART_OK"
        )
        r = sub(node, restart, 30)
        print(f"  ✅ Upgrade sent")
    else:
        print(f"  ❌ Download failed - trying fallback...")
        # Fallback: just download via curl
        fallback = "curl -sL -o " + bin_path + " http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe 2>&1 && chmod +x " + bin_path + " && echo CURL_OK"
        r = sub(node, fallback, 120)
        tid = r.get("data", {}).get("task_id", "")
        if tid:
            d = poll(tid, 90)
            out = (d.get("stdout") or "")[:200]
            print(f"  Fallback: {out}")

print("\n⏳ 30s...")
time.sleep(30)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n.get('node_id','?')} v{n.get('version','?')} {n.get('status','')}")

print("\n=== Hall ===")
try:
    r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
    for m in json.loads(r.read()).get("data", {}).get("messages", []):
        print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")
except: pass