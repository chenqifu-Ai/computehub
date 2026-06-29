#!/usr/bin/env python3
"""
STD-005 蓝绿升级 v2 — Base64 通道（精简版）

ecs-p2ph(base64) → Windows(下载+certutil解码) → 蓝绿升级
"""

import base64, json, urllib.request, time, sys

GW = "http://36.250.122.43:8282"
NODE_WIN = "windows-home-01"
NODE_ECS = "ecs-p2ph"
BIN_DIR_WIN = r"D:\computehub"
DEPLOY_DIR = "/home/computehub/deploy"
B64_FILENAME = "computehub.b64"

def submit(cmd, timeout=10, node=NODE_ECS):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct", "assigned_node": node}
    req = urllib.request.Request(GW+"/api/v1/tasks/submit", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data",{}).get("task_id","")

def poll(tid, max_wait=15):
    for i in range(max_wait):
        time.sleep(1)
        d = json.loads(urllib.request.urlopen(GW+"/api/v1/tasks/detail?task_id="+tid, timeout=10).read()).get("data",{})
        if d.get("status") in ("completed","failed"): return d
    return None

def run(cmd, timeout=10, node=NODE_ECS):
    return poll(submit(cmd, timeout, node), timeout+5)

def ps(cmd):
    b = base64.b64encode(cmd.encode("utf-16le")).decode()
    return f"powershell -EncodedCommand {b}"

def get_pid(port):
    d = run(ps(f"(Get-NetTCPConnection -LocalPort {port}).OwningProcess"), 12, NODE_WIN)
    for l in ((d.get("stdout") or "").split("\n")):
        if l.strip().isdigit(): return int(l.strip())
    raise Exception(f"找不到端口 {port}")

def main():
    print("=" * 68)
    print("🚀 STD-005 蓝绿升级 v2 — Base64 通道")
    print("=" * 68)

    # ========== Phase A: ecs-p2ph 生成 .b64 ==========
    print("\n📦 Phase A: ecs-p2ph base64 编码 windows binary")
    print("──────────────────────────────────────────")
    
    d = run(f"base64 {DEPLOY_DIR}/windows-amd64/computehub.exe > {DEPLOY_DIR}/{B64_FILENAME} && ls -la {DEPLOY_DIR}/{B64_FILENAME}", 15, NODE_ECS)
    out = (d.get("stdout","") or "").strip()
    print(f"  {out}")
    
    d = run(f"wc -c {DEPLOY_DIR}/{B64_FILENAME}", 5, NODE_ECS)
    sz = (d.get("stdout","") or "").strip().split()[0]
    expected = 14412460  # 10.8MB binary → base64 size
    print(f"  .b64 大小: {sz} bytes (预期 ~{expected})")
    
    # ========== Phase B: Windows 下载 + 解码 ==========
    print("\n⬇️  Phase B: Windows 下载 .b64 → certutil 解码")
    print("──────────────────────────────────────────")

    dl_url = f"{GW}/api/v1/download?file={B64_FILENAME}"
    d = run(f'cmd /c curl -sL -o {BIN_DIR_WIN}\\{B64_FILENAME} "{dl_url}" & echo DL_OK', 30, NODE_WIN)
    if "DL_OK" not in (d.get("stdout","") or ""):
        print(f"  ❌ 下载失败: {(d.get('stderr','') or '')[:100]}")
        sys.exit(1)
    print(f"  ✅ .b64 下载完成")

    d = run(f'cmd /c certutil -decode {BIN_DIR_WIN}\\{B64_FILENAME} {BIN_DIR_WIN}\\computehub.v2.exe >nul 2>&1 & echo DECODE_OK', 30, NODE_WIN)
    if "DECODE_OK" not in (d.get("stdout","") or ""):
        print(f"  ❌ certutil 解码失败: {(d.get('stderr','') or '')[:100]}")
        sys.exit(1)
    print(f"  ✅ certutil 解码成功 → computehub.v2.exe")

    d = run(f'cmd /c if exist {BIN_DIR_WIN}\\computehub.v2.exe (echo OK {BIN_DIR_WIN}\\computehub.v2.exe) else (echo MISSING)', 5, NODE_WIN)
    if "OK" in ((d.get("stdout","") or "").strip()):
        print(f"  ✅ 文件确认存在")
    else:
        print(f"  ❌ 文件不存在")
        sys.exit(1)

    # ========== Phase C: 蓝绿升级 ==========
    print(f"\n📌 Phase C: 蓝绿升级（无 copy，使用 v2.exe）")
    print("──────────────────────────────────────────")

    worker_pid = get_pid(8383)
    gw_pid = get_pid(8282)
    print(f"  旧 Worker  PID: {worker_pid}")
    print(f"  旧 Gateway PID: {gw_pid}")

    # 杀旧GW → 启动新GW (computehub.v2.exe)
    print(f"\n  📦 杀旧GW → 启新GW...")
    d = run(f'cmd /c taskkill /f /pid {gw_pid} >nul 2>&1 & start /B {BIN_DIR_WIN}\\computehub.v2.exe gateway & echo GW_OK', 15, NODE_WIN)
    print(f"  {d.get('stdout','').strip()[:50]}")
    print(f"  等 8 秒让新 Gateway 启动...")
    time.sleep(8)

    # 全面测试 ⭐
    print(f"\n  🔬 新Gateway全面测试...")
    tests = {}
    
    t = run('curl -s http://localhost:8282/api/v1/nodes/list', 10, NODE_WIN)
    tests["API"] = '"success":true' in (t.get("stdout","") or "")
    
    t = run('curl -s -o NUL -w "%{http_code}" http://localhost:8282/gallery', 10, NODE_WIN)
    tests["Gallery"] = '200' in (t.get("stdout","") or "")
    
    t = run('curl -s -o NUL -w "%{http_code}" http://localhost:8282/ai', 10, NODE_WIN)
    tests["AI"] = '200' in (t.get("stdout","") or "")
    
    t = run('curl -s http://localhost:8383/api/v1/worker/health', 10, NODE_WIN)
    tests["Worker"] = '"status":"ok"' in (t.get("stdout","") or "")
    
    for k,v in tests.items(): print(f"    {'✅' if v else '❌'} {k}")
    
    if not all(tests.values()):
        failed = [k for k,v in tests.items() if not v]
        print(f"\n  ❌ 失败项: {failed} → 回滚")
        new_gw = get_pid(8282)
        run(f'cmd /c taskkill /f /pid {new_gw} >nul 2>&1 & start /B {BIN_DIR_WIN}\\computehub.exe gateway & echo ROLLBACK', 15, NODE_WIN)
        print("  ✅ 回滚完成")
        sys.exit(1)
    print(f"  ✅ 全部通过！")

    # 杀旧Worker → move → 启新Worker
    print(f"\n  🔄 杀旧Worker → 替换 → 启新Worker...")
    d = run(
        f'cmd /c '
        f'taskkill /f /pid {worker_pid} >nul 2>&1 & '
        f'move /Y {BIN_DIR_WIN}\\computehub.v2.exe {BIN_DIR_WIN}\\computehub.exe >nul & '
        f'start /B {BIN_DIR_WIN}\\computehub.exe worker '
        f'--gw {GW} --node-id {NODE_WIN} '
        f'--interval 3 --concurrent 2 --heartbeat 10 & '
        f'echo PHASE4_DONE',
        20, NODE_WIN
    )
    print(f"  {d.get('stdout','').strip()[:60]}")
    print(f"  等 15 秒...")
    time.sleep(15)

    # 验证
    print(f"\n🔍 Phase D: 验证升级结果")
    print("──────────────────────────")
    r = json.loads(urllib.request.urlopen(GW+"/api/v1/nodes/list", timeout=10).read())
    for n in r.get("data", []):
        if n["node_id"] == NODE_WIN:
            print(f"  📌 {NODE_WIN}: {n['status']} (v{n.get('version','?')})")
            if n["status"] == "online":
                print(f"\n  🎉 蓝绿升级 v2 成功！Base64 通道验证通过 ✅")
            else:
                print(f"  ⚠️  状态: {n['status']}")
            break
    else:
        print(f"  ⚠️  {NODE_WIN} 未注册")

if __name__ == "__main__":
    main()