#!/usr/bin/env python3
"""
STD-005: ComputeHub 蓝绿升级实操
基于 v1.3.10 → v1.3.10（同版本演练，验证完整升级流程）
目标: windows-home-01 (D:\\computehub)
"""

import base64, json, urllib.request, time, sys

# ── 配置 ──
GW = "http://36.250.122.43:8282"
NODE = "windows-home-01"
BIN_DIR = r"D:\computehub"
DL_URL = f"{GW}/api/v1/download?file=computehub.exe&platform=windows-amd64"

# ══════════════════════════════════════
# 工具函数
# ══════════════════════════════════════

def submit(cmd, timeout=10, node=NODE):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct"}
    body["assigned_node"] = node
    req = urllib.request.Request(GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def poll(tid, max_wait=15):
    for i in range(max_wait):
        time.sleep(1)
        resp = json.loads(urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") in ("completed", "failed"): return d
    return None

def ps(cmd):
    return f"powershell -EncodedCommand {base64.b64encode(cmd.encode('utf-16le')).decode()}"

def get_pid(port):
    """根据端口查PID"""
    tid = submit(ps(f"(Get-NetTCPConnection -LocalPort {port}).OwningProcess"), 12, NODE)
    d = poll(tid, 12)
    for l in (d.get('stdout') or '').split('\n'):
        l = l.strip()
        if l.isdigit(): return int(l)
    raise Exception(f"找不到端口 {port}")

def run_cmd(cmd, timeout=10, node=NODE):
    """提交命令并等结果"""
    tid = submit(cmd, timeout, node)
    d = poll(tid, timeout + 5)
    return d

def show_result(step, d, detail=""):
    """格式化输出"""
    stdout = (d.get('stdout') or '').strip()[:150]
    stderr = (d.get('stderr') or '').strip()[:100]
    exit_code = d.get('exit_code')
    print(f"  exit={exit_code} | stdout: {stdout}")
    if stderr:
        print(f"  stderr: {stderr}")

# ══════════════════════════════════════
# 主流程
# ══════════════════════════════════════

def main():
    print("=" * 60)
    print("🚀 STD-005 蓝绿升级实操  v1.3.10 → v1.3.10（演练）")
    print("=" * 60)
    
    # ── Step 0: 查当前 PID ──
    print("\n📌 Step 0: 查当前 PID...")
    worker_pid = get_pid(8383)
    gw_pid = get_pid(8282)
    print(f"  旧 Worker  PID: {worker_pid}")
    print(f"  旧 Gateway PID: {gw_pid}")
    
    # ── Phase 1: 下载新 binary ──
    print("\n⬇️  Phase 1: 下载新 binary...")
    dl_cmd = f'cmd /c curl -sL -o {BIN_DIR}\\computehub.new.exe "{DL_URL}" & echo DL_OK'
    d = run_cmd(dl_cmd, 30)
    assert 'DL_OK' in (d.get('stdout') or ''), f"下载失败: {d.get('stderr','')[:200]}"
    print("  ✅ 下载成功")
    
    # ── Phase 2: 备份→杀旧GW→启动新GW ──
    print("\n📦 Phase 2: 备份→杀旧Gateway→启动新Gateway...")
    phase2_cmd = (
        'cmd /c '
        f'copy /Y {BIN_DIR}\\computehub.exe {BIN_DIR}\\computehub.old.exe >nul & '
        f'taskkill /f /pid {gw_pid} >nul 2>&1 & '
        f'start /B {BIN_DIR}\\computehub.new.exe gateway & '
        f'echo PHASE2_DONE'
    )
    d = run_cmd(phase2_cmd, 15)
    show_result("Phase 2", d)
    print("  等待 5 秒让新 Gateway 启动...")
    time.sleep(5)
    
    # ── Phase 3: 新Gateway全面测试 ⭐ ──
    print("\n🔬 Phase 3: 新Gateway全面功能测试...")
    test_results = {}
    
    # 测试1: API基本响应
    d = run_cmd('curl -s http://localhost:8282/api/v1/nodes/list', 10)
    out = (d.get('stdout') or '').strip()
    test_results['API基本响应'] = '"success":true' in out
    print(f"  📡 API基本响应: {'✅' if test_results['API基本响应'] else '❌'}")
    
    # 测试2: Gallery 页面
    d = run_cmd('curl -s -o NUL -w "%%{http_code}" http://localhost:8282/gallery', 10)
    out = (d.get('stdout') or '').strip()
    test_results['Gallery'] = '200' in out
    print(f"  🖼️  Gallery:     {'✅' if test_results['Gallery'] else '❌'}")
    
    # 测试3: AI 页面
    d = run_cmd('curl -s -o NUL -w "%%{http_code}" http://localhost:8282/ai', 10)
    out = (d.get('stdout') or '').strip()
    test_results['AI页面'] = '200' in out
    print(f"  🧠  AI页面:       {'✅' if test_results['AI页面'] else '❌'}")
    
    # 测试4: Worker连通性（旧Worker还活着，应该能响应）
    d = run_cmd('curl -s http://localhost:8383/api/v1/worker/health', 10)
    out = (d.get('stdout') or '').strip()
    test_results['Worker连通'] = '"status":"ok"' in out
    print(f"  🔗 Worker连通:   {'✅' if test_results['Worker连通'] else '❌'}")
    
    # 测试5: 任务提交
    d = run_cmd('cmd /c echo hello_from_new_gateway', 10)
    test_results['任务提交'] = d and d.get('exit_code') == 0
    print(f"  📋 任务提交:     {'✅' if test_results['任务提交'] else '❌'}")
    
    # 决策
    all_pass = all(test_results.values())
    print(f"\n  总体判定: {'✅ 全部通过，继续升级' if all_pass else '❌ 有失败项，执行回滚'}")
    
    if not all_pass:
        failed = [k for k, v in test_results.items() if not v]
        print(f"  失败项: {failed}")
        print("\n🔄 执行回滚...")
        new_gw_pid = get_pid(8282)
        rollback_cmd = (
            'cmd /c '
            f'taskkill /f /pid {new_gw_pid} >nul 2>&1 & '
            f'start /B {BIN_DIR}\\computehub.old.exe gateway & '
            f'echo ROLLBACK_DONE'
        )
        d = run_cmd(rollback_cmd, 15)
        print("  ✅ 回滚完成，旧Gateway已恢复")
        sys.exit(1)
    
    # ── Phase 4: 杀旧Worker→替换→启动新Worker ──
    print("\n🔄 Phase 4: 杀旧Worker→替换binary→启动新Worker...")
    phase4_cmd = (
        'cmd /c '
        f'taskkill /f /pid {worker_pid} >nul 2>&1 & '
        f'move /Y {BIN_DIR}\\computehub.new.exe {BIN_DIR}\\computehub.exe >nul & '
        f'start /B {BIN_DIR}\\computehub.exe worker '
        f'--gw {GW} --node-id {NODE} '
        f'--interval 3 --concurrent 2 --heartbeat 10 & '
        f'echo PHASE4_DONE'
    )
    d = run_cmd(phase4_cmd, 20)
    show_result("Phase 4", d)
    
    # 等一会儿让新Worker注册
    print("  等待 15 秒让新Worker注册到ECS...")
    time.sleep(15)
    
    # ── Phase 5: 验证 ──
    print("\n🔍 Phase 5: 验证升级结果...")
    
    # 验证新Gateway
    d = run_cmd('curl -s http://localhost:8282/api/v1/nodes/list', 10)
    out = (d.get('stdout') or '').strip()
    if '"success":true' in out:
        print("  ✅ 新Gateway API 正常")
    else:
        print("  ❌ 新Gateway API 异常")
    
    # 从ECS看节点状态
    try:
        req = urllib.request.Request(f"{GW}/api/v1/nodes/list")
        r = json.loads(urllib.request.urlopen(req, timeout=10).read())
        found = False
        for node in r.get("data", []):
            if node["node_id"] == NODE:
                found = True
                print(f"  📌 {NODE}: {node['status']} (v{node.get('version','?')})")
                if node["status"] == "online":
                    print("\n" + "=" * 60)
                    print("🎉 蓝绿升级成功！新Worker已上线 ✅")
                    print("=" * 60)
                else:
                    print(f"\n⚠️  状态异常: {node['status']}")
        if not found:
            print(f"\n⚠️  {NODE} 未注册到集群")
            print(f"  手动启动: start /B {BIN_DIR}\\computehub.exe worker --gw {GW} --node-id {NODE}")
    except Exception as e:
        print(f"\n❌ 无法获取节点状态: {e}")

if __name__ == "__main__":
    main()