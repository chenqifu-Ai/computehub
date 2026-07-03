"""Start OpenClaw Gateway - simple version"""
import subprocess, time, sys

oc = r"C:\ProgramData\nodejs\node-v24.16.0-win-x64\openclaw.cmd"
log = r"C:\temp\oc-gw.log"

# Kill old processes
subprocess.run("taskkill /f /im openclaw* 2>nul", shell=True, capture_output=True)

# Start gateway
p = subprocess.Popen([oc, "gateway"], stdout=open(log, "w"), stderr=subprocess.STDOUT,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
print(f"Started PID={p.pid}", flush=True)

time.sleep(8)

# Check port
r = subprocess.run("netstat -ano | findstr 18789", shell=True, capture_output=True, text=True)
if r.stdout.strip():
    print("GW_OK:", r.stdout.strip(), flush=True)
else:
    print("GW_FAIL", flush=True)
    try:
        print(open(log).read()[-500:], flush=True)
    except:
        print("No log", flush=True)