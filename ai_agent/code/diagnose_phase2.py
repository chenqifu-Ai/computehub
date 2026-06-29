#!/usr/bin/env python3
"""分析 Phase 2 copy 失败的原因 + 验证 Gallery/AI 测试失败的原因"""
import base64, json, urllib.request, time

GW = "http://36.250.122.43:8282"
NODE = "windows-home-01"

def ps(cmd):
    b64 = base64.b64encode(cmd.encode("utf-16le")).decode()
    return f"powershell -EncodedCommand {b64}"

def submit(cmd, timeout=10):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct", "assigned_node": NODE}
    req = urllib.request.Request(GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data",{}).get("task_id","")

def poll(tid, max_wait=15):
    for i in range(max_wait):
        time.sleep(1)
        resp = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return None

# 分析1: 检查 copy 文件时 Worker 是否占用了 computehub.exe
print("=== 分析1: Worker 持有 computehub.exe 文件锁 ===")
# 查 Worker PID 打开的文件句柄
tid = submit(ps("(Get-Process -Id (Get-NetTCPConnection -LocalPort 8383).OwningProcess).ProcessName"), 10)
d = poll(tid, 12)
if d:
    print("  8383 端口进程名: " + (d.get("stdout","").strip() or "未知"))

# 分析2: 确认 copy 失败是因为文件被Worker占用
print()
print("=== 分析2: copy 失败根因 ===")
tid = submit("cmd /c copy /Y D:\\computehub\\computehub.exe D:\\computehub\\copy_test.exe 2>&1 & echo DONE")
d = poll(tid, 10)
if d:
    print("  copy 结果: " + (d.get("stderr","") or d.get("stdout","")).strip()[:200])
    
# 清理
tid = submit("cmd /c if exist D:\\computehub\\copy_test.exe del D:\\computehub\\copy_test.exe", 5)
poll(tid, 8)

# 分析3: 模拟 Gallery 测试 - 检查新 Gateway 启动要多长时间
print()
print("=== 分析3: Gateway 启动时间测试 ===")
start = time.time()
tid = submit("cmd /c curl -s -o NUL -w %{http_code} http://localhost:8282/gallery", 10)
d = poll(tid, 12)
elapsed = time.time() - start
if d:
    print("  当前 Gateway 的 Gallery 响应耗时: {:.1f}s, HTTP: {}".format(elapsed, (d.get("stdout","").strip() or "-")))

# 分析4: 检查 computehub.new.exe 内容是否与主文件一致
print()
print("=== 分析4: 文件一致性 ===")
tid = submit(ps("(Get-FileHash D:\\computehub\\computehub.exe -Algorithm SHA256).Hash"))
d = poll(tid, 12)
h1 = (d.get("stdout","") or "").strip() if d else ""
tid = submit(ps("(Get-FileHash D:\\computehub\\computehub.new.exe -Algorithm SHA256).Hash"))
d = poll(tid, 12)
h2 = (d.get("stdout","") or "").strip() if d else ""
print("  computehub.exe SHA256: " + h1[:64])
print("  computehub.new.exe SHA256: " + h2[:64])
print("  文件一致: " + ("✅" if h1 and h2 and h1[:64] == h2[:64] else "❌ 不一致"))

# 分析5: 备份文件来源
print()
print("=== 分析5: computehub.old.exe 备份 ===")
tid = submit(ps("(Get-FileHash D:\\computehub\\computehub.old.exe -Algorithm SHA256).Hash"))
d = poll(tid, 12)
h3 = (d.get("stdout","") or "").strip() if d else ""
print("  computehub.old.exe SHA256: " + h3[:64])
print("  备份是否等于当前binary: " + ("✅" if h1 and h3 and h1[:64] == h3[:64] else "❌ 不一致"))
print("  备份是否等于新binary: " + ("✅" if h2 and h3 and h2[:64] == h3[:64] else "❌ 不一致"))