# WIN-STD-001: Windows远程软件安装标准流程

> 建立时间: 2026-05-18
> 版本: v1.2
> 适用场景: 通过 ComputeHub Worker 向远程节点静默安装/更新软件
> 
> **v1.2 更新**: 新增 Git/FFmpeg/Node.js 安装模板 + PowerShell -EncodedCommand 正式升级为 PATH 更新首选方案 + LTSC 兼容性说明（基于 Windows-mobile-01 下午实战）
> **v1.1 更新**: 新增 ComputeHub Gateway API 安装模式 & Linux 节点安装扩展（基于 ECS 实战经验）

---

## 目录

1. [安装前检核清单](#1-安装前检核清单)
2. [安装执行流程](#2-安装执行流程)
3. [安装后验证](#3-安装后验证)
4. [ComputeHub Gateway API 安装模式](#4-computehub-gateway-api-安装模式)
5. [Linux 节点安装扩展](#5-linux-节点安装扩展)
6. [常见问题与预案](#6-常见问题与预案)
7. [附录：命令速查表](#7-附录命令速查表)

---

## 1. 安装前检核清单

### □ 1.1 目标节点确认

| 检查项 | 方法 | 通过标准 |
|--------|------|----------|
| 节点在线 | 向目标节点提交 `echo OK` | 返回 `status=completed exit=0` |
| 磁盘空间 | 提交 `dir C:\` 或 `wmic logicaldisk get size,freespace` | 剩余空间 ≥ 安装包 3 倍 |
| 架构确认 | 提交 `echo %PROCESSOR_ARCHITECTURE%` | amd64 / ARM64 |
| OS 版本 | 提交 `ver` | 确认兼容性 |
| 管理员权限 | 提交 `net session >nul 2>&1 && echo ADMIN || echo NOT_ADMIN` | 返回 ADMIN |

### □ 1.2 安装包就绪

| 检查项 | 方法 | 通过标准 |
|--------|------|----------|
| 下载源可达 | 提交 `curl -sI https://go.dev/dl/go1.26.3.windows-amd64.msi 2>&1` | HTTP 200 |
| 本地缓存 | 提交 `dir C:\installers\ /b 2>nul` | 如已有缓存则跳过下载 |
| 安装包哈希 | `certutil -hashfile <file> SHA256` | 与官方一致 |

### □ 1.3 路径检查（仅首次安装）

```batch
rem 检查是否已安装
C:\Program Files\Go\bin\go.exe version
C:\Go\bin\go.exe version
where go 2>nul
```
如果返回版本号 → 安装已存在，确认是否需要升级/跳过。

---

## 2. 安装执行流程

### 2.1 总流程图

```
准备阶段
  ├─ 检查节点在线 → 异常则中止
  ├─ 检查已安装 → 已装则跳过或升级
  ├─ 检查磁盘空间 → 不足则报错
  └─ 创建 C:\installers\ 目录
  
下载阶段
  ├─ 下载安装包到 C:\installers\
  ├─ 验证文件存在（大小/哈希）
  └─ 检查 exit_code = 0

安装阶段
  ├─ 执行静默安装命令
  ├─ 等待时间 = timeout × 0.5 后轮询
  └─ 确认 exit_code = 0 且进程未卡死

验证阶段
  ├─ 软件路径直接调用（不用 PATH 依赖）
  ├─ 软件版本号确认
  └─ 功能测试（跑 hello world）

收尾阶段
  ├─ 安装完成标记
  ├─ 更新 PATH（如需要）
  └─ 清除安装包（可选）
```

### 2.2 安装命令规范

#### 通用规则

| 规则 | 说明 |
|------|------|
| **优先 MSI** | MSI 比 EXE 更可靠，支持 msiexec 统一管理 |
| **使用 8.3 短名** | `C:\Progra~1\` 避免空格引号问题 |
| **JSON 引号转义** | Windows cmd 双引号在 JSON 中要 `\\\"` 转义 |
| **timeout 留余量** | 下载设 300s，安装设 120s，下载后等至少 60s 再查 |
| **分步而非嵌套** | 不要一条命令 curl && msiexec，拆成两步 |

#### 常用软件安装模板

**Python (EXE)**
```batch
C:\python-3.11.6-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
```

**Go (MSI)**
```batch
msiexec /i C:\installers\go1.26.3.windows-amd64.msi /quiet /norestart
```

**Git (EXE)** — 2026-05-18 实战验证 ✅
```batch
C:\installers\Git-2.54.0-64-bit.exe /SILENT /NORESTART
```
- 验证: `C:\Progra~1\Git\bin\git.exe --version`
- PATH 补（PowerShell -EncodedCommand）:
```python
import base64
ps_code = "[Environment]::SetEnvironmentVariable('Path', 'C:\\Program Files\\Git\\bin;' + [Environment]::GetEnvironmentVariable('Path','Machine'), 'Machine')"
b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
submit(f"powershell -EncodedCommand {b64}", 15)
```

**FFmpeg (ZIP/单exe)** — 2026-05-18 实战验证 ✅
FFmpeg 没有传统安装器，只需下载 ffmpeg.exe 放到目录并补 PATH：
```batch
rem 1. 创建目录
cmd /c mkdir "C:\Program Files\FFmpeg\bin" 2>nul

rem 2. 下载 ffmpeg.exe
curl -L -o C:\Progra~1\FFmpeg\bin\ffmpeg.exe https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
rem 或用 winrar/7z 解压后提取 ffmpeg.exe

rem 3. 验证
C:\Progra~1\FFmpeg\bin\ffmpeg.exe -version
```
- ✅ **不需要安装器**，一个 exe 就够了
- PATH 补法同上 PowerShell -EncodedCommand（路径：`C:\Program Files\FFmpeg\bin`）

**Node.js (MSI)** — ⚠️ **LTSC 2019 不兼容，优先 ZIP 版**
```batch
rem ❌ MSI 方式（LTSC 2019 会 exit 1620）
msiexec /i C:\installers\node-v20.xx.0-x64.msi /quiet /norestart

rem ✅ ZIP 方式（LTSC 2019 已验证）
rem 1. 下载 ZIP
curl -L -o C:\installers\node-v18.20.8-win-x64.zip https://nodejs.org/dist/v18.20.8/node-v18.20.8-win-x64.zip

rem 2. PowerShell 解压
powershell -Command "Expand-Archive -Path C:\installers\node-v18.20.8-win-x64.zip -DestinationPath 'C:\Program Files\nodejs\' -Force"

rem 3. 验证
C:\Progra~1\nodejs\node.exe --version
C:\Progra~1\nodejs\npm.cmd --version
```
- **2026-05-18 经验**: LTSC 2019 不支持 Node 20+，ZIP 二进制版比安装器更可靠
- npm 10.8.2 在 v18.20.8 下正常工作

**Chrome (MSI)**
```batch
msiexec /i C:\installers\googlechromestandaloneenterprise64.msi /quiet /norestart
```

### 2.3 PATH 更新规范

> ⚠️ **核心教训**：安装程序声称的 "Add to PATH" 不总是可靠，必须验证后手动补

#### PATH 更新方法（按优先级排序）

**方法 A：PowerShell -EncodedCommand（推荐 ⭐ 2026-05-18 实测最优解）**
```python
import base64
ps_code = "[Environment]::SetEnvironmentVariable('Path', 'C:\\Program Files\\Git\\bin;' + [Environment]::GetEnvironmentVariable('Path','Machine'), 'Machine')"
b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
submit(f"powershell -EncodedCommand {b64}", 15)
```
- **优点**: 零转义问题、零引号嵌套、一次性写入注册表、立即生效
- **验证**: 同样用 PowerShell 读取
```python
ps_read = '[Environment]::GetEnvironmentVariable("Path","Machine").Contains("Git")'
b64 = base64.b64encode(ps_read.encode('utf-16le')).decode()
submit(f"powershell -EncodedCommand {b64}", 10)
# 预期: exit=0, stdout="True"
```
- **注意事项**:
  - BOM: UTF-16LE 是 PowerShell -EncodedCommand 的标准编码
  - 路径中 `\` 在 Python 字符串里要 `\\`
  - 可以用 `;` 拼接多个路径：`C:\\Progra~1\\Git\\bin;C:\\Progra~1\\FFmpeg\\bin;`
  - 路径字符串中空格不影响（PowerShell 处理没问题）

**方法 B：注册表直接写入（备选）**
```batch
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path /t REG_EXPAND_SZ /d "C:\Program Files\Go\bin;%PATH%" /f
```
- 优点：立即生效，不需要重启
- 缺点：`%PATH%` 展开后可能超长，遇到空格在 cmd 上下文容易出错

**方法 C：setx 系统级（备选但有坑）**
```batch
setx PATH "C:\Program Files\Go\bin;C:\Program Files\Go;C:\Program Files\Python311;%PATH%" /M
```
- ⚠️ `/M` 必须在**参数末尾**，不能在变量名前
- ⚠️ `%PATH%` 展开后可能超长（≥1024字符截断），需先 `echo %PATH% > C:\path_backup.txt`
- ⚠️ 双引号内的反斜杠在 cmd 上下文中容易产生嵌套问题

**方法 D：用户级 PATH（不需要管理员）**
```batch
setx PATH "C:\Program Files\Go\bin;%PATH%"
```

#### PATH 批量合并技巧（2026-05-18 经验）
安装多个软件后，**不需要每个软件单独补一次 PATH**，最后一次性补：
```python
# 合并 PATH：Git + FFmpeg + Node.js 一次搞定
paths = [
    "C:\\Program Files\\Git\\bin",
    "C:\\Program Files\\FFmpeg\\bin",
    "C:\\Program Files\\nodejs",
]
combined = ";".join(paths)
ps_code = f"[Environment]::SetEnvironmentVariable('Path', '{combined};' + [Environment]::GetEnvironmentVariable('Path','Machine'), 'Machine')"
b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
submit(f"powershell -EncodedCommand {b64}", 15)
```

#### PATH 验证
```batch
cmd /c "echo %PATH% | findstr /I Git"
```
以及 PowerShell 读取法（见方法 A 验证部分）。

### 2.4 Python 脚本封装规范

当安装步骤 > 3 步时，**禁止**每次手动提交，必须用 Python 脚本统一管理：

```python
"""安装模板 - 三步走"""
def step1_download(): ...
def step2_install(node, cmd, timeout=120): ...
def step3_verify(node, verify_cmd): ...
```

脚本文件保存到 Gateway 服务器的 `~/` 下，可复用。

---

## 3. 安装后验证

### 3.1 即时验证（必须做）

```python
# Python 验证
submit('C:\\Progra~1\\Python311\\python.exe --version', 10)

# Go 验证
submit('C:\\Progra~1\\Go\\bin\\go.exe version', 10)

# npm 验证
submit('C:\\Progra~1\\nodejs\\npm.cmd --version', 10)
```

> **不要**用 `python --version` 或 `go version`（不加路径）。  
> 这些依赖 PATH，而 PATH 在安装后可能未更新。

### 3.2 PATH 验证（额外做）

```batch
cmd /c where python
cmd /c where go
```

### 3.3 注册表验证（额外做）

```batch
reg query HKLM\SOFTWARE\Go /v InstallDir
reg query HKLM\SOFTWARE\Python\PythonCore\3.11\InstallPath /ve
```

### 3.4 功能测试（推荐做）

```python
# Python
submit('python -c "import sys; print(sys.version)"', 10)

# Go
submit('go version', 10)
```

---

## 4. ComputeHub Gateway API 安装模式

> 💡 **2026-05-18 实战验证**: ECS 服务器 Git 安装全程通过 ComputeHub Gateway API 完成，零 SSH。
> 
> **端点**: `http://<gateway>:8282/api/v1/tasks/submit` + `tasks/detail`

### 4.1 API 工作流

```
Submit ─→ Poll Detail ──→ 成功
  │          │
  │    status=None → 等+重试
  │    exit_code≠0 → 排查
  │    exit_code=0 → 验证
  └──────────┘
```

### 4.2 Python 客户端模板

```python
"""ComputeHub Gateway API 安装客户端"""
import json, urllib.request, time

GW = "http://<gateway-ip>:8282"  # 替换为你的 Gateway 地址

def submit(cmd, timeout, node=None):
    """通过 Gateway API 提交任务"""
    body = {
        "command": cmd,
        "timeout": timeout,
        "priority": 10,
        "source_type": "direct"
    }
    if node:
        body["assigned_node"] = node
    
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def wait(task_id, poll_interval=3, max_wait=120):
    """轮询任务结果，直到 status=completed"""
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        resp = json.loads(urllib.request.urlopen(
            f"{GW}/api/v1/tasks/detail?task_id={task_id}", timeout=10
        ).read())
        data = resp.get("data", {})
        status = data.get("status")
        if status == "completed":
            return data
        elif status == "failed":
            return data
        # status=None 或 pending → 继续等
    return data  # 超时返回最后数据

def run(cmd, timeout=30, node=None, label=""):
    """submit + wait + log 一步到位"""
    tid = submit(cmd, timeout, node)
    print(f"  ⏳ {label}: task_id={tid}")
    data = wait(tid, poll_interval=2, max_wait=timeout + 10)
    stdout = (data.get("stdout") or "").strip()
    stderr = (data.get("stderr") or "").strip()
    exit_code = data.get("exit_code")
    status = data.get("status")
    
    print(f"     exit_code={exit_code}, status={status}")
    if stdout:
        print(f"     stdout: {stdout[:200]}")
    return data
```

### 4.3 ⚠️ 关键实战教训

#### 🎯 教训 1：Worker 用户 ≠ root
**现象**: `apt-get install -y git` → `Permission denied (13)`
**根因**: Worker 进程默认以低权限 user 运行，没有 `sudo` 或 root
**解决**:
- **方案 A**（已验证 ✅）: 目标用户有 `NOPASSWD` sudo → `sudo apt-get install -y <pkg>`
- **方案 B**: Worker 配置为 root 用户运行（需 security review）
- **方案 C**: 提前配置 `computeHub ALL=(ALL) NOPASSWD: ALL` 在 `/etc/sudoers`

#### 🎯 教训 2：永远用完整路径验证
**现象**: `git --version` = OK，`go version` = OK（在同一 shell 内正常）
**原则**: **验证命令永远用完整路径**，不依赖 shell 继承环境
```
✅ /usr/bin/git --version
✅ /usr/local/go/bin/go version
❌ git --version
❌ go version
```

#### 🎯 教训 3：API 响应模式
```python
# Submit 响应结构
{ "code": 0, "data": { "task_id": "cm8jxxx" } }

# Detail 响应结构（未完成）
{ "code": 0, "data": { "status": None } }

# Detail 响应结构（已完成）
{ "code": 0, "data": { "status": "completed", "exit_code": 0,
                        "stdout": "...", "stderr": "" } }
```

- **status=None** → 任务未开始或未分配，**不要放弃**，继续 poll
- **poll_interval ≤ 3s** → 足够快不浪费
- **max_wait ≥ timeout + 10s** → 留 buffer

#### 🎯 教训 4：不要一条命令搞定一切
```python
# ❌ 错误：apt-get && git --version 合一条（失败后不知哪步的问题）
# ✅ 正确：拆成 submit → wait → verify 三步
tid = submit("sudo apt-get install -y git", 120)  # 第1步：安装
wait(tid)
tid = submit("/usr/bin/git --version", 10)         # 第2步：验证
d = wait(tid)
```

---

## 5. Linux 节点安装扩展

> 虽然 WIN-STD 源于 Windows，但 ComputeHub Worker 同样面向 Linux 节点。  
> **E-001 实战**: 2026-05-18 ECS 服务器 Git 安装（Ubuntu 24.04 LTS）。

### 5.1 Linux vs Windows 对比

| 环节 | Windows | Linux |
|------|---------|-------|
| 包管理器 | winget / chocolatey | `apt`, `yum`, `dnf` |
| 静默安装 | msiexec / EXE flags | `apt-get install -y` |
| 权限 | Administrator | `sudo` / root |
| 验证路径 | `C:\Progra~1\Go\bin\go.exe` | `/usr/bin/git` |
| PATH 更新 | reg / setx | 系统级 `/etc/environment` |

### 5.2 Linux 安装流程

#### 步骤 1：确认用户与权限
```python
# 检查当前 worker 用户
tid = submit("whoami", 10)
# 检查 sudo 权限
tid = submit("sudo -n echo OK 2>&1", 10)
# 预期: 
#   "OK" → 有免密 sudo ✅
#   "sudo: a terminal is required" → 需要 tty sudo
#   "user is not in the sudoers file" → ❌ 无权限
```

#### 步骤 2：免密 sudo 配置（仅首次，需 root）
> 如果 worker 用户没有 sudo 权限，需要在目标节点预先配置：
```bash
# 在 /etc/sudoers.d/ 中添加:
echo "computeHub ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/computehub
```

#### 步骤 3：安装
```python
# apt 安装
tid = submit("sudo apt-get update -qq && sudo apt-get install -y git", 120)
data = wait(tid)

# 或：从官方下载二进制（无 root 需求）
tid = submit("curl -sL https://go.dev/dl/go1.26.3.linux-amd64.tar.gz | tar -C /usr/local -xz", 300)
```

#### 步骤 4：验证
```python
# ✅ 完整路径验证
tid = submit("/usr/bin/git --version", 10)
data = wait(tid)
assert data.get("exit_code") == 0
assert "git version" in (data.get("stdout") or "")

# 也验证 PATH 可找到
tid = submit("command -v git", 10)
```

### 5.3 Linux 常用安装命令

| 软件 | Ubuntu/Debian | CentOS/RHEL |
|------|--------------|-------------|
| Git | `sudo apt-get install -y git` | `sudo yum install -y git` |
| Python3 | `sudo apt-get install -y python3` | `sudo yum install -y python3` |
| Go | `sudo apt-get install -y golang` | `sudo yum install -y golang` |
| Node.js | `sudo apt-get install -y nodejs npm` | `sudo yum install -y nodejs npm` |
| Docker | `sudo apt-get install -y docker.io` | `sudo yum install -y docker` |

> ⚠️ **注意**: apt 安装的版本可能不是最新。如需精确版本，走源码/官网下载。

---

## 6. 常见问题与预案

### ❌ Q1: PATH 未生效

**现象**: 安装 exit_code=0 但 `python --version` → "not recognized"

**原因**: 
- 安装程序 `/PrependPath=1` 写入注册表但未广播
- Worker 任务运行在新 shell，未收到 PATH 更新事件
- setx 语法错误或权限不足

**解决**:
```batch
# 方案A：用完整路径运行
C:\Progra~1\Python311\python.exe --version

# 方案B：手动 setx
setx PATH "C:\Program Files\Python311;%PATH%" /M

# 方案C：重启 shell（对 worker 无效）
```

**预防**:
- 验证时**永远用完整路径**，不用依赖 PATH 的短命令
- 安装完成后用 Python 脚本统一补 PATH

### ❌ Q2: msiexec 任务挂死

**现象**: 提交安装任务后 `status=None` 持续超时，不返回 exit_code

**原因**:
- msiexec 启动子进程后父进程不会自动退出
- 任务 timeout 不够长
- msiexec 等待用户交互（尽管 `/quiet`）

**解决**:
```batch
# 检查 msiexec 是否还在跑
tasklist /fi "IMAGENAME eq msiexec.exe"

# 如有残留，强制结束
taskkill /f /im msiexec.exe /t
```

**预防**:
- MSI 安装 timeout ≥ 120s
- 安装后隔 30s 再做验证，不要立刻查
- 如果安装挂死，记录后走备选方案（手动装）

### ❌ Q3: JSON/Shell 引号嵌套问题

**现象**: Shell 报 "Syntax error"、"Unterminated string"

**根因**: Python 字符串 `"` + 外层 JSON `"` + Windows cmd `"` 三层嵌套

**适用场景**: Python 脚本内嵌 Windows cmd 命令时

**解决**:
```python
# ❌ 错误（三层嵌套直接写字符串）
# ✅ 正确：写入 .py 文件再 scp 到 ECS 执行
```

> **v1.1 补充**: ComputeHub API 模式下，`submit()` 的 `command` 参数在 Python 中构造，
> Linux 命令基本不受嵌套影响（单引号安全），Windows cmd 仍需注意。

**预防**:
- 安装脚本长度 < 5 行：直接 submit
- 安装脚本长度 ≥ 5 行：写入临时文件 → scp → ECS 执行
- Windows 路径中的反斜杠用 `\\` 或直接 `/`（cmd 兼容）

### ❌ Q4: Worker 提交后 status=None

**现象**: submit 返回 task_id 但 poll 一直 `status=None`

**原因**:
- 目标节点 worker 离线或心跳丢失
- gateway worker 路由不对
- 任务在队列中尚未被 worker 调度

**解决**:
```python
# 1. 检查节点是否在线
tid = submit("echo OK", 10, node="your-node-id")
wait(tid)

# 2. 增加初始等待
time.sleep(5)  # 等 workers 心跳和调度

# 3. 确保 poll_interval 够长
#    不要 < 2s 高频 poll
```

**预防**:
- 安装前先验证节点可达
- submit 后等至少 5s 再 poll
- poll_interval = 3s, max_wait = timeout + 10s 作为默认值

### ❌ Q5: 安装包下载超时

**现象**: curl 下载大文件（> 50MB）超时

**解决**: timeout 设 ≥ 300s（5分钟），或改用后台下载

**预防**:
- 在 gateway ECS 服务器先下载好，用 `scp` 传上去
- 或创建 `C:\installers\` 缓存目录，重装复用

### ❌ Q6: Worker 用户权限不足 (v1.1 新增)

**现象**: `apt install` / `msiexec` → Permission denied

**根因**: Worker 进程以低权限用户执行，安装需要 root/Administrator

**解决**:
- **方案 A**（已验证 ✅）: 目标用户有 `NOPASSWD` sudo → 用 `sudo` 执行
- **方案 B**: Worker 配置为特权用户
- **方案 C**: 目标节点预先配置 `/etc/sudoers.d/` 授权

**预防**:
- 安装前必检：`sudo -n echo OK 2>&1`
- Windows 必检：`net session >nul 2>&1 && echo ADMIN || echo NOT_ADMIN`

---

## 7. 附录：命令速查表

### 7.1 节点诊断命令

**Windows 诊断**
```batch
rem 节点在线
echo Hello

rem 系统信息
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"

rem 磁盘
wmic logicaldisk get caption,freespace,size

rem 架构
echo %PROCESSOR_ARCHITECTURE%

rem PATH查看
echo %PATH:;=&echo.%

rem 已安装软件（注册表）
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall /s /f "Go" 2>nul
```

**Linux 诊断**
```bash
# 系统信息
uname -a
cat /etc/os-release

# 磁盘
df -h /

# 架构
uname -m

# 用户
whoami
id

# sudo 检查
sudo -n echo OK 2>&1

# PATH
echo $PATH | tr ':' '\n'

# 软件是否安装
dpkg -l | grep git
which git
```

### 7.2 ComputeHub API 命令速查

```python
# === 提交任务 ===
# POST /api/v1/tasks/submit
{
  "command": "your command",
  "timeout": 30,          # 超时秒数
  "priority": 10,          # 优先级
  "assigned_node": "node-id",  # 可选，指定节点
  "source_type": "direct"
}

# === 查询任务 ===
# GET /api/v1/tasks/detail?task_id=<id>

# === 列任务 ===
# GET /api/v1/tasks/list

# === 常用参数 ===
# GW          → http://<gateway>:8282
# poll_interval → 2-3s
# max_wait      → timeout + 10s
```

### 7.3 常用安装 URL（截至 2026-05）

| 软件 | 下载 URL |
|------|----------|
| Go 1.26.3 | `https://go.dev/dl/go1.26.3.windows-amd64.msi` |
| Python 3.11.6 | `https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe` |
| Python 3.12 | `https://www.python.org/ftp/python/3.12.x/python-3.12.x-amd64.exe` |
| Node.js LTS | `https://nodejs.org/dist/v20.x.x/node-v20.x.x-x64.msi` |
| Git | `https://github.com/git-for-windows/git/releases/download/v2.xx.x/Git-2.xx.x-64-bit.exe` |

> 下载前先通过 web_fetch 或 curl 获取最新版本号

### 7.4 Python 验证脚本模板

```python
"""Verify installation via ComputeHub Gateway API"""
import json, urllib.request, time

GW = "http://localhost:8282"

def submit(cmd, timeout, node=None):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct"}
    if node:
        body["assigned_node"] = node
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        timeout=15
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, sec):
    time.sleep(sec)
    resp = json.loads(urllib.request.urlopen(
        f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10
    ).read())
    return resp.get("data", {})

def verify(node, software, version_cmd):
    tid = submit(version_cmd, 10, node)
    d = wait(tid, 5)
    out = (d.get("stdout") or "").strip()
    exit_code = d.get("exit_code")
    if exit_code == 0 and out:
        print(f"✅ {software} installed: {out[:100]}")
    else:
        print(f"❌ {software} NOT found (exit={exit_code})")
        print(f"   stderr: {(d.get('stderr') or '')[:200]}")
```

---

## 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-05-18 | v1.2 | +Git/FFmpeg/Node.js 安装模板 +PowerShell -EncodedCommand 升级为 PATH 更新首选 +批量 PATH 合并技巧 +LTSC 兼容性说明 (基于 Windows-mobile-01 下午实战) |
| 2026-05-18 | v1.1 | +ComputeHub Gateway API 安装模式 +Linux 节点安装扩展 +Q6 权限不足 FAQ +API 命令速查 (基于 ECS Git 安装实战) |
| 2026-05-18 | v1.0 | 初版，基于 Go+Python 安装实战经验 |
