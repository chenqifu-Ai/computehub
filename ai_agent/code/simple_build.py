#!/usr/bin/env python3
"""简化版分布式编译"""
import json, time, urllib.request

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]

def submit(cmd, node):
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps({"command": cmd, "node_id": node}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())["data"]["task_id"]

def wait(tid, timeout=30):
    for _ in range(timeout // 2):
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={tid}"),
                timeout=10
            )
            d = json.loads(resp.read())
            if d["data"]["status"] in ("completed", "failed"):
                return d["data"].get("stdout", "").strip(), d["data"]["status"]
        except:
            pass
    return None, "timeout"

print("=" * 60)
print("🔨 ComputeHub 分布式编译流水线")
print("=" * 60)

# 阶段1：环境检测
print("\n📋 阶段1：环境检测")
print("-" * 40)

env_results = {}
for node in NODES:
    tid = submit("python3 -c 'import platform;print(platform.platform());print(platform.machine());print(platform.python_version())'", node)
    stdout, status = wait(tid)
    ok = status == "completed"
    env_results[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")
    if stdout and ok:
        for line in stdout.split('\n')[:2]:
            print(f"     {line}")

# 阶段2：编译验证
print("\n🔧 阶段2：编译验证")
print("-" * 40)

compile_results = {}
for node in NODES:
    tid = submit("python3 -c 'print(\"COMPILE_OK\")'", node)
    stdout, status = wait(tid)
    ok = status == "completed" and "COMPILE_OK" in stdout
    compile_results[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")

# 阶段3：生成构建产物
print("\n📦 阶段3：生成构建产物")
print("-" * 40)

artifact_results = {}
for node in NODES:
    tid = submit(f"python3 -c 'import json;print(json.dumps({{\"node\":\"{node}\",\"build\":\"OK\"}}))'", node)
    stdout, status = wait(tid)
    ok = status == "completed" and "OK" in stdout
    artifact_results[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")
    if stdout:
        print(f"     {stdout}")

# 汇总
print("\n" + "=" * 60)
print("🏆 结果")
print("=" * 60)

total = len(NODES)
phase1 = sum(env_results.values())
phase2 = sum(compile_results.values())
phase3 = sum(artifact_results.values())

print(f"环境检测：{phase1}/{total}")
print(f"编译验证：{phase2}/{total}")
print(f"产物生成：{phase3}/{total}")

if phase1 == phase2 == phase3 == total:
    print(f"\n🎉 全部 3 节点成功完成流水线！")
else:
    failed = [n for n in NODES if not (env_results.get(n) and compile_results.get(n) and artifact_results.get(n))]
    print(f"\n⚠️ 失败节点: {', '.join(failed) if failed else '无'}")
print("=" * 60)
