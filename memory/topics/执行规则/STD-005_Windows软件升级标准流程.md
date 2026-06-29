# STD-005: ComputeHub 软件升级标准流程（Windows 守护架构版）

> v1.0 · 2026-06-03 基于 windows-home-01 实战
> 
> **核心理念**: Worker 是永不中断的守护进程 → Worker 管理 Gateway → Gateway 管理人机交互

---

## 🏗️ 守护架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Worker Agent（守护进程）                    │
│                    PID 7892 · 端口 8383                      │
│                    "永远活着，管理一切"                        │
│                                                             │
│  Worker 职责：                                               │
│  ├─ 🔄 启动/重启 Gateway                                   │
│  ├─ 🔄 升级 Gateway binary                                 │
│  ├─ 🔄 监控 Gateway 健康                                    │
│  ├─ 🔄 如果 Gateway 挂了，自动拉起来                        │
│  └─ 🔄 自身通过 ECS 升级（30min 自动检查）                  │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │           Gateway（控制面板）                          │  │
│   │           PID 可变 · 端口 8282                        │  │
│   │           "可以被随意替换"                              │  │
│   │                                                        │  │
│   │  Gateway 职责：                                        │  │
│   │  ├─ API 端点（nodes/tasks/gallery）                    │  │
│   │  ├─ AI 智能体（/api/v1/agent/think）                   │  │
│   │  ├─ Gallery 作品广场（/gallery）                       │  │
│   │  ├─ Web 管理页面（/ai）                                │  │
│   │  └─ 管控所有 Worker                                    │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                             │
│   ═══ 控制流 ═══                                            │
│   你 → Gateway API → Worker 执行 → 结果返回                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 关键设计

### 为什么 Worker 要管 Gateway？

| 场景 | 传统做法（Gateway 自己管自己） | 守护架构（Worker 管 Gateway） |
|------|---------------------------|---------------------------|
| **升级** | Gateway 自杀 → 断联 → 等重启 | Worker 替它杀+起 → **零断联** |
| **崩溃** | 没人管，等人发现 | Worker 检测到挂了，**自动拉起** |
| **回滚** | 靠外部脚本 | Worker 重新下载旧版再起 |
| **重启** | 手动 SSH 或远程桌面 | 通过 Worker 一键重启 |

### 一句话总结

> **Worker 是打不死的监理，Gateway 是被监理管理的服务。**

---

## 0️⃣ 前置条件

- [ ] Worker Agent 已注册到 ECS Gateway（nodes/list 显示 online ✅）
- [ ] 知道 Gateway 的启动命令（`"D:\computehub\computehub.exe" gateway`）
- [ ] 知道 Worker 的启动命令（`"D:\computehub\computehub.exe" worker --gw ...`）
- [ ] 新 binary 已上传到 ECS deploy 目录

---

## 1️⃣ 基础：Worker 后台管理 Gateway

### 1.1 启动 Gateway（首次部署）

```python
# 通过 ECS 向 Worker 提交任务 → Worker 启动 Gateway
cmd = 'cmd /c start /B D:\\computehub\\computehub.exe gateway & echo GW_STARTED'
submit(cmd, 10, "windows-home-01")
```

### 1.2 重启 Gateway（不停 Worker）

```python
cmd = (
    'cmd /c '
    'taskkill /f /pid <GATEWAY_PID> >nul 2>&1 & '
    'ping -n 3 127.0.0.1 >nul & '
    'start /B D:\\computehub\\computehub.exe gateway & '
    'echo GW_RESTARTED'
)
submit(cmd, 15, "windows-home-01")
```

### 1.3 监控 Gateway 健康

```python
# Worker 自检（通过本地 8383）
submit('curl -s http://localhost:8383/api/v1/worker/health', 5, "windows-home-01")
# → {"node_id":"windows-home-01","status":"ok"}

# 检查 Gateway（通过本地 8282）
submit('curl -s -o NUL -w "%%{http_code}" http://localhost:8282/api/v1/nodes/list', 5, "windows-home-01")
# → HTTP 200
```

---

## 2️⃣ 升级流程（核心）

### Step 0：查当前 Gateway PID

```python
import base64

def ps(cmd):
    b64 = base64.b64encode(cmd.encode('utf-16le')).decode()
    return f"powershell -EncodedCommand {b64}"

# 查 Gateway PID（端口 8282 的归属进程）
tid = submit(ps("(Get-NetTCPConnection -LocalPort 8282).OwningProcess"), 10, NODE)
d = poll(tid, 12)
gateway_pid = d['stdout'].strip().split('\n')[0].strip()
print(f"Gateway PID: {gateway_pid}")
# → Gateway PID: 20324
```

### Step 1：下载新 binary

```python
DOWNLOAD_URL = "http://36.250.122.43:8282/deploy/computehub.exe"
cmd = f'cmd /c curl -sL -o D:\\computehub\\computehub.new.exe {DOWNLOAD_URL} & echo DL_OK'
tid = submit(cmd, 30, NODE)
d = poll(tid, 35)
assert 'DL_OK' in (d.get('stdout') or ''), "下载失败"
```

### Step 2：& 链升级（Worker 替 Gateway 升级）

```python
cmd = (
    'cmd /c '
    f'taskkill /f /pid {gateway_pid} >nul 2>&1 & '    # 杀旧 Gateway
    'ping -n 3 127.0.0.1 >nul & '                      # 等 3 秒
    'move /y D:\\computehub\\computehub.new.exe '       # 替换
    '    D:\\computehub\\computehub.exe >nul & '
    'start /B D:\\computehub\\computehub.exe '          # 起新 Gateway
    '    gateway & '
    'echo GW_UPGRADED'                                  # 确认信号
)
tid = submit(cmd, 20, NODE)
d = poll(tid, 25)
```

⚠️ **`&` 链规则**：不用 `&&`，用 `&`。`&&`+`start` 会导致 cmd 挂死被 SIGTERM。

### Step 3：验证升级结果

```python
time.sleep(5)

verify_tests = [
    ("进程数",          'tasklist | findstr computehub',        lambda o: len(o.strip().split('\n')) >= 2),
    ("Gateway API",    'curl -s http://localhost:8282/api/v1/nodes/list', lambda o: '"success":true' in o),
    ("Gallery 页面",   'curl -s -o NUL -w "%%{http_code}" http://localhost:8282/gallery', lambda o: '200' in o),
    ("Worker 健康",    'curl -s http://localhost:8383/api/v1/worker/health', lambda o: '"status":"ok"' in o),
]

for name, cmd, check in verify_tests:
    tid = submit(cmd, 10, NODE)
    d = poll(tid, 12)
    ok = check((d.get('stdout') or '').strip())
    print(f"  {'✅' if ok else '❌'} {name}")
```

---

## 3️⃣ 回滚预案

如果新 Gateway 启动异常：

```python
# Worker 重新下载旧版本，再启动
rollback_cmd = (
    'cmd /c '
    'curl -sL -o D:\\computehub\\computehub.exe '
    'http://36.250.122.43:8282/deploy/computehub.bak.exe '
    '& start /B D:\\computehub\\computehub.exe gateway'
)
submit(rollback_cmd, 20, NODE)
```

---

## 4️⃣ Python 一键升级脚本

```python
#!/usr/bin/env python3
"""
ComputeHub 守护架构升级脚本

用法:
    python3 upgrade_gateway.py

流程:
    Worker(守护) → 下载 → Kill旧Gateway → 替换 → 启动新Gateway → 验证
"""
import base64, json, urllib.request, time

# ── 配置 ──
GW = "http://36.250.122.43:8282"      # ECS 主 Gateway
NODE = "windows-home-01"               # 目标 Windows 节点
BIN_DIR = r"D:\computehub"            # binary 目录
DL_URL = f"{GW}/deploy/computehub.exe"

def main():
    print("=" * 50)
    print("🚀 ComputeHub Gateway 守护升级")
    print("=" * 50)
    
    # Step 0: 查当前 Gateway PID
    pid = get_gateway_pid()
    print(f"📌 旧 Gateway PID: {pid}")
    
    # Step 1: 下载
    print("⬇️  下载新 binary...", end=" ")
    download()
    print("✅")
    
    # Step 2: Worker 替 Gateway 升级
    print(f"🔄 Worker 执行升级...", end=" ")
    upgrade(pid)
    print("✅")
    
    # Step 3: 验证
    print("🔍 验证...")
    time.sleep(5)
    ok = verify()
    
    if ok:
        print("\n✅ 升级完成！Worker(PID 不变) + 新Gateway(旧PID已替换)")
    else:
        print("\n⚠️  验证异常，检查后重试或执行回滚")

# ── 核心操作 ──
def get_gateway_pid():
    tid = submit(ps("(Get-NetTCPConnection -LocalPort 8282).OwningProcess"), 10, NODE)
    d = poll(tid, 12)
    for line in (d.get('stdout') or '').split('\n'):
        if line.strip().isdigit():
            return int(line.strip())
    raise Exception("找不到 Gateway 端口 8282")

def download():
    cmd = f'cmd /c curl -sL -o {BIN_DIR}\\computehub.new.exe {DL_URL} & echo DL_OK'
    tid = submit(cmd, 30, NODE)
    d = poll(tid, 35)
    assert 'DL_OK' in (d.get('stdout') or ''), "下载失败"

def upgrade(pid):
    cmd = (
        f'cmd /c '
        f'taskkill /f /pid {pid} >nul 2>&1 & '
        f'ping -n 3 127.0.0.1 >nul & '
        f'move /y {BIN_DIR}\\computehub.new.exe {BIN_DIR}\\computehub.exe >nul & '
        f'start /B {BIN_DIR}\\computehub.exe gateway & '
        f'echo GW_UPGRADED'
    )
    tid = submit(cmd, 20, NODE)
    poll(tid, 25)

def verify():
    all_ok = True
    tests = [
        ("进程数",    'tasklist | findstr computehub',
         lambda o: len([l for l in o.split('\n') if l.strip()]) >= 2),
        ("API就绪",   'curl -s http://localhost:8282/api/v1/nodes/list',
         lambda o: '"success":true' in o),
        ("Gallery",   'curl -s -o NUL -w "%%{http_code}" http://localhost:8282/gallery',
         lambda o: '200' in o),
        ("Worker运行中", 'curl -s http://localhost:8383/api/v1/worker/health',
         lambda o: '"status":"ok"' in o),
    ]
    for name, cmd, check in tests:
        tid = submit(cmd, 10, NODE)
        d = poll(tid, 12)
        ok = check((d.get('stdout') or '').strip())
        print(f"  {'✅' if ok else '❌'} {name}")
        if not ok: all_ok = False
    return all_ok

# ── 工具 ──
def submit(cmd, timeout=10, node=None):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct"}
    if node: body["assigned_node"] = node
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

if __name__ == "__main__":
    main()
```

---

## 5️⃣ 守护架构 vs 传统架构

| 对比项 | 传统（Gateway 管一切） | ✅ 守护架构（Worker 管 Gateway） |
|--------|---------------------|------------------------------|
| Gateway 升级 | 外部脚本/手动 | **Worker 自动替它升** |
| Gateway 崩溃 | 没人管，服务中断 | **Worker 自动拉起来** |
| Worker 升级 | 自带 30min 自动检查 | 不变（已有能力） |
| 部署复杂度 | 低 | 略高（多一个守护层） |
| 可靠性 | 单点故障 | ⭐ **Worker 不死，体系不崩** |

---

## 📜 实战验证记录

**2026-06-03 22:29 — windows-home-01**

```
升级前: Worker(PID 7892) + 旧Gateway(PID 20324)
                    ↓
         Worker 执行 & 链升级命令
                    ↓
升级后: Worker(PID 7892 ✓ 不变) + 新Gateway(PID 24568)
```

- Gateway 升级耗时: ~5 秒
- Worker 全程在线 ✅
- API/Gallery/Worker health 全部正常 ✅
- 无任何人工干预 ✅

---

**变更记录**

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-03 | v1.0 | 初版，基于守护架构升级实战 |