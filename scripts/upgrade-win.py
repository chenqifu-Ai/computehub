#!/usr/bin/env python3
"""升级 windows-mobile — 全程 Python 构造 JSON，零 shell 转义"""
import json, urllib.request, time, sys, base64

GW = sys.argv[1] if len(sys.argv) > 1 else "http://36.250.122.43:8282"
NODE = "Windows-mobile"

def submit(node, command, timeout=120):
    task_id = f"up-{int(time.time()*1000)}"
    task = {"task_id": task_id, "node_id": node, "command": command, "timeout": timeout}
    body = json.dumps(task).encode()
    req = urllib.request.Request(f"{GW}/api/v1/tasks/submit", data=body,
                                 headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    if not result.get("success"):
        raise Exception(f"Submit failed: {result}")
    return task_id

def wait_task(task_id, node, timeout=30):
    """轮询直到任务完成或超时"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        req = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}&node_id={node}")
        resp = urllib.request.urlopen(req, timeout=10)
        detail = json.loads(resp.read()).get("data", {})
        status = detail.get("status", "?")
        if status in ("completed", "failed", "cancelled"):
            return detail
        time.sleep(2)
    # 最后再查一次
    req = urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}&node_id={node}")
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read()).get("data", {})

# ====== Step 1: 下载新 binary ======
print("🎯 Step 1: 下载 computehub v1.3.4 (11MB)...")
DL_CMD = f"cmd /c curl -sL -o C:\\tmp\\ch_new.exe {GW}/api/v1/files/computehub-windows-amd64.exe && echo DL_OK"
t1 = submit(NODE, DL_CMD, 120)
print(f"   任务: {t1}")
d1 = wait_task(NODE, t1, 60)
print(f"   状态: {d1.get('status','?')} exit={d1.get('exit_code','?')}")
print(f"   STDOUT: {d1.get('stdout','(empty)').strip()[:200]}")

if d1.get("status") != "completed" or d1.get("exit_code") != 0:
    print("❌ 下载失败")
    sys.exit(1)

# ====== Step 2: 写重启批处理 + 启动 ======
print("\n🎯 Step 2: 写重启脚本...")
BAT_CMD = (
    'cmd /c '
    'echo @echo off > C:\\tmp\\rb.bat && '
    'echo ping -n 4 127.0.0.1 >> C:\\tmp\\rb.bat && '
    'echo taskkill /f /im computehub.exe >> C:\\tmp\\rb.bat && '
    'echo ping -n 3 127.0.0.1 >> C:\\tmp\\rb.bat && '
    'echo move /y C:\\tmp\\ch_new.exe C:\\computehub.exe >> C:\\tmp\\rb.bat && '
    'echo C:\\computehub.exe worker --gw ' + GW + ' --node-id Windows-mobile --interval 3 --concurrent 4 --heartbeat 10 >> C:\\tmp\\rb.bat && '
    'echo BAT_READY'
)
t2 = submit(NODE, BAT_CMD, 30)
print(f"   任务: {t2}")
d2 = wait_task(NODE, t2, 20)
print(f"   状态: {d2.get('status','?')} exit={d2.get('exit_code','?')}")
print(f"   STDOUT: {d2.get('stdout','(empty)').strip()[:200]}")

# ====== Step 3: 触发重启（独立进程） ======
print("\n🎯 Step 3: 触发重启...")
TRIG_CMD = "cmd /c start /b C:\\tmp\\rb.bat && echo TRIGGERED"
t3 = submit(NODE, TRIG_CMD, 15)
d3 = wait_task(NODE, t3, 12)
print(f"   触发结果: {d3.get('stdout','?').strip()[:100]}")

print("\n⏳ 等待 50 秒让 Worker 重启上线...")
time.sleep(50)

# ====== 验证 ======
req = urllib.request.Request(f"{GW}/api/v1/nodes/list")
resp = urllib.request.urlopen(req, timeout=10)
nodes = json.loads(resp.read()).get("data", [])
for n in nodes:
    icon = "📡" if n["node_id"] == NODE else "  "
    print(f"   {icon} {n['node_id']:25s} {n['status']}")

# 检查版本
time.sleep(5)
VER_CMD = "cmd /c C:\\computehub.exe version"
t4 = submit(NODE, VER_CMD, 15)
d4 = wait_task(NODE, t4, 15)
version = d4.get("stdout", "?").strip()
print(f"\n🔖 版本: {version}")
print("✅ 升级成功！" if "1.3.4" in version else f"⚠️ 仍是 {version}")