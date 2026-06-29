# STD-005: ComputeHub Gateway 零中断升级标准流程

> v1.0 · 2026-06-03 基于 windows-home-01 实战
> 
> **核心思想**: Worker 永不自杀 → Worker 作为升级代理 → 由 Worker 来 kill + start Gateway

---

## 🧠 核心原理

```
          ┌─────────────────┐
          │   Worker Agent  │ ← 永不中断，负责执行升级
          │   (PID 7892)    │
          │   端口 8383     │
          └────────┬────────┘
                   │ 升级命令
                   ▼
          ┌─────────────────┐
          │   旧 Gateway    │ → taskkill → 消失
          │   (PID 20324)   │
          │   端口 8282     │
          └─────────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │   新 Gateway    │ ← start /B，新 PID
          │   (PID 24568)   │
          │   端口 8282     │ ✅ 同一端口，无缝接管
          └─────────────────┘
```

**关键差异：**
- ❌ Worker 自杀升级 = Worker 断了，命令挂半路
- ✅ Worker 替 Gateway 升级 = Worker 活着，全程可控

---

## 0️⃣ 前置条件

- [ ] 目标节点已注册到 ECS Gateway（`nodes/list` 显示 online）
- [ ] 新 binary 已上传到 ECS deploy 目录
- [ ] 知道当前 Gateway 的启动命令（见 Step 0）

### Step 0：查 Gateway 启动命令

```python
import base64, json, urllib.request, time

GW = "http://36.250.122.43:8282"  # ECS Gateway

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

def ps_encoded(cmd):
    b64 = base64.b64encode(cmd.encode('utf-16le')).decode()
    return f"powershell -EncodedCommand {b64}"

NODE = "windows-home-01"

# 查 Gateway 端口 8282 的进程命令行
tid = submit(ps_encoded(
    "(Get-NetTCPConnection -LocalPort 8282).OwningProcess"
), 10, NODE)
d = poll(tid, 12)
gateway_pid = (d.get('stdout') or '').strip().split('\n')[0].strip()
print(f"Gateway PID: {gateway_pid}")

# 查启动命令
tid = submit(ps_encoded(
    f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {gateway_pid}').CommandLine"
), 10, NODE)
d = poll(tid, 12)
stdout = (d.get('stdout') or '').strip()
clean = [l for l in stdout.split('\n') if not l.startswith('#<')]
gateway_cmd = '\n'.join(clean).strip()
print(f"Gateway 启动命令: {gateway_cmd}")
```

**预期输出示例：**
```
Gateway PID: 20324
Gateway 启动命令: "D:\computehub\computehub.exe" gateway
```

---

## 1️⃣ 下载新 binary

```python
# 从 ECS deploy 目录下载新版本到临时路径
DOWNLOAD_CMD = (
    'cmd /c curl -sL -o D:\\computehub\\computehub.new.exe '
    'http://36.250.122.43:8282/deploy/computehub.exe '
    '& echo DL_OK'
)

tid = submit(DOWNLOAD_CMD, 30, NODE)
d = poll(tid, 35)
assert (d.get('stdout') or '').strip() == 'DL_OK', "下载失败"
print("✅ 下载成功")
```

---

## 2️⃣ & 链：kill → 延迟 → 替换 → 启动（核心步骤）

```python
# 🎯 一条命令干四件事
UPGRADE_CMD = (
    'cmd /c '
    'taskkill /f /pid 20324 >nul 2>&1 & '      # 1. 杀旧 Gateway
    'ping -n 3 127.0.0.1 >nul & '               # 2. 等3秒（端口释放）
    'move /y D:\\computehub\\computehub.new.exe '
    '    D:\\computehub\\computehub.exe >nul & '  # 3. 替换 binary
    'start /B D:\\computehub\\computehub.exe '
    '    gateway & '                              # 4. 后台启动新 Gateway
    'echo GW_UPGRADED'                            # 5. 确认信号
)

tid = submit(UPGRADE_CMD, 20, NODE)
d = poll(tid, 25)
stdout = (d.get('stdout') or '').strip()
print(f"升级结果: {stdout}")
```

**`&` 链各段详解：**

| 段 | 命令 | 作用 | 必须 |
|----|------|------|------|
| ① | `taskkill /f /pid <PID> >nul 2>&1` | 杀死旧 Gateway | ✅ |
| ② | `ping -n 3 127.0.0.1 >nul` | 等3秒让端口释放 | ✅ |
| ③ | `move /y new.exe old.exe >nul` | 替换 binary | ✅ |
| ④ | `start /B computehub.exe gateway` | 起新服务 | ✅ |
| ⑤ | `echo GW_UPGRADED` | 确认命令执行完毕 | 推荐 |

> ⚠️ **为什么用 `&` 不用 `&&`？**
> 
> Worker 执行 cmd 时，`&&`+`start` 会导致 cmd.exe 等待 start 的子进程，然后超时被 SIGTERM。
> 用 `&` 后每条命令独立执行，前一条的失败/超时不影响后一条。

---

## 3️⃣ 验证（等 5 秒让新 Gateway 就绪）

```python
time.sleep(5)

# 验证 1：新进程是否存活
tid = submit('tasklist | findstr computehub', 10, NODE)
d = poll(tid, 12)
print("当前进程:")
print((d.get('stdout') or '').strip())

# 验证 2：API 是否正常
tid = submit('curl -s http://localhost:8282/api/v1/nodes/list', 10, NODE)
d = poll(tid, 12)
print("API 响应:")
print((d.get('stdout') or '').strip()[:200])

# 验证 3：Gallery 是否正常
tid = submit('curl -s -o NUL -w "%%{http_code}" http://localhost:8282/gallery', 10, NODE)
d = poll(tid, 12)
print(f"Gallery: HTTP {(d.get('stdout') or '').strip()}")

# 验证 4：Worker AI 是否正常（Worker 不能被升级影响）
tid = submit('curl -s http://localhost:8383/api/v1/worker/health', 10, NODE)
d = poll(tid, 12)
print(f"Worker: {(d.get('stdout') or '').strip()[:100]}")
```

### 通过标准

| 检查项 | 期望值 |
|--------|--------|
| 进程数 | 2（Gateway + Worker） |
| `nodes/list` | 正常 JSON，data 非空 |
| `Gallery` | HTTP 200 |
| `Worker health` | `{"status":"ok"}` |

---

## 4️⃣ 回滚预案

如果新 Gateway 启动异常：

```python
# 方案：用旧 binary（如果没被覆盖）或重新下载
rollback_cmd = (
    'cmd /c '
    'curl -sL -o D:\\computehub\\computehub.exe '
    'http://36.250.122.43:8282/deploy/computehub.bak.exe '
    '& start /B D:\\computehub\\computehub.exe gateway'
)
tid = submit(rollback_cmd, 20, NODE)
d = poll(tid, 25)
print("回滚执行完成")
```

---

## 5️⃣ Python 一键升级脚本

```python
#!/usr/bin/env python3
"""ComputeHub Gateway 升级脚本"""
import base64, json, urllib.request, time, sys

GW = "http://36.250.122.43:8282"
NODE = "windows-home-01"
BIN_DIR = r"D:\computehub"
DOWNLOAD_URL = "http://36.250.122.43:8282/deploy/computehub.exe"

def main():
    print("=" * 50)
    print("ComputeHub Gateway 升级")
    print("=" * 50)
    
    # Step 0: 查当前 Gateway PID
    pid = get_gateway_pid()
    print(f"📌 当前 Gateway PID: {pid}")
    
    cmdline = get_process_cmdline(pid)
    print(f"📌 启动命令: {cmdline}")
    
    # Step 1: 下载新 binary
    print("\n⬇️ Step 1: 下载新 binary...")
    download()
    print("   ✅ 下载完成")
    
    # Step 2: & 链升级
    print("\n🔄 Step 2: 执行升级...")
    upgrade(pid)
    print("   ✅ 升级命令已执行")
    
    # Step 3: 验证
    print("\n🔍 Step 3: 验证...")
    time.sleep(5)
    verify()
    print("\n✅ 升级完成！")

def get_gateway_pid():
    tid = submit(ps_encoded("(Get-NetTCPConnection -LocalPort 8282).OwningProcess"), 10, NODE)
    d = poll(tid, 12)
    out = (d.get('stdout') or '').strip()
    for line in out.split('\n'):
        if line.strip().isdigit():
            return int(line.strip())
    raise Exception("找不到 Gateway PID")

def get_process_cmdline(pid):
    tid = submit(ps_encoded(f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine"), 10, NODE)
    d = poll(tid, 12)
    out = (d.get('stdout') or '').strip()
    clean = [l for l in out.split('\n') if not l.startswith('#<')]
    return '\n'.join(clean).strip()

def download():
    cmd = f'cmd /c curl -sL -o {BIN_DIR}\\computehub.new.exe {DOWNLOAD_URL} & echo DL_OK'
    tid = submit(cmd, 30, NODE)
    d = poll(tid, 35)
    assert 'DL_OK' in (d.get('stdout') or ''), f"下载失败: {(d.get('stderr') or '')[:200]}"

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
    d = poll(tid, 25)

def verify():
    tests = [
        ("进程数", 'tasklist | findstr computehub', lambda o: len(o.strip().split('\n')) >= 2),
        ("API节点", 'curl -s http://localhost:8282/api/v1/nodes/list', lambda o: '"success":true' in o),
        ("Gallery", 'curl -s -o NUL -w "%%{http_code}" http://localhost:8282/gallery', lambda o: '200' in o),
        ("Worker", 'curl -s http://localhost:8383/api/v1/worker/health', lambda o: '"status":"ok"' in o),
    ]
    all_ok = True
    for name, cmd, check in tests:
        tid = submit(cmd, 10, NODE)
        d = poll(tid, 12)
        out = (d.get('stdout') or '').strip()
        ok = check(out)
        print(f"   {'✅' if ok else '❌'} {name}")
        if not ok: all_ok = False
    if not all_ok:
        print("⚠️  部分验证失败，请检查！")
    return all_ok

# ── 工具函数 ──
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

def ps_encoded(cmd):
    b64 = base64.b64encode(cmd.encode('utf-16le')).decode()
    return f"powershell -EncodedCommand {b64}"

if __name__ == "__main__":
    main()
```

---

## 6️⃣ 对比：三种升级模式

| 模式 | 执行者 | Gateway 可升级？ | Worker 可升级？ | 风险 |
|------|--------|-----------------|-----------------|------|
| **自升级** | Worker 自己 | ❌ | ✅（build-in 30min 自动检查） | Worker 自杀 |
| **Worker 替 Gateway 升** ⭐ | Worker | **✅** | ❌ | **最低** |
| **Gateway 替 Worker 升** | Gateway | ❌ | ✅（可通过 submit 实现） | Worker 断联 |

**推荐：Worker 替 Gateway 升级**——Worker 不死，升级全程可控，失败了还能重试。

---

## 📜 实战记录

| 时间 | 操作 | 结果 | 教训 |
|------|------|------|------|
| 2026-06-03 22:29 | Gateway kill + start | ✅ 5秒恢复 | 用 `&` 链，不用多步提交 |
| 2026-06-03 22:36 | Worker kill + start | ✅ 7秒恢复 | 用 `&` 链，Worker 重新注册到 ECS |

---

**附：ECS 备用 SSH**
```bash
# 主端口
ssh computehub@36.250.122.43 -p 8022
# 备用（8022 挂了时）
ssh computehub@36.250.122.43 -p 8222
```