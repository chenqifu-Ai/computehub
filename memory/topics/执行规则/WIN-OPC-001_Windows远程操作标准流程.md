# WIN-OPC-001: Windows 节点远程操作标准流程

> 建立时间: 2026-06-13  
> 版本: v1.2  
> 适用场景: 通过 ComputeHub Gateway 向远程 Windows 节点执行操作  
> 来源: wanlida-opc01 实战复盘 + 多场景扩展

---

## 📋 目录

1. [操作前检核清单](#1-操作前检核清单)
2. [标准操作流程图](#2-标准操作流程图)
3. [命令执行方式与选择](#3-命令执行方式与选择)
4. [二进制输出场景模板](#4-二进制输出场景模板)
5. [文件操作模板](#5-文件操作模板)
6. [进程管理模板](#6-进程管理模板)
7. [Windows 服务管理](#7-windows-服务管理)
8. [环境变量管理](#8-环境变量管理)
9. [注册表操作](#9-注册表操作)
10. [定时任务管理](#10-定时任务管理)
11. [防火墙规则管理](#11-防火墙规则管理)
12. [大文件传输方案](#12-大文件传输方案)
13. [多步骤编排与条件分支](#13-多步骤编排与条件分支)
14. [日志与审计](#14-日志与审计)
15. [常见问题与预案](#15-常见问题与预案)
16. [附录：命令速查表](#16-附录命令速查表)
17. [实用运维场景模板](#17-实用运维场景模板)
18. [FAQ 补充](#18-faq-补充)

---

## 1. 操作前检核清单

### □ 1.1 节点可达性检查

| 序号 | 检查项 | 命令 | 通过标准 |
|------|--------|------|----------|
| 1 | 节点在线 | `echo OK` | 返回 `completed, exit=0` |
| 2 | Shell 可用 | `echo hello_world && echo alive` | 多命令正常执行 |
| 3 | PowerShell 可用 | `where powershell` | 返回完整路径 |
| 4 | curl 可用 | `where curl` | 返回完整路径 |
| 5 | node.js 可用 | `C:\Users\admin\node\node.exe --version` | 返回版本号 |
| 6 | 磁盘空间 | `wmic logicaldisk get caption,freespace` | 剩余 ≥ 操作需要 3 倍 |

> ⚠️ **教训**: 节点可能显示 online（WebSocket 连接中）但 HTTP 下载超时。先做简单命令检查，再决定后续操作。

### □ 1.2 目标状态确认

| 检查项 | 命令 | 说明 |
|--------|------|------|
| 目标目录是否存在 | `dir C:\target\ 2>nul && echo EXISTS || echo MISSING` | 避免对不存在的路径操作 |
| 目标文件是否存在 | `dir C:\file.exe 2>nul` | 确认文件存在/不存在 |
| 目标进程是否运行 | `tasklist | findstr PROCESS_NAME` | 确认进程状态 |
| 端口监听 | `netstat -ano \| findstr :PORT` | 确认服务状态 |

### □ 1.3 网络条件评估

| 网络类型 | 特征 | 推荐策略 |
|----------|------|----------|
| 本地内网 (192.168.x.x) | SSH 直连快 | 直接用 SSH |
| 远端公网 (183.251.x.x) | WS 可能不稳定 | 先 `echo` 测试，大文件避免 |
| 跨 NAT/防火墙 | 连接延迟大 | 用 Gateway WebSocket，不走 HTTP 下载 |

> ⚠️ **教训**: wanlida-opc01 — WS 连接存活但 HTTP 下载 hang 死。**网络分层：WS 通道 ≠ HTTP 可达**。

---

## 2. 标准操作流程图

```
操作开始
  │
  ├─ Step 0: 节点可达性检查
  │   └─ echo OK → 不通过则中止 ❌
  │
  ├─ Step 1: 根据操作类型选择执行方式
  │   ├─ 纯文本输出 → 直接命令提交
  │   ├─ 二进制/大输出 → base64+certutil+node (WIN-CMD-001)
  │   └─ 大脚本 (>3 行) → 写入文件执行
  │
  ├─ Step 2: 清理临时文件
  │   └─ del /Q C:\temp\*.b64 2>nul
  │      del /Q C:\temp\*.js 2>nul
  │
  ├─ Step 3: 执行主操作
  │   └─ 提交任务 → 轮询结果
  │
  ├─ Step 4: 结果验证
  │   └─ 确认 exit_code=0 + 输出符合预期
  │
  └─ Step 5: 收尾
      └─ 清理临时文件 + 记录结果
```

---

## 3. 命令执行方式与选择

### 3.1 方式对比

| 方式 | 适用场景 | 优点 | 缺点 | 推荐度 |
|------|----------|------|------|--------|
| 直接提交 | 纯文本小命令（≤100 字符） | 最简单，零准备 | 超长输出被截断 | ⭐⭐⭐ |
| WIN-CMD-001 | 需要完整二进制输出 | 完整输出，绕过 cmd 限制 | 需准备 base64 脚本 | ⭐⭐⭐⭐⭐ |
| PowerShell -EncodedCommand | PATH 更新、注册表操作 | 零转义，一次生效 | 只适合小脚本 | ⭐⭐⭐ |
| 写入 .py 文件 + scp | 复杂安装流程 | 可复用，易调试 | 需要 SSH 或 Gateway 上传 | ⭐⭐⭐ |

### 3.2 直接提交（简单命令）

**适用**: `echo`, `dir`, `ver`, `where`, `netstat` 等纯文本输出命令

```python
import json, urllib.request, time

GW = "http://36.250.122.43:8282"

def submit_simple(cmd, timeout, node_id):
    payload = json.dumps({
        "node_id": node_id,
        "command": cmd,
        "timeout": timeout,
        "priority": 8
    }).encode()
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    task_id = resp.get("data", {}).get("task_id", "")
    return task_id

def get_result(task_id):
    for i in range(45):
        time.sleep(1)
        req = urllib.request.Request(
            f"{GW}/api/v1/tasks/detail?task_id={task_id}"
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        data = resp.get("data", {})
        status = data.get("status")
        if status in ["completed", "failed", "cancelled"]:
            return data
    return None

# 使用示例
tid = submit_simple("echo test", 10, "wanlida-opc01")
result = get_result(tid)
print(f"exit_code={result['exit_code']}, stdout={result.get('stdout','')}")
```

### 3.3 WIN-CMD-001（base64 + certutil + node.js）

**适用**: `nvidia-smi`, `dir`, `tasklist`, `wmic` 等需要完整输出的命令

```python
import base64, json, urllib.request, time

# Step 1: 准备 JS 脚本（单引号，无双引号）
script = r"""var cp=require('child_process');
var fs=require('fs');
var r;
try {
    r=cp.execFileSync('cmd',['/C','dir C:\\computehub\\'],{encoding:'utf8',timeout:30000});
    fs.writeFileSync('C:\\temp\\result.txt',r,'utf8');
    console.log('OK');
} catch(e) {
    fs.writeFileSync('C:\\temp\\result.txt','ERROR:'+e.message,'utf8');
    console.log('ERROR:'+e.message);
}"""

# Step 2: base64 编码
b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')

# Step 3: 构建命令链（先清理再写入）
cmd = (
    'del /Q C:\\temp\\script.b64 2>nul && '
    'del /Q C:\\temp\\script.js 2>nul && '
    'del /Q C:\\temp\\result.txt 2>nul && '
    'echo ' + b64 + ' > C:\\temp\\script.b64 && '
    'certutil -decode C:\\temp\\script.b64 C:\\temp\\script.js && '
    'C:\\Users\\admin\\node\\node.exe C:\\temp\\script.js && '
    'type C:\\temp\\result.txt'
)

# Step 4: 提交 + 轮询
payload = json.dumps({
    "node_id": "wanlida-opc01",
    "command": cmd,
    "timeout": 60,
    "priority": 8
})
```

### 3.4 关键规则

| 规则 | 说明 | 违反后果 |
|------|------|----------|
| **JS 脚本用单引号 `'`** | 不用双引号 `"` | cmd 层吞双引号 → 语法错误 |
| **路径反斜杠必须双写 `\\`** | `'C:\\\\temp\\\\'` | `\t` 被解析为制表符 → 路径崩溃 |
| **命令数组参数** | `['/C','dir C:\\path\\']` | 不用字符串拼接 |
| **先清理再写** | `del /Q C:\\temp\\* 2>nul` | `ERROR_FILE_EXISTS` → certutil 失败 |
| **timeout ≥ 60s** | 含 base64→decode→exec 全过程 | 中间步骤耗时累积 → 超时 |

---

## 4. 二进制输出场景模板

### 4.1 查询目录内容 (`dir`)

```python
script = r"""var cp=require('child_process');
var fs=require('fs');
try {
    var r=cp.execFileSync('cmd',['/C','dir C:\\target\\'],{encoding:'utf8',timeout:30000});
    fs.writeFileSync('C:\\temp\\dir_result.txt',r,'utf8');
    console.log('OK');
} catch(e) {
    fs.writeFileSync('C:\\temp\\dir_result.txt','ERROR:'+e.message,'utf8');
}"""
```

### 4.2 查询 GPU 信息 (`nvidia-smi`)

```python
script = r"""var cp=require('child_process');
var fs=require('fs');
try {
    var r=cp.execFileSync('nvidia-smi',{encoding:'utf8',timeout:60000});
    fs.writeFileSync('C:\\temp\\gpu_result.txt',r,'utf8');
    console.log('OK');
} catch(e) {
    fs.writeFileSync('C:\\temp\\gpu_result.txt','ERROR:'+e.message,'utf8');
}"""
```

### 4.3 查询进程列表 (`tasklist`)

```python
script = r"""var cp=require('child_process');
var fs=require('fs');
try {
    var r=cp.execFileSync('tasklist',['/v','/FO','CSV'],{encoding:'utf8',timeout:30000});
    fs.writeFileSync('C:\\temp\\processes.txt',r,'utf8');
    console.log('OK');
} catch(e) {
    fs.writeFileSync('C:\\temp\\processes.txt','ERROR:'+e.message,'utf8');
}"""
```

### 4.4 查询系统信息 (`systeminfo`)

```python
script = r"""var cp=require('child_process');
var fs=require('fs');
try {
    var r=cp.execFileSync('systeminfo',{encoding:'utf8',timeout:60000});
    fs.writeFileSync('C:\\temp\\systeminfo.txt',r,'utf8');
    console.log('OK');
} catch(e) {
    fs.writeFileSync('C:\\temp\\systeminfo.txt','ERROR:'+e.message,'utf8');
}"""
```

---

## 5. 文件操作模板

### 5.1 复制文件

```python
# 简单复制 — 直接提交
cmd = 'copy /Y C:\\source\\file.exe C:\\dest\\file.exe'
# exit=0, stdout="1 file(s) copied."
```

### 5.2 移动/重命名文件

```python
# 移动
cmd = 'move /Y C:\\source\\file.exe C:\\dest\\file.exe'
# 重命名
cmd = 'ren C:\\path\\old.exe new.exe'
```

### 5.3 删除文件

```python
cmd = 'del /Q C:\\path\\file.exe'            # 单文件
cmd = 'del /Q C:\\temp\\*.tmp'               # 通配符
cmd = 'rmdir /S /Q C:\\path\\to\\dir'        # 目录含子目录
```

### 5.4 创建目录

```python
cmd = 'mkdir C:\\path\\to\\dir 2>nul'  # 2>nul 忽略已存在
```

---

## 6. 进程管理模板

### 6.1 启动进程

```python
# 前台进程（会等待退出）
cmd = 'C:\\computehub\\wanlida.exe worker --gw http://36.250.122.43:8282 --node-id wanlida-temp'
# ⚠️ 长进程 timeout=60 会超时返回，但进程继续在远端运行
# 通过 tasklist 验证是否启动成功

# 后台进程（用 start /B）
cmd = 'start /B "" C:\\computehub\\wanlida.exe worker --gw http://36.250.122.43:8282 --node-id wanlida-temp'
```

### 6.2 查询进程

```python
cmd = 'tasklist | findstr wanlida'
cmd = 'netstat -ano | findstr :8383'
```

### 6.3 终止进程

```python
cmd = 'taskkill /F /IM wanlida.exe'     # 按名称
cmd = 'taskkill /F /PID 1234'           # 按 PID
```

---

## 7. Windows 服务管理

> Windows 服务是长期驻留进程的标准管理方式，比手动启动更可靠。

### 7.1 查询服务状态

```batch
sc.exe query wanlida-service
# 输出: STATE: 1  STOPPED  |  4  RUNNING
```

### 7.2 启动/停止服务

```batch
sc.exe start wanlida-service
timeout /t 3 && sc query wanlida-service    # 验证 STATE: 4  RUNNING

sc.exe stop wanlida-service
timeout /t 5
```

### 7.3 创建服务

```batch
# ⚠️ 经典坑: = 后必须有空格！否则 sc.exe 不报错但创建失败
sc.exe create wanlida-service binpath= "C:\computehub\wanlida.exe worker ..." start= auto displayname= "Wanlida Worker"

# 自动重启策略
sc.exe failure wanlida-service reset= 86400 failures= 5 restart= 5
# 3 次失败后重启，重启间隔 5s，24h 重置计数器
```

### 7.4 删除服务

```batch
sc.exe stop wanlida-service
timeout /t 3
sc.exe delete wanlida-service
```

### 7.5 服务 vs 定时任务 vs start /B

| 方案 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| **Windows 服务** | 长期运行 | 自动重启、开机自启 | 需管理员 |
| **schtasks 定时任务** | 任意进程 | 简单、灵活 | 无自动重启 |
| **start /B** | 临时后台 | 最简单 | 会话断开可能影响 |

---

## 8. 环境变量管理

### 8.1 读取

```batch
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path
echo %TEMP%
```

### 8.2 设置（按推荐度排序）

| 方式 | 作用域 | 立即生效 | 推荐度 |
|------|--------|----------|--------|
| **PowerShell -EncodedCommand** | 系统级 | ✅ | ⭐⭐⭐⭐⭐ |
| **reg add** | 系统级 | ✅ | ⭐⭐⭐ |
| **setx** | 用户/系统级 | ❌ 新 shell 才生效 | ⭐⭐ |

#### 方式 A：PowerShell -EncodedCommand（推荐）

```python
import base64
ps_code = "[Environment]::SetEnvironmentVariable('MY_VAR','value','Machine')"
b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
# submit: powershell -EncodedCommand {b64}
```

#### 方式 B：reg add

```batch
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v MY_VAR /t REG_SZ /d "value" /f
```

### 8.3 PATH 批量更新

```python
import base64
paths = ["C:\\Progra~1\\Go\\bin", "C:\\computehub"]
path_str = ";".join(paths)
ps_code = f"[Environment]::SetEnvironmentVariable('Path','{path_str};'+[Environment]::GetEnvironmentVariable('Path','Machine'),'Machine')"
b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
```

### 8.4 验证

```batch
echo %MY_VAR%
echo %PATH% | findstr /I "computehub"
```

---

## 9. 注册表操作

### 9.1 读取

```batch
reg query "HKLM\SOFTWARE\wanlida" /v Version
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Go" 2>nul
```

### 9.2 写入

```batch
reg add "HKLM\SOFTWARE\wanlida" /v Version /t REG_SZ /d "1.3.26" /f
reg add "HKLM\SOFTWARE\wanlida" /v LogLevel /t REG_DWORD /d 2 /f
```

### 9.3 备份/删除

```batch
reg export "HKLM\SOFTWARE\wanlida" C:\temp\backup.reg /y
reg delete "HKLM\SOFTWARE\wanlida" /v OldValue /f
```

---

## 10. 定时任务管理 (schtasks)

> Windows 任务计划程序，适合长期服务部署。

### 10.1 创建

```batch
schtasks /create /tn "WanlidaWorker" /tr "C:\computehub\wanlida.exe worker ..." /sc onlogon /ru SYSTEM /rl HIGHEST
```

### 10.2 管理

```batch
schtasks /query /tn "WanlidaWorker" /fo LIST
schtasks /run /tn "WanlidaWorker"
schtasks /end /tn "WanlidaWorker"
schtasks /delete /tn "WanlidaWorker" /f
```

---

## 11. 防火墙规则管理

### 11.1 查看

```batch
netsh advfirewall show allprofiles state
netsh advfirewall firewall show rule name=all
```

### 11.2 添/删规则

```batch
netsh advfirewall firewall add rule name="WanlidaWorker" dir=in action=allow protocol=TCP localport=8383
netsh advfirewall firewall delete rule name="WanlidaWorker"
```

---

## 12. 大文件传输方案

> ⚠️ wanlida-opc01 HTTP 下载不通，需要替代方案。

### 12.1 方案对比

| 方案 | 限制 | 网络要求 | 速度 | 场景 |
|------|------|----------|------|------|
| Gateway 内置下载 | ~10MB | HTTP 可达 | 慢 | 小 binary |
| **base64 分块** | 不限 | WS 可达 | 中 | 配置文件/脚本 ✅ 首选 |
| SCP/SFTP | 不限 | SSH 可达 | 快 | 内网节点 |
| PowerShell 下载 | 不限 | HTTP 可达 | 中 | 替代 curl |

### 12.2 base64 分块（WS 可用时的万能方案）

```python
import base64
# 小文件直接传
with open('config.yaml', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('ascii')
cmd = f'echo {b64} > C:\\temp\\file.b64 && certutil -decode C:\\temp\\file.b64 C:\\target\\file'
```

### 12.3 PowerShell 下载（HTTP 可达时）

```python
import base64
ps_script = r"""$wc=New-Object System.Net.WebClient;$wc.DownloadFile('http://url/file.exe','C:\target\file.exe');Write-Output 'OK'"""
b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()
# submit: powershell -EncodedCommand {b64}
```

### 12.4 传输验证

```batch
dir C:\target\file.exe                    # 检查大小
certutil -hashfile C:\target\file.exe SHA256  # 检查哈希
```

---

## 13. 多步骤编排与条件分支

### 13.1 条件分支

```python
def conditional_download(node_id, file_path, download_url):
    check = run(node_id, f'dir "{file_path}" 2>nul && echo EXISTS || echo MISSING', 10)
    if 'EXISTS' in (check.get('stdout') or ''):
        print(f"  ✅ {file_path} 已存在，跳过")
        return True
    dl = run(node_id, f'curl -L -o "{file_path}" "{download_url}"', 300)
    return dl and dl.get('exit_code') == 0
```

### 13.2 序列编排（失败停止）

```python
def sequential_ops(node_id, steps):
    for step in steps:
        result = run(node_id, step['command'], step.get('timeout', 60))
        if not result or result.get('exit_code') != 0:
            print(f"  ❌ '{step['label']}' 失败，中止")
            return False
    print(f"  ✅ 全部 {len(steps)} 步完成")
    return True
```

### 13.3 部署新版本示例

```python
steps = [
    {"label": "备份", "command": "copy /Y C:\\computehub\\computehub.exe C:\\computehub\\computehub.exe.bak", "timeout": 15},
    {"label": "下载", "command": "curl -L -o C:\\computehub\\computehub_new.exe http://...", "timeout": 300},
    {"label": "替换", "command": "copy /Y C:\\computehub\\computehub_new.exe C:\\computehub\\computehub.exe", "timeout": 15},
    {"label": "验证", "command": "C:\\computehub\\computehub.exe --version", "timeout": 15},
]
sequential_ops("wanlida-opc01", steps)
```

### 13.4 并行检查

```python
import concurrent.futures
nodes = ["wanlida-opc01", "ecs-p2ph", "worker-arm"]
results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as ex:
    for nid in nodes:
        results[nid] = ex.submit(run, nid, "echo OK", 10).result()
```

### 13.5 回滚机制

```python
def deploy_with_rollback(node_id, upgrade_steps, rollback_steps):
    if not sequential_ops(node_id, upgrade_steps):
        print(f"  🔄 回滚...")
        sequential_ops(node_id, rollback_steps)
```

---

## 14. 日志与审计

### 14.1 操作日志记录

```python
import json
from datetime import datetime

def log_operation(node_id, operation, command, result):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "node_id": node_id,
        "operation": operation,
        "exit_code": result.get('exit_code') if result else None,
    }
    append_cmd = f'echo {json.dumps(entry, ensure_ascii=False)} >> C:\\computehub\\ops.log'
    submit(node_id, append_cmd, timeout=15)
```

### 14.2 审计标准格式

```json
{
    "timestamp": "2026-06-13T15:58:00+08:00",
    "node_id": "wanlida-opc01",
    "operation": "copy",
    "command": "copy /Y C:\\computehub\\computehub.exe C:\\computehub\\wanlida.exe",
    "exit_code": 0,
    "stdout": "1 file(s) copied.",
    "status": "success"
}
```

### 14.3 查询日志

```batch
powershell -Command "Get-Content C:\computehub\ops.log -Tail 10"
```

---

## 15. 常见问题与预案

### ❌ Q1: certutil -decode 报 ERROR_FILE_EXISTS

**根因**: 旧 `script.b64` / `script.js` 未清理，certutil 拒绝覆盖。  
**预案**: 命令链首行加 `del /Q C:\\temp\\*.b64 2>nul && del /Q C:\\temp\\*.js 2>nul && del /Q C:\\temp\\*.txt 2>nul && ...`

### ❌ Q2: JS 脚本中 `\t` 解析为制表符

**根因**: `\t` → tab 字符，路径崩溃。  
**预案**: 路径中 `\\t` 在 JS 里写 `\\\\t`（四反斜杠 → 两个 → cmd 处理为一个）。

### ❌ Q3: 节点 online 但操作超时

**根因**: 网络分层 — WS 存活但 HTTP 不通。  
**预案**: 先 `echo` 测试 → 简单命令可用 → 大文件走 base64 分块。

### ❌ Q4: 长进程 timeout

**根因**: worker 是后台常驻进程，不会退出，Gateway 超时强制中断。  
**预案**: timeout ≥60s → 超时不代表失败 → 用 `tasklist` 验证进程存在。

### ❌ Q5: Gateway API 端点 404

**根因**: 版本变更或路由调整。  
**预案**: submit 成功后等待重试 detail → 通过本地命令间接验证（如 `tasklist`）。

### ❌ Q6: 临时文件路径中文字符编码

**根因**: cmd 默认 GBK，node.js 用 UTF-8。  
**预案**: JS 中指定 `{encoding:'utf8'}`，结果写入文件后用 `type` 读取。

### ❌ Q7: sc.exe 创建服务失败（经典坑）

**现象**: `sc.exe create svc binpath="路径"` 无反应，创建空服务。  
**根因**: `=` 后必须有空格！`binpath= "路径"` 才对。  
**预案**: 严格遵循 `sc.exe create 名 binpath= "路径" start= auto`。

---

## 16. 附录：命令速查表

### 16.1 节点诊断

```batch
echo OK
systeminfo | findstr "OS Name|OS Version"
wmic logicaldisk get caption,freespace,size
echo %PROCESSOR_ARCHITECTURE%
tasklist /FI "IMAGENAME eq computehub.exe"
netstat -ano | findstr LISTENING
whoami
```

### 16.2 服务管理

```batch
sc.exe query wanlida-service
sc.exe start wanlida-service
sc.exe stop wanlida-service
sc.exe create wanlida-service binpath= "路径" start= auto
sc.exe delete wanlida-service
```

### 16.3 文件操作

```batch
dir C:\target\
copy /Y C:\src\file.exe C:\dst\file.exe
move /Y C:\src\file.exe C:\dst\file.exe
del /Q C:\file.exe
certutil -hashfile C:\file.exe SHA256
```

### 16.4 环境变量

```batch
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path
echo %TEMP%
set
```

### 16.5 定时任务

```batch
schtasks /query /tn "Name" /fo LIST
schtasks /create /tn "Name" /tr "路径" /sc onlogon /ru SYSTEM
schtasks /run /tn "Name"
schtasks /delete /tn "Name" /f
```

### 16.6 防火墙

```batch
netsh advfirewall show allprofiles state
netsh advfirewall firewall add rule name="Name" dir=in action=allow protocol=TCP localport=8383
netsh advfirewall firewall delete rule name="Name"
```

### 16.7 注册表

```batch
reg query "HKLM\SOFTWARE\wanlida" /v Version
reg add "HKLM\SOFTWARE\wanlida" /v Version /t REG_SZ /d "1.3.26" /f
reg export "HKLM\SOFTWARE\wanlida" C:\temp\backup.reg /y
```

### 16.8 路径要点

| 场景 | 写法 | 示例 |
|------|------|------|
| Python r-string + JS | `r'''C:\\temp\\file.txt'''` | ✅ |
| Python 普通 string + JS | `'C:\\\\temp\\\\file.txt'` | ✅ |
| JS execFileSync 路径 | `'/C','dir C:\\path\\'` | ✅ |
| ❌ 绝对不要用 | `r'C:\temp\file'` 在 JS 里 | `\t` → tab |

### 16.9 Python 工具函数

```python
import base64, json, urllib.request, time

GW_BASE = "http://36.250.122.43:8282"

def submit(node_id, cmd, timeout=60, priority=8):
    payload = json.dumps({"node_id": node_id, "command": cmd, "timeout": timeout, "priority": priority}).encode()
    req = urllib.request.Request(f"{GW_BASE}/api/v1/tasks/submit", data=payload, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read()).get("data", {}).get("task_id", "")

def wait(task_id, poll_interval=2, max_wait=120):
    for _ in range(max_wait // poll_interval):
        time.sleep(poll_interval)
        try:
            resp = json.loads(urllib.request.urlopen(f"{GW_BASE}/api/v1/tasks/detail?task_id={task_id}", timeout=10).read())
            status = resp.get("data", {}).get("status")
            if status in ["completed", "failed", "cancelled"]:
                return resp.get("data")
        except: pass
    return None

def run(node_id, cmd, timeout=60):
    task_id = submit(node_id, cmd, timeout)
    print(f"  ⏳ Task: {task_id}")
    result = wait(task_id)
    if result:
        print(f"  Exit: {result.get('exit_code','?')}, Stdout: {(result.get('stdout') or '')[:500]}")
    else:
        print(f"  ⚠️ Timeout")
    return result
```

---

## 17. 实用运维场景模板

### 17.1 全集群健康检查（一键脚本）

```python
def cluster_health_check():
    """一键检查所有节点的运行状态"""
    nodes = {
        "wanlida-opc01": {"expected_version": "1.3.26", "expected_memory_gb": 16},
        "ecs-p2ph": {"expected_version": "1.3.26"},
        "windows-mobile": {"expected_version": "1.3.25"},
    }
    
    results = {}
    for nid, config in nodes.items():
        # Step 1: 检查在线
        r = run(nid, "echo OK", 10)
        if not r or r.get('exit_code') != 0:
            results[nid] = {"status": "OFFLINE"}
            continue
        
        # Step 2: 查系统信息
        script = r"""var cp=require('child_process');
        var fs=require('fs');
        try {
            var r=cp.execFileSync('systeminfo',{encoding:'utf8',timeout:60000});
            fs.writeFileSync('C:\\temp\\health.txt',r,'utf8');
            console.log('OK');
        } catch(e) {
            fs.writeFileSync('C:\\temp\\health.txt','ERROR:'+e.message,'utf8');
        }"""
        r = run(nid, base64_node_cmd(script), 60)
        
        # Step 3: 查进程
        r = run(nid, "tasklist | findstr computehub.exe", 10)
        
        # Step 4: 查磁盘
        r = run(nid, "wmic logicaldisk get caption,freespace", 10)
        
        results[nid] = {
            "status": "ONLINE",
            "system_info": (r.get('stdout') or '')[:500] if r else "",
            "process": (run(nid, "tasklist | findstr computehub.exe", 10).get('stdout') or '')[:200],
        }
    
    return results
```

### 17.2 新节点批量部署（Windows）

```python
def deploy_node(node_id, gateway_url, node_name, binary_path="C:\\computehub\\computehub.exe"):
    """部署新节点到集群的完整流程"""
    steps = [
        # 1. 创建安装目录
        {"label": "创建目录", "command": f"mkdir C:\\computehub 2>nul", "timeout": 15},
        
        # 2. 下载 binary
        {"label": "下载 binary", "command": f"curl -L -o {binary_path} http://<gateway>/api/v1/download?file=computehub.exe&platform=windows/amd64", "timeout": 300},
        
        # 3. 验证 binary
        {"label": "验证文件", "command": f"certutil -hashfile {binary_path} SHA256", "timeout": 15},
        
        # 4. 创建服务
        {"label": "注册服务", "command": f'sc.exe create {node_name}-worker binpath= "{binary_path} worker --gw {gateway_url} --node-id {node_name}" start= auto displayname= "{node_name} Worker"', "timeout": 30},
        
        # 5. 启动服务
        {"label": "启动服务", "command": f"sc.exe start {node_name}-worker", "timeout": 30},
        
        # 6. 验证注册
        {"label": "验证服务", "command": f"sc.exe query {node_name}-worker", "timeout": 15},
    ]
    return sequential_ops(node_id, steps)
```

### 17.3 故障排查流程（标准诊断包）

```python
def diagnose_node(node_id):
    """标准诊断：收集所有关键信息"""
    results = {}
    
    # 基本信息
    results['os'] = run(node_id, 'systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"', 15)
    results['disk'] = run(node_id, 'wmic logicaldisk get caption,freespace,size', 10)
    results['network'] = run(node_id, 'ipconfig /all | findstr /C:"IPv4" /C:"Subnet" /C:"Default Gateway"', 10)
    results['processes'] = run(node_id, 'tasklist /FI "IMAGENAME eq computehub.exe" /FI "STATUS eq RUNNING"', 10)
    results['services'] = run(node_id, 'sc.exe query type= service state= all | findstr "wanlida"', 10)
    results['firewall'] = run(node_id, 'netsh advfirewall show allprofiles state', 10)
    results['events'] = run(node_id, 'wevtutil qe Application /q:*[System[Provider[@Name=\'wanlida-worker\']]] /c:5 /f:text', 15)
    
    return results
```

### 17.4 Python Win32 API 自动化（高级操作）

> 当 Windows 命令不够用时，用 Python + pywin32 直接操作 Windows API。

#### GPU 查询（Python + wmi 模块）

```python
import base64

script = r"""var cp=require('child_process');
var fs=require('fs');
try {
    // 用 Python + wmi 模块查询 GPU
    var r=cp.execFileSync('cmd',['/C','python -c "import wmi; c=wmi.WMI(); print([g.Name for g in c.Win32_VideoController()])" > C:\\temp\\gpu.txt'],{encoding:'utf8',timeout:30000});
    fs.writeFileSync('C:\\temp\\result.txt','python wmi check done','utf8');
} catch(e) {
    fs.writeFileSync('C:\\temp\\result.txt','ERROR:'+e.message,'utf8');
}"""
```

#### 文件操作（Python pywin32）

```python
script = r"""var cp=require('child_process');
var fs=require('fs');
try {
    // 用 PowerShell + win32com 查询服务
    var r=cp.execFileSync('powershell',['-Command','Get-Service | Where-Object {$_.Status -eq \'Running\'} | Select-Object Name,Status | Format-Table -AutoSize'],{encoding:'utf8',timeout:30000});
    fs.writeFileSync('C:\\temp\\services.txt',r,'utf8');
    console.log('OK');
} catch(e) {
    fs.writeFileSync('C:\\temp\\services.txt','ERROR:'+e.message,'utf8');
}"""
```

---

## 18. FAQ 补充

### ❌ Q8: 通过 Gateway 执行命令时中文乱码

**现象**: `dir` 目录中有中文文件，stdout 出现乱码。

**根因**: cmd 默认 GBK 编码（chcp 936），Node.js 用 UTF-8 读取。

**预案**:
```batch
# 方案1: 设置代码页
chcp 65001 >nul && dir C:\path\

# 方案2: 在 cmd 中指定
cmd /C "chcp 65001 & dir C:\path"

# 方案3: 读取文件时用 UTF-8 编码
cp.execFileSync('cmd', ['/C', 'chcp 65001 >nul & dir C:\\path'], {encoding: 'utf8'})
```

### ❌ Q9: 命令中含有管道符 `|` 被截断

**现象**: `tasklist | findstr python` 只执行 `tasklist`，`findstr` 被忽略。

**根因**: Gateway 层对管道符有特殊处理。

**预案**:
```python
# 方案1: 用 cmd /C 包裹
cmd = 'cmd /C "tasklist | findstr python"'

# 方案2: 用 powershell 执行
cmd = 'powershell -Command "tasklist | select-string python"'

# 方案3: 分两步（先查全部，再在本地过滤）
```

### ❌ Q10: 需要安装 Python 等依赖

**现象**: Windows 上没有 Python/Node.js，无法执行复杂操作。

**预案**:
1. 先检查已有: `where python`, `where node`
2. 已有则直接用; 没有则先安装
3. 安装后验证完整路径: `C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe --version`

### ❌ Q11: 任务提交成功但节点不执行

**现象**: submit 返回 task_id 但轮询一直 `status=None`。

**排查**:
1. 先 `echo OK` 确认节点是否真在线
2. 检查节点是否有能力执行（是否有 Python/node 等依赖）
3. 检查 Gateway 是否正在分配任务（可能有其他节点在抢）
4. 提升优先级: `"priority": 10`（1-10，10最高）

### ❌ Q12: 需要执行交互式程序（如 nvidia-smi 带 UI）

**现象**: 某些命令行工具会弹出 UI 窗口。

**预案**:
```python
# nvidia-smi 通常有 UI 输出，但可以用 -q 参数静默查询
cmd = 'nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader'
# 或者用 wmi 模块（需要 Python + wmi）
```

---

## 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-13 | v1.2 | +实用运维场景（健康检查/批量部署/故障排查） +Python Win32 API +FAQ Q8-Q12（中文乱码/管道截断/依赖安装/任务不执行/交互式程序） |
| 2026-06-13 | v1.1 | +Windows 服务管理 +环境变量管理 +注册表 +定时任务 +防火墙 +大文件传输 +多步骤编排 +日志审计 +sc.exe 坑 |
| 2026-06-13 | v1.0 | 初版，基于 wanlida-opc01 实战 |

---

*本文档由端智编写，2026-06-13。持续更新中。*
