#!/usr/bin/env python3
"""ComputeHub Gateway 功能测试报告"""
import json, urllib.request, sys, platform
from datetime import datetime

HOST = "http://localhost:8282"
passed, failed, warnings = 0, 0, 0

def req(method, path, body=None):
    url = HOST + path
    data = json.dumps(body).encode() if body else None
    try:
        r = urllib.request.Request(url, data=data, method=method,
            headers={"Content-Type": "application/json"} if body else {})
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return json.loads(body)
        except:
            return {"success": False, "error": f"HTTP {e.code}: {body.decode(errors='replace')[:100]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test(name, fn):
    global passed, failed
    try:
        ok, detail = fn()
        if ok:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name} — {detail}")
            failed += 1
    except Exception as e:
        print(f"  ❌ {name} — exception: {e}")
        failed += 1

def warn(msg):
    global warnings
    print(f"  ⚠️  {msg}")
    warnings += 1

print("╔══════════════════════════════════════════════╗")
print("║  ComputeHub Gateway 功能测试报告              ║")
print("╚══════════════════════════════════════════════╝")
print(f"\n📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🎯 目标: {HOST}")

# ═══════ 1. 基础 API ═══════
print("\n━━━ 1. 基础 API ━━━")
def check_health():
    r = req("GET", "/api/health")
    return r.get("success", False), f'data={r.get("data","?")}'
test("Health 端点", check_health)

def check_status():
    r = req("GET", "/api/status")
    # Status endpoint returns data directly (no success wrapper)
    ok = "kernel" in r and r.get("kernel", {}).get("status") == "RUNNING"
    return ok, f'kernel={r.get("kernel",{}).get("status","?")}'
test("Status 端点", check_status)

# ═══════ 2. Video API ═══════
print("\n━━━ 2. Video API ━━━")
def check_video_list():
    r = req("GET", "/api/v1/video/list")
    return r.get("success", False), f'tasks={len(r.get("data",[]))}'
test("GET /api/v1/video/list", check_video_list)

def check_video_list_post():
    r = req("POST", "/api/v1/video/list")
    return not r.get("success", True), 'POST to list should fail'
test("POST /api/v1/video/list 拒绝", check_video_list_post)

def check_video_progress_no_task():
    r = req("GET", "/api/v1/video/progress")
    ok = not r.get("success", True)
    err = r.get("error", "")
    return ok, f'error={err}'
test("GET /api/v1/video/progress (缺task_id)", check_video_progress_no_task)

def check_video_progress_invalid():
    r = req("GET", "/api/v1/video/progress?task_id=test_123")
    return r.get("success", False), f'stage={r.get("data",{}).get("stage","?")}'
test("GET /api/v1/video/progress (无效task)", check_video_progress_invalid)

def check_video_generate_empty():
    r = req("POST", "/api/v1/video/generate", {})
    ok = not r.get("success", True)
    err = r.get("error", "")
    return ok, f'error={err}'
test("POST /api/v1/video/generate (空body校验)", check_video_generate_empty)

def check_video_generate_valid():
    r = req("POST", "/api/v1/video/generate", {"doc_path": "/tmp/test.docx"})
    ok = r.get("success", False)
    task_id = r.get("data", {}).get("task_id", "?") if ok else "N/A"
    return ok, f'task_id={task_id}'
test("POST /api/v1/video/generate (正确参数)", check_video_generate_valid)

# ═══════ 3. 系统状态 ═══════
print("\n━━━ 3. 系统状态信息 ━━━")
status = req("GET", "/api/status")
if "kernel" in status or status.get("success"):
    nm = status.get("nodeManager", {})
    kn = status.get("kernel", {})
    print(f"  🖥  节点: {nm.get('online_nodes',0)}/{nm.get('total_nodes',0)} 在线")
    print(f"  📋 任务: {nm.get('active_tasks',0)} 活跃 / {nm.get('total_tasks',0)} 总计")
    print(f"  ⏱  运行时间: {status.get('uptime','?')}")
    print(f"  ⚙️  调度器: {kn.get('status','?')} (队列深度 {kn.get('queue_depth',0)})")
else:
    warn(f"无法获取状态")

# ═══════ 4. 环境信息 ═══════
print("\n━━━ 4. 环境信息 ━━━")
print(f"  💻 系统: {platform.system()} {platform.machine()}")
print(f"  🐍 Python: {sys.version.split()[0]}")

pkgs = [
    ("edge-tts", "edge_tts"),
    ("Pillow", "PIL"),
    ("PyPDF2", "PyPDF2"),
    ("pydub", "pydub"),
    ("moviepy", "moviepy"),
    ("opencv-python", "cv2"),
    ("python-docx", "docx"),
    ("pypdf", "pypdf")
]
installed, missing = [], []
for display_name, import_name in pkgs:
    try:
        __import__(import_name)
        installed.append(display_name)
    except ImportError:
        missing.append(display_name)

if installed:
    print(f"  ✅ pip 已安装: {', '.join(installed)}")
if missing:
    print(f"  ⚠️  pip 未安装: {', '.join(missing)}")

# ═══════ 结果 ═══════
print(f"\n━━━ 结果汇总 ━━━")
total = passed + failed
print(f"  ✅ 通过: {passed}/{total}")
print(f"  ❌ 失败: {failed}/{total}")
pct = (passed / total * 100) if total else 0
print(f"  📊 通过率: {pct:.0f}%")
print(f"\n{'🎉 全部测试通过!' if failed == 0 else '🔧 部分测试失败，需要修复'}")
