"""
ComputeHub Gateway API: 在 ECS 节点安装 ffmpeg
遵循 WIN-STD-001 v1.1 标准流程

用法: python3 install_ffmpeg_ecs.py
"""
import json, urllib.request, time

GW = "http://36.250.122.43:8282"
NODE = None  # 不指定则随机分配

def submit(cmd, timeout=30, node=None):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct"}
    if node:
        body["assigned_node"] = node
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, max_wait=60):
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(2)
        elapsed += 2
        try:
            resp = json.loads(urllib.request.urlopen(
                f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
            data = resp.get("data", {})
            if data.get("status") == "completed":
                return data
        except:
            pass
    return {}

def run(cmd, timeout=30, label=""):
    tid = submit(cmd, timeout)
    print(f"  ⏳ {label}: task_id={tid}")
    d = wait(tid, max_wait=timeout+10)
    ec = d.get("exit_code")
    out = (d.get("stdout") or "").strip()
    err = (d.get("stderr") or "").strip()
    print(f"     exit={ec} | stdout: {out[:200]}")
    if err:
        print(f"     stderr: {err[:200]}")
    return d

# ============ Phase 1: 预检 ============
print("=" * 60)
print("Phase 1: 预检清单")
print("=" * 60)

run("echo OK", 10, "节点在线")
run("whoami", 10, "当前用户")
run("sudo -n echo OK 2>&1", 10, "sudo权限检查")
run("uname -am", 10, "系统架构")

# 检查是否已安装
d = run("which ffmpeg 2>/dev/null; /usr/bin/ffmpeg -version 2>/dev/null | head -1; dpkg -l 2>/dev/null | grep ffmpeg", 10, "已安装检查")
already_installed = d.get("exit_code") == 0 and ("ffmpeg" in (d.get("stdout") or "").lower() or "ffmpeg" in (d.get("stderr") or "").lower())
if already_installed:
    print("\n✅ ffmpeg 已安装，跳过安装步骤")
    exit(0)

run("df -h / | tail -1", 10, "磁盘空间")

# ============ Phase 2: 安装 ============
print("\n" + "=" * 60)
print("Phase 2: 安装 ffmpeg")
print("=" * 60)

# 先 apt update
d = run("sudo apt-get update -qq", 120, "apt update")
if d.get("exit_code") != 0:
    print("❌ apt update 失败，中止")
    exit(1)

# 安装 ffmpeg
d = run("sudo apt-get install -y ffmpeg", 120, "安装 ffmpeg")
if d.get("exit_code") != 0:
    print("❌ 安装失败")
    exit(1)

# ============ Phase 3: 验证 ============
print("\n" + "=" * 60)
print("Phase 3: 安装验证")
print("=" * 60)

# 完整路径验证
d = run("/usr/bin/ffmpeg -version 2>&1 | head -1", 10, "完整路径验证")
if d.get("exit_code") == 0 and "ffmpeg" in (d.get("stdout") or "").lower():
    ver = (d.get("stdout") or "").strip()
    print(f"\n✅ ffmpeg 安装成功！版本: {ver}")
else:
    print(f"\n❌ 验证失败")
    exit(1)

# 功能测试：编码测试
d = run("ffmpeg -encoders 2>&1 | head -5", 15, "编码器列表")
if d.get("exit_code") == 0:
    print("✅ 编码器功能正常")

# 功能测试：查看支持格式
d = run("ffmpeg -formats 2>&1 | head -5", 15, "格式支持")
if d.get("exit_code") == 0:
    print("✅ 格式支持正常")

# which 确认
d = run("which ffmpeg", 10, "PATH验证")
print(f"   路径: {(d.get('stdout') or '').strip()}")

print("\n🎉 全部完成！ffmpeg 安装成功。")
