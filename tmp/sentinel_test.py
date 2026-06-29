#!/usr/bin/env python3
"""Sentinel 安全审批系统 - 全面测试"""

import json, time, urllib.request, urllib.error, sys

GATEWAY = "http://36.250.122.43:8282"
NODE = "ecs-p2ph"

def submit(label, payload_dict):
    """提交 test task 到 ecs-p2ph 执行 safety_check"""
    inner = json.dumps(payload_dict, ensure_ascii=False)
    # curl 包装
    cmd = f"curl -s -X POST http://127.0.0.1:8383/api/v1/worker/safety_check -H 'Content-Type: application/json' -d '{inner}'"
    
    task = {
        "node_id": NODE,
        "task_type": "exec",
        "payload": cmd,
        "timeout": 8
    }
    req = urllib.request.Request(f"{GATEWAY}/api/v1/tasks/submit",
                                 data=json.dumps(task).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    tid = result.get("data", {}).get("task_id", "ERR")
    return tid

def get_result(tid):
    """等待完成并获取 stdout"""
    for _ in range(10):
        req = urllib.request.Request(f"{GATEWAY}/api/v1/tasks/detail?task_id={tid}&node_id={NODE}")
        with urllib.request.urlopen(req) as resp:
            d = json.loads(resp.read())
        data = d.get("data", {})
        status = data.get("status", "unknown")
        if status == "completed":
            stdout = data.get("stdout", "")
            if stdout:
                return json.loads(stdout)
            return {"error": "no stdout", "stderr": data.get("stderr","")}
        if status == "failed":
            return {"error": "task failed", "stderr": data.get("stderr","")}
        time.sleep(1)
    return {"error": "timeout"}

tests = [
    ("T1: {} 空对象", {}),
    ("T2: 完整参数（全部填写）", {
        "action": "升级到 v1.3.8",
        "why": "修复安全漏洞需要紧急升级",
        "scope": "ecs-p2ph 节点，仅此一个 Worker",
        "rollback": "从 .bak 备份文件恢复旧版本 binary 并重启 worker",
        "command": "computehub upgrade --force"
    }),
    ("T3: 无 rollback", {
        "action": "杀进程",
        "why": "内存不足需要释放",
        "scope": "ecs-p2ph",
        "rollback": "",
        "command": "killall computehub"
    }),
    ("T4: rollback 仅 2 字", {
        "action": "重启",
        "why": "节点卡死需要重启",
        "scope": "ecs-p2ph",
        "rollback": "重启",
        "command": "reboot"
    }),
    ("T5: rollback 刚好 4 字", {
        "action": "测试",
        "why": "测试边界场景",
        "scope": "自己",
        "rollback": "重启",
        "command": "echo test"
    }),
    ("T6: rollback 刚好 5 字", {
        "action": "测试",
        "why": "测试边界场景",
        "scope": "自己",
        "rollback": "重启重试",
        "command": "echo test"
    }),
    ("T7: kill 未指定目标", {
        "action": "杀进程释放内存",
        "why": "内存使用率超过 90%，需要紧急释放",
        "scope": "ecs-p2ph 节点",
        "rollback": "被杀进程的 task 会自动重试",
        "command": "killall -9 computehub"
    }),
    ("T8: kill 指定了目标（taskkill /PID）", {
        "action": "停止异常 Worker 进程",
        "why": "Worker 进程 CPU 100%，影响其他任务",
        "scope": "Windows-mobile 节点",
        "rollback": "自动心跳检测到离线后会拉起新进程；10分钟仍离线则远程桌面人工处理",
        "command": "taskkill /PID 1234"
    }),
    ("T9: Windows 操作无网络预案", {
        "action": "重启 Windows-mobile Worker",
        "why": "Windows-mobile 离线超过 30 分钟需要重启恢复",
        "scope": "Windows-mobile 节点（远程操作）",
        "rollback": "人工远程桌面检查后手动重启",
        "command": "ssh Windows-mobile reboot"
    }),
    ("T10: Windows 操作有网络预案", {
        "action": "重启 Windows-mobile Worker",
        "why": "Windows-mobile 离线超过 30 分钟，心跳无响应",
        "scope": "Windows-mobile 节点，当前无活跃任务",
        "rollback": "如果 10 分钟仍无心跳则人工登录远程桌面检查；如有备份 worker binary 则从备份恢复",
        "command": "taskkill /F /IM computehub.exe"
    }),
    ("T11: 无 why 字段", {
        "action": "删除文件",
        "why": "",
        "scope": "服务器 /tmp 目录",
        "rollback": "文件已备份到 /backup",
        "command": "rm -rf /tmp/cache"
    }),
    ("T12: 无 scope 字段", {
        "action": "清理缓存",
        "why": "磁盘空间不足需要清理",
        "scope": "",
        "rollback": "从备份恢复缓存文件",
        "command": "rm -rf /var/cache/*"
    }),
    ("T13: why 字段太短（3字）", {
        "action": "测试",
        "why": "测试",
        "scope": "自己",
        "rollback": "失败就从备份恢复重新执行",
        "command": "echo test"
    }),
    ("T14: why 字段刚好 10 字", {
        "action": "测试边界",
        "why": "测试边界10字",
        "scope": "自己",
        "rollback": "失败就从备份恢复重新执行",
        "command": "echo test"
    }),
]

results = []
for label, payload in tests:
    tid = submit(label, payload)
    result = get_result(tid)
    v = result.get("verdict", "?")
    a = result.get("approved", "?")
    w = result.get("warnings", [])
    ws = "; ".join(w) if w else "—"
    sug = result.get("suggestion", "")
    results.append((label, v, a, ws, sug))
    status_icon = "✅" if "approve" in v else ("⚠️" if "warning" in v else "❌")
    print(f"{status_icon} {label}")
    print(f"   verdict: {v} | approved: {a}")
    if w:
        for ww in w:
            print(f"   {ww}")
    if sug:
        print(f"   suggestion: {sug}")
    time.sleep(0.3)

print()
print("=" * 72)
print("SENTINEL 安全审批 - 汇总报告")
print("=" * 72)
print(f"{'测试':<30} {'结果':<25} {'通过':<5}")
print("-" * 62)
for label, v, a, ws, sug in results:
    ok = "✅" if ("approve" in v) else "❌"
    print(f"{label:<30} {v:<25} {ok:<5}")