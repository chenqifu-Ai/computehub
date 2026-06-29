#!/usr/bin/env python3
"""v1.3.17 push - corrected download URLs"""
import json, urllib.request, time, base64

GW = "http://36.250.122.43:8282"

def sub(node, cmd, timeout=120):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout}).encode()
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p, headers={"Content-Type":"application/json"})
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

# Step 1: Get base64 of the download Python script
dl_py = "import urllib.request,u,hashlib as h;d=urllib.request.urlopen('URL',timeout=120).read();print(len(d),h.sha256(d).hexdigest());open('OUT','wb').write(d);import os;os.chmod('OUT',0o755);print('OK')"
dl_b64 = base64.b64encode(dl_py.encode()).decode()

arm_url = "http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe"
arm_bin = "/root/bin/linux-arm64/computehub"

for node in ["local-arm", "xiaomi-table-01"]:
    print(f"\n=== {node} ===")
    
    dl_code = dl_py.replace("URL", arm_url).replace("OUT", "/tmp/ch-v1.3.17")
    # Encode the resolved script
    encoded = base64.b64encode(dl_code.encode()).decode()
    cmd = f"python3 -c \"$(echo '{encoded}' | base64 -d)\""
    
    r = sub(node, cmd, 120)
    tid = r.get("data", {}).get("task_id", "")
    if not tid:
        print(f"  Submit failed: {r}")
        continue
    
    d = poll(tid, 90)
    out = (d.get("stdout") or "") + (d.get("stderr") or "")
    print(f"  DL: {out[:200]}")
    
    if "OK" in out:
        restart = (
            f"cp /tmp/ch-v1.3.17 {arm_bin} && "
            f"pkill -f 'computehub.*{node.split('-')[0]}' 2>/dev/null; sleep 2; "
            f"nohup {arm_bin} worker --agent --gw http://36.250.122.43:8282 "
            f"--node-id {node} --interval 3 --concurrent 8 --heartbeat 10 "
            f"> /dev/null 2>&1 & echo RESTART_OK"
        )
        r = sub(node, restart, 20)
        tid2 = r.get("data", {}).get("task_id", "")
        print(f"  Restart sent: {tid2[:25]}")
        time.sleep(3)
    else:
        print(f"  ❌ Download failed")

# Windows
print(f"\n=== Windows-mobile ===")
try:
    r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
    nd = json.loads(r.read()).get("data", [])
    win_online = any(n.get("node_id") == "Windows-mobile" and n.get("status") == "online" for n in nd)
except:
    win_online = False

if win_online:
    win_url = "http://36.250.122.43:8282/api/v1/download?file=computehub-windows-amd64.exe"
    win_cmd = (
        'powershell -NoProfile -Command '
        '"{0}"'.format(
            '$wc=New-Object Net.WebClient; '
            f'$d=$wc.DownloadData("{win_url}"); '
            '$f=[IO.File]::WriteAllBytes("C:\\Windows\\Temp\\ch-v1.3.17.exe",$d); '
            'Write-Output ($d.Length,"bytes"); Write-Output "OK"'
        )
    )
    # Simpler: just use net use download
    win_cmd = (
        f'curl -sL -o C:\\Windows\\Temp\\ch-v1.3.17.exe "{win_url}" '
        f'2>&1 && echo OK || echo FAIL'
    )
    r = sub("Windows-mobile", win_cmd, 120)
    tid = r.get("data", {}).get("task_id", "")
    if tid:
        d = poll(tid, 120)
        out = (d.get("stdout") or "")[:200]
        print(f"  DL: {out}")
        if "OK" in out:
            restart = (
                'taskkill /F /IM computehub.exe 2>nul & timeout /t 3 >nul & '
                'copy /Y C:\\Windows\\Temp\\ch-v1.3.17.exe '
                'C:\\Users\\Administrator\\.computehub\\computehub.exe & '
                'start /B C:\\Users\\Administrator\\.computehub\\computehub.exe worker --agent '
                '--gw http://36.250.122.43:8282 --node-id Windows-mobile '
                '--interval 3 --concurrent 8 --heartbeat 10 & echo RESTART_OK'
            )
            r = sub("Windows-mobile", restart, 20)
            print(f"  Restart sent")
else:
    print("  Offline, skip")

print("\n⏳ Waiting 20s for re-registration...")
time.sleep(20)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n.get('node_id','?')} v{n.get('version','?')} {n.get('status','')}")

print("\n=== Hall ===")
r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
for m in json.loads(r.read()).get("data", {}).get("messages", []):
    print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")