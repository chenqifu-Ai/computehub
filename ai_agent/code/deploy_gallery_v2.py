#!/usr/bin/env python3
"""
部署新版 Gallery v2 到 ECS
步骤: 备份 → 替换 → 编译 → 重启 → 验证
"""
import subprocess, sys, time

REMOTE = "computehub@36.250.122.43"
SSH_ARGS = ["-o", "BatchMode=yes", "-i", "/root/.ssh/id_ed25519_computehub", REMOTE]

def ssh(cmd):
    r = subprocess.run(["ssh"] + SSH_ARGS + [cmd], capture_output=True, text=True, timeout=60)
    if r.returncode != 0 and r.stderr.strip():
        msg = r.stderr.strip()[:200]
        if not msg.startswith("Warning"):
            print(f"  ^^^ {msg}")
    return r.stdout.strip()

def main():
    print("=== Step 1: 备份旧 gallery.go ===")
    ssh("cp /home/computehub/src/src/gateway/gallery.go /home/computehub/src/src/gateway/gallery.go.bak")
    print("  backup: gallery.go.bak")

    print("=== Step 2: 替换新文件 ===")
    ssh("cp /home/computehub/src/src/gateway/gallery2.go /home/computehub/src/src/gateway/gallery.go")
    print("  replaced: gallery.go")

    print("=== Step 3: 编译 ===")
    r = ssh("cd /home/computehub/src && CGO_ENABLED=0 go build -ldflags=-s -w -o /home/computehub/computehub ./cmd/gateway/ 2>&1")
    if "error" in r.lower() and "error" in r:
        print(f"  FAIL: {r}")
        ssh("cp /home/computehub/src/src/gateway/gallery.go.bak /home/computehub/src/src/gateway/gallery.go")
        sys.exit(1)
    sz = ssh("ls -lh /home/computehub/computehub | awk \'{print $5}\'")
    print(f"  build OK: {sz}")

    print("=== Step 4: 重启 ===")
    old_pid = ssh("ps aux | grep /home/computehub/computehub | grep -v grep | awk \'{print $2}\' | head -1")
    if old_pid:
        print(f"  kill old PID: {old_pid}")
        ssh(f"kill {old_pid}")
        time.sleep(1)
    ssh("nohup /home/computehub/computehub > /home/computehub/gateway.log 2>&1 &")
    time.sleep(2)

    print("=== Step 5: 验证 ===")
    new_pid = ssh("ps aux | grep /home/computehub/computehub | grep -v grep | awk \'{print $2}\' | head -1")
    if new_pid:
        print(f"  new PID: {new_pid}")
    else:
        log = ssh("tail -10 /home/computehub/gateway.log").replace("\n", " ")
        print(f"  FAIL: {log}")
        sys.exit(1)

    time.sleep(1)
    code = ssh("curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8282/gallery")
    print(f"  Gallery page HTTP: {code}")
    data = ssh("curl -s http://localhost:8282/api/v1/gallery?format=json | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'total={d.get(\\\"total\\\",0)} tasks={len(d.get(\\\"tasks\\\",[]))}')\"")
    print(f"  Gallery API: {data}")

    print()
    print("Done! http://36.250.122.43:8282")

if __name__ == "__main__":
    main()
