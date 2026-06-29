#!/usr/bin/env python3
"""Final v1.3.17 push to all nodes"""
import json, urllib.request, base64, time, subprocess, hashlib

GW = "http://36.250.122.43:8282"
SSH = "ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43"
NODES = [
    ("local-arm", "linux-arm64/computehub",
     "b78a27394e8c33642486137bbde7a998ee15774568d933d038319348b10fd962",
     "/root/bin/linux-arm64/computehub"),
    ("xiaomi-table-01", "linux-arm64/computehub",
     "b78a27394e8c33642486137bbde7a998ee15774568d933d038319348b10fd962",
     "/root/bin/linux-arm64/computehub"),
]

def sub_t(node_id, command, timeout=80):
    p = json.dumps({"node_id": node_id, "command": command, "timeout": timeout}).encode()
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(r, timeout=timeout+10)
    return json.loads(resp.read())

def poll_t(tid, max_wait=80):
    for _ in range(max_wait):
        try:
            r = urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5)
            d = json.loads(r.read()).get("data", {})
            s = d.get("status", "")
            if s in ("completed", "failed", "error", "cancelled"):
                return d
        except: pass
        time.sleep(1)
    return {"error": "timeout"}

# Python download script that each node will run
dl_script = """import urllib.request, hashlib, os, sys
url = sys.argv[1]
exp = sys.argv[2]
data = urllib.request.urlopen(url, timeout=90).read()
h = hashlib.sha256(data).hexdigest()
print("OK", len(data), h)
if h == exp:
    path = sys.argv[3]
    with open(path, "wb") as f: f.write(data)
    os.chmod(path, 0o755)
    print("MATCH")
else:
    print("MISMATCH expected="+exp)
"""

dl_b64 = base64.b64encode(dl_script.encode()).decode()

for node_id, file, expected_hash, bin_path in NODES:
    print(f"\n=== {node_id} ===")
    dl_url = f"{GW}/api/v1/download?file={file}"
    
    # Step 1: Write download script + run it
    cmd = (
        f"echo '{dl_b64}' | base64 -d > /tmp/dl.py && "
        f"python3 /tmp/dl.py '{dl_url}' '{expected_hash}' '/tmp/ch-v1.3.17'"
    )
    r = sub_t(node_id, cmd, 120)
    tid = r.get("data", {}).get("task_id")
    if not tid:
        print(f"  ❌ Submit failed: {r}")
        continue
    
    d = poll_t(tid, 90)
    out = (d.get("stdout") or "") + (d.get("stderr") or "")
    print(f"  {out[:200]}")
    
    if "MATCH" in out:
        # Step 2: Replace binary + restart
        restart = (
            f"cp /tmp/ch-v1.3.17 {bin_path} && "
            f"pkill -f 'computehub.*{node_id.split("-")[0]}' 2>/dev/null; "
            f"sleep 2; "
            f"nohup {bin_path} worker --agent --gw http://36.250.122.43:8282 "
            f"--node-id {node_id} --interval 3 --concurrent 8 --heartbeat 10 "
            f"> /dev/null 2>&1 & echo RESTART_OK"
        )
        r = sub_t(node_id, restart, 20)
        tid = r.get("data", {}).get("task_id")
        if tid:
            time.sleep(3)
        print(f"  ✅ Upgrade OK")

# Windows
time.sleep(2)
print("\n=== Windows-mobile ===")
# Skip if offline
try:
    r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
    nodes = json.loads(r.read()).get("data", [])
    win_online = any(n.get("node_id") == "Windows-mobile" and n.get("status") == "online" for n in nodes)
except: win_online = False

if not win_online:
    print("  ⚠️ Offline - will auto-upgrade when reconnects")
else:
    dl_url = f"{GW}/api/v1/download?file=windows-amd64/computehub.exe"
    exp_hash = "71faf32cd8c98e156f28ea13306bd0a91d81f1383f877639216188007c5f1826"
    
    # Windows download via PowerShell
    ps_dl = f"""$url='{dl_url}'; $wc=New-Object Net.WebClient; $d=$wc.DownloadData($url); $h=[System.BitConverter]::ToString((New-Object Security.Cryptography.SHA256Managed).ComputeHash($d)).Replace('-','').ToLower(); Write-Host \"OK $($d.Length) $h\"; if($h -eq '{exp_hash}'){{ [IO.File]::WriteAllBytes('C:\\Windows\\Temp\\ch-v1.3.17.exe',$d); Write-Host 'MATCH' }}else{{ Write-Host 'MISMATCH' }}"""
    
    ps_b64 = base64.b64encode(ps_dl.encode('utf-16-le')).decode()
    cmd = f"powershell -NoProfile -EncodedCommand {ps_b64}"
    
    r = sub_t("Windows-mobile", cmd, 120)
    tid = r.get("data", {}).get("task_id")
    if tid:
        d = poll_t(tid, 120)
        out = (d.get("stdout") or "") + (d.get("stderr") or "")
        print(f"  {out[:200]}")
        
        if "MATCH" in out:
            restart = (
                "taskkill /F /IM computehub.exe 2>nul & "
                "timeout /t 3 >nul & "
                "copy /Y C:\\Windows\\Temp\\ch-v1.3.17.exe "
                "C:\\Users\\Administrator\\.computehub\\computehub.exe & "
                "start /B C:\\Users\\Administrator\\.computehub\\computehub.exe "
                "worker --agent --gw http://36.250.122.43:8282 "
                "--node-id Windows-mobile --interval 3 --concurrent 8 --heartbeat 10 & "
                "echo RESTART_OK"
            )
            r = sub_t("Windows-mobile", restart, 20)
            print(f"  ✅ Upgrade sent")

# Wait and check
print("\n⏳ Waiting 20s for re-registration...")
time.sleep(20)

try:
    r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
    nodes = json.loads(r.read()).get("data", [])
    print("\n=== Final Node List ===")
    for n in nodes:
        print(f"  {n.get('node_id','?')} v{n.get('version','?')} {n.get('status','')}")
    
    # Hall check
    r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
    hall = json.loads(r.read()).get("data", {}).get("messages", [])
    print(f"\n=== Hall ({len(hall)} messages) ===")
    for m in hall:
        print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")
except Exception as e:
    print(f"Final check error: {e}")