# OPC-WIN-STD-001: Worker 远程更新标准流程 v2.0

> 建立时间: 2026-05-28 | 最后更新: 2026-05-29
> 版本: v2.1
> 适用场景: 通过 OPC Gateway 远程更新 Worker 二进制（Windows/Linux）
>
> **核心教训**: 更新过程中 Worker 进程会被自己杀死，必须设计"自杀不掉链"的独立执行流程
>
> **适用对象**: 运维人员 / AI 智能体 / 自动更新子系统

---

## 目录

1. [架构总览](#1-架构总览)
2. [版本管理机制](#2-版本管理机制)
3. [核心原理](#3-核心原理)
4. [标准更新流程（Windows）](#4-标准更新流程windows)
5. [标准更新流程（Linux）](#5-标准更新流程linux)
6. [全自动更新机制（代码自更新）](#6-全自动更新机制代码自更新)
7. [远程推送部署（SSH 方式）](#7-远程推送部署ssh方式)
8. [回滚流程](#8-回滚流程)
9. [常见问题与深度排查](#9-常见问题与深度排查)
10. [附录](#10-附录)

---

## 1. 架构总览

### 更新链路全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                      开发/编译阶段                                      │
│  git tag v1.1.1                                                       │
│       ↓                                                                │
│  build_all.sh  →  ldflags 注入版本号  →  bin/{platform}/computehub     │
│       ↓                                                                │
│  sync-deploy.sh  →  deploy/{version}/{platform}/  +  deploy/{platform}/ │
│       ↓                                                                │
│  sync-deploy.sh Step 6  →  Gallery 上传（供 Worker 下载）               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      更新执行阶段（两条路径）                            │
│                                                                         │
│  路径 A: Worker 自动更新（无需人工介入）                                   │
│  Worker 每5分钟 checkUpgrade() → 发现新版本 → performUpgrade()          │
│                                                                         │
│  路径 B: 远程手动更新（通过 OPC push 命令）                                │
│  OPC submit → Windows: curl + schtasks / Linux: nohup                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 关键端点

| 端点 | 用途 | 路径 |
|------|------|------|
| **升级检查** | Worker 查询是否有新版本 | `GET /api/v1/upgrade/check?current_version=X&node_id=Y&platform=Z` |
| **Worker 下载** | Worker 自动更新专用，返回 deploy/ 下编译产物 | `GET /api/v1/download?file=computehub-linux-amd64` |
| **Worker 下载（新平台）** | 同上，支持 windows-amd64 等 | `GET /api/v1/download?file=computehub-windows-amd64.exe` |
| **文件下载（Gallery）** | Gallery 上传文件（人工下载/预览，与 Worker 更新无关） | `GET /api/v1/files/computehub-linux-amd64` |
| **画廊上传** | 部署脚本上传新文件 | `POST /api/v1/gallery/upload` (multipart) |
| **画廊删除** | 覆盖前删除旧文件 | `POST /api/v1/gallery/delete?name=xxx` |
| **版本设置** | 设置最新版本号 | `POST /api/v1/upgrade/config` (body: `{"version":"1.1.1"}`) |

### ⚠️ 两个下载端点关键差异（2026-05-29 验证修正）

> ⚠️ **重要**: 这两个端点下载的是**完全不同的文件**，不要混用！

```
/api/v1/download?file=computehub-linux-amd64
  → Worker 自动更新专用
  → 返回 deploy/linux-amd64/computehub（编译产物，~8.5MB）
  → upgradeBinaryName() 返回 computehub-worker-linux-amd64 或 computehub
  → ⚠️ 不要用 &platform= 参数，会返回 405
  → ✅ 直接用文件名: file=computehub-linux-amd64

/api/v1/files/computehub-linux-amd64
  → Gallery 上传文件（人工下载/预览）
  → 返回 gallery/computehub-linux-amd64（可能不同版本，~9.2MB）
  → 与 Worker 自动更新无关
```

| 特性 | /api/v1/download | /api/v1/files/ |
|------|-----------------|----------------|
| 用途 | Worker 自动更新 | Gallery 文件下载 |
| 文件来源 | deploy/linux-amd64/ | gallery/ |
| 内容 | 编译产物 | 人工上传文件 |
| MD5 | 不同 | 不同 |
| 推荐场景 | 代码自动更新 | 人工下载/预览 |

**Worker 代码路径**: `upgradeBinaryName()` 在 v1.1.0+ 返回 `computehub` 或 `computehub.exe`（不再用 `computehub-worker-*` 命名）。

---

## 2. 版本管理机制

### 2.1 版本号从哪来

```go
// src/version/version.go
var VERSION = "dev"  // 编译时用 ldflags 注入
var BUILD = "dev"
```

版本注入链路：

```
git tag v1.1.1
    ↓
git describe --tags --abbrev=0  →  "1.1.1"  （去掉了 v 前缀）
    ↓
build_all.sh: go build -ldflags="-X github.com/computehub/opc/src/version.VERSION=1.1.1"
    ↓
编译后的二进制里 VERSION = "1.1.1"
```

⚠️ **常见陷阱**: `deploy/version.txt` 和 VERSION 是两个不同的东西

| 东西 | 位置 | 用途 |
|------|------|------|
| `VERSION` 常量 | 编译进二进制 | Worker 启动时 `version.Short()` 读取 |
| `deploy/version.txt` | Gateway 磁盘文件 | Gateway `handleUpgradeCheck()` 返回给 Worker |

**这两个必须一致！** 如果不同：
- Worker `version.Short()` = "1.1.0"
- Gateway `version.txt` = "1.1.3"
- 自动更新会认为永远有新版本，无限循环

### 2.2 ⚡ v1.1.1 变 v1.1.0 的教训

```
原因: git tag 是 v1.1.1，但运行 binary 显示 v1.1.0
排查链路:
  1. build_all.sh 用 `git describe --tags --abbrev=0` 取版本号
  2. sync-deploy.sh 同样用 `git describe --tags`
  3. 两者必须基于**同一个 git tag**
  4. 如果 tag 打晚了（编译后才打），VERSION 还是旧值
  
解决方案:
  1. 先 git tag v1.1.1
  2. 再 git push --tags
  3. 最后编译
```

### 2.3 deploy/ 目录结构

```
deploy/                              ← 顶层（可含当前平台 binary 快捷方式）
├── computehub                       ← 当前平台的 symlink/copy
│
├── version.txt                      ← "1.1.1" (Gateway 读取此文件)
│
├── sha256sums-1.1.1.txt             ← 校验和
│
├── 1.1.1/                           ← 版本归档
│   ├── linux-amd64/computehub
│   ├── linux-arm64/computehub
│   ├── darwin-amd64/computehub
│   ├── darwin-arm64/computehub
│   └── windows-amd64/computehub.exe
│
├── linux-amd64/computehub           ← 平铺（供 download 端点使用）
├── linux-arm64/computehub
├── darwin-amd64/computehub
├── darwin-arm64/computehub
├── windows-amd64/computehub.exe
│
├── computehub-worker-linux-amd64    ← symlink → deploy/linux-amd64/computehub
├── computehub-worker-linux-arm64    ← symlink → deploy/linux-arm64/computehub
├── computehub-worker-win-amd64.exe  ← symlink → deploy/windows-amd64/computehub.exe
```

注意：`deploy/` 本身就是一个 `symlink -> /home/computehub/src/deploy/`（指向 OPC 项目外部的源码 deploy 目录）。

---

## 3. 核心原理

### 3.1 🚨 首要原则：Worker 会杀死自己

`taskkill /f /im computehub.exe` 或 `killall computehub` 会杀掉**所有同名进程**，包括正在执行更新命令的 Worker 本身。

```
❌ Worker 发命令 → taskkill → 全部被杀 → 后续命令中断
✅ Worker 发命令 → schtasks/at/anacron → 独立进程执行 →
   taskkill(独立进程不受影响) → move → 重启新 Worker
```

Windows 进程树关系：

```
Worker (PID=1000)                        ← OPC 发来更新命令
├── cmd.exe (PID=1001)                   ← 执行 OPC task 的子进程
│   └── schtasks.exe (PID=1002)         ← 创建计划任务
│       └── [svchost]                    ← Windows Task Scheduler 接管
│           └── cmd.exe (PID=2000)      ← 独立进程！Worker 挂了也不影响
│               └── taskkill (PID=2001)  ← 杀 Worker(PID=1000) 但不影响自己
│               └── move (PID=2002)      ← 替换 binary
│               └── computehub.exe ...    ← 启动新 Worker
```

### 3.2 更新三部曲

```
下载新版本 → 停旧换新 → 启动新版本
```

**致命坑**: 停旧这一步会杀掉 Worker，所以下载和替换必须在独立执行上下文中完成。

### 3.3 安全边界：Windows vs Linux

| 特性 | Windows | Linux |
|------|---------|-------|
| 独立进程机制 | `schtasks` 计划任务 | `nohup` + `&` |
| 被杀风险 | `taskkill /f /im` 杀全部同名进程 | `pkill` 不杀 parent shell |
| 文件替换 | `move /y`（不能覆盖正在运行的 exe） | `mv; chmod +x` |
| 启动方式 | `start "" "exe" args` | `nohup exe &` |
| 备份机制 | 自动备份为 `exe.bak.VERSION` | 自动备份为 `exe.bak.VERSION` |

---

## 4. 标准更新流程（Windows）

### Step 1：下载新版本

通过 OPC 推送 `curl` 命令：

```bash
# ✅ 标准写法
curl -sL http://<GATEWAY>:8282/api/v1/files/computehub-windows-amd64.exe -o C:\computehub-v1.1.1.exe

# ⚠️ 要点
# - 用 /api/v1/files/ 端点（固定文件名，不追加时间戳）
# - 文件名加版本号后缀（避免覆盖运行中的文件）
# - timeout 设 120s（10MB+ 文件可能较慢）
# - Windows curl 可能以非零退出码结束但文件已成功下载 → 用 dir 验证
```

**验证下载**（必须！因为 Windows curl 退出码不可靠）：

```bash
dir C:\computehub-v1.1.1.exe
```

**⚠️ Windows curl 坑**: 即使在 CMD 中 curl 显示错误（exit code != 0），文件可能已经完整下载。**必须用 `dir` 检查文件存在和大小**，不能只依赖 exit code。

### Step 2：编写更新批处理脚本

#### 方法 A：PowerShell -EncodedCommand 写入（手动推送推荐）

使用 PowerShell **Base64 编码命令**写入 bat 文件，避免 CMD 引号嵌套地狱：

```python
import base64

batch_content = """@echo off
chcp 65001 >nul
echo [1/3] 停旧进程...
taskkill /f /im computehub.exe 2>nul
timeout /t 2 /nobreak >nul
echo [2/3] 替换新版...
move /y C:\\computehub-v1.1.1.exe C:\\computehub.exe
echo [3/3] 启动新版 Worker...
start /B C:\\computehub.exe worker --gateway http://<GATEWAY>:8282 --node-id "<NODE_NAME>"
echo OK!
"""

# 三层编码：Python → base64(bat) → PowerShell -EncodedCommand → base64(PS cmd, UTF-16LE)
b64_batch = base64.b64encode(batch_content.encode()).decode()
ps_cmd = f"$c=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64_batch}'));Set-Content C:\\update_worker.bat -Value $c -Encoding ASCII"
# 最终 OPC 提交的 command
encoded = base64.b64encode(ps_cmd.encode('utf-16le')).decode()
final_cmd = f"powershell -EncodedCommand {encoded}"
```

**编码链路图解**：
```
原始 bat 脚本 (UTF-8)
    → base64 编码
    → 嵌入 PowerShell 命令: [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('...'))
    → 将整个 PowerShell 命令再 base64 (UTF-16LE)
    → 最终: powershell -EncodedCommand <最终编码>
```

#### 方法 B：代码自动生成（auto_upgrade.go 做法）

Worker 自身的自动更新代码直接在当前目录写 `upgrade.bat`：

```bash
# auto_upgrade.go 生成的 bat 内容
@echo off
chcp 65001 >nul
echo ========================================
echo ComputeHub Worker 自动升级
echo ========================================

:wait
tasklist /fi "IMAGENAME eq computehub.exe" 2>nul | find /i "computehub.exe" >nul
if errorlevel 1 goto do_upgrade
echo [1/4] 等待旧 Worker 退出...
ping 127.0.0.1 -n 2 >nul
goto wait

:do_upgrade
echo [2/4] 替换二进制...
copy /Y ".\computehub.exe.upgrade" "C:\path\to\computehub.exe" >nul
echo [3/4] 启动新版 Worker...
start "" "C:\path\to\computehub.exe" worker --gateway http://<GW>:8282 --node-id "windows-mobile"
echo [4/4] 清理升级脚本...
del "%~f0"
echo ✅ 升级完成!
```

区别：方法 B 会先**等待**旧 Worker 主动退出，再用 `copy` 替换。方法 A 直接 `taskkill` + `move`。方法 B 更安全。

### Step 3：用 schtasks 独立调度执行（关键——唯一正确的方式）

**🚫 绝对禁止的做法**：
```bash
# ❌ 错误！taskkill 会杀子进程，start /B 仍在 Worker 进程树中
start /B C:\update_worker.bat
```

**✅ 唯一正确的做法——schtasks 独立调度**：

```bash
# 三条命令必须一次性发送（用 & 连接，而不是 &&）
# 因为 taskkill 可能在第一条之后执行，&& 可能断链
schtasks /create /sc once /tn "UpdateWorker" /tr "cmd /c C:\update_worker.bat" /st 00:00 /f & schtasks /run /tn "UpdateWorker" & schtasks /delete /tn "UpdateWorker" /f
```

**为什么必须用 `&` 而不是 `&&`**：

```
✅ & 链（推荐）:
  schtasks /create ... & schtasks /run ... & schtasks /delete ...
  即使 /create 返回非零（task 已存在）也不中断

❌ && 链（不推荐）:
  schtasks /create ... && schtasks /run ... && schtasks /delete ...
  如果 /create 失败（比如旧 task 没删干净），整条链断掉
```

### Step 4：验证

```bash
# 检查版本
C:\computehub.exe version
# 预期: ComputeHub v1.1.1

# 检查 Gallery 上文件状态
curl http://<GATEWAY>:8282/api/v1/files/computehub-windows-amd64.exe -I
```

---

## 5. 标准更新流程（Linux）

Linux 下相对简单，因为：
- `pkill` 不会杀 bash 子进程
- 可以用 `nohup` + `&` 做完全后台进程

### 方法 A：一次性脚本通过 OPC 推送

```bash
# 通过 OPC 一次性提交（用 nohup 包裹整个命令链）
nohup bash -c 'pkill -f "computehub.*worker"; sleep 2; mv /tmp/computehub-new /home/computehub/computehub; chmod +x /home/computehub/computehub; nohup /home/computehub/computehub worker --gw http://localhost:8282 --node-id ecs-p2ph > /tmp/worker.log 2>&1 &' > /dev/null 2>&1 &
```

⚠️ **关键细节**: 最外层的 `nohup ... &` 必须在 OPC 命令中。如果不加，Worker 被杀后 OPC task 还没返回，可能被 gateway 标记为超时。

### 方法 B：通过 sync-deploy.sh push（SSH 推送）

参见第 7 节。

---

## 6. 全自动更新机制（代码自更新）

### 6.1 架构

Worker 启动后会在 goroutine 中运行 `upgradeLoop()`：

```go
// workercmd/auto_upgrade.go
func (s *WorkerState) upgradeLoop() {
    time.Sleep(10 * time.Second)  // 延迟启动，让注册完成
    for {
        resp, err := s.checkUpgrade()   // GET /api/v1/upgrade/check
        if resp.UpdateAvailable {
            s.performUpgrade(resp)      // 下载 + 替换 + 重启
            // 成功后 os.Exit(0)，不会到此
        }
        time.Sleep(5 * time.Minute)     // 每5分钟检查
    }
}
```

### 6.2 自更新流程（Unix 路径）

```
1. checkUpgrade(): GET /api/v1/upgrade/check?current_version=1.0.1&node_id=xxx&platform=linux/amd64
2. Gateway: 比较 deploy/version.txt vs current_version，返回 UpdateAvailable=true
3. Worker: 下载新 binary 到 .computehub-worker-linux-amd64.upgrade (临时文件)
4. Worker: os.Rename(currentExe, currentExe.bak.1.0.1)  ← 备份旧版
5. Worker: os.Rename(tmpFile, currentExe)                ← 替换
6. Worker: chmod +x
7. Worker: os.StartProcess(currentExe, args...)          ← 启动新版
8. Worker: os.Exit(0)
```

### 6.3 自更新流程（Windows 路径）

```
1. checkUpgrade(): 同上
2. Gateway: 返回 UpdateAvailable=true
3. Worker: 下载到 .computehub-worker-win-amd64.exe.upgrade
4. Worker: 解析实际 exe 路径（处理 symlink 情况）
5. Worker: 写 upgrade.bat（含 wait→replace→start 逻辑）
6. Worker: schtasks /create → /run → /delete（一次完成）
7. Worker: 取消注册 → os.Exit(0)  ← 主动退出
8. bat (独立进程): tasklist 等待 Worker 退出 → copy 新版 → start 启动
```

### 6.4 自更新 vs 手动更新对比

| 特性 | 自动更新（代码） | 手动更新（OPC push） |
|------|-----------------|---------------------|
| 触发方式 | 每5分钟自动检查 | 运维人员/智能体主动调用 |
| 下载超时 | 120s (代码硬编码) | 建议设 120s |
| 文件存放 | `.exe.upgrade` 临时文件 | `C:\computehub-v1.1.1.exe` |
| bat 写入 | `os.WriteFile` 直接写 | PowerShell -EncodedCommand |
| 调度方式 | schtasks（代码实现） | schtasks（手动写） |
| 重启 | `os.Exit(0)` 后 bat 接管 | bat 内 start |
| 可靠性 | 已稳定运行 | 已验证通过 |

---

## 7. 远程推送部署（SSH 方式）

`sync-deploy.sh push` 实现了一条龙远程部署：检测架构 → SCP 传输 → 安装到 PATH → 停旧进程 → 启动新版本 → 验证 → Gallery 上传。

### 7.1 基本用法

```bash
# 仅推送，不启停
bash scripts/sync-deploy.sh push <host>

# 推送 + 停旧 + 启动 gateway + worker（完整重启）
bash scripts/sync-deploy.sh push 36.250.122.43 --action restart-all

# 仅推送并启动 worker
bash scripts/sync-deploy.sh push 36.250.122.43 --action worker --gateway http://36.250.122.43:8282

# 带密码
bash scripts/sync-deploy.sh push 192.168.2.140 '密码' chenqifu

# 指定 SSH 密钥
bash scripts/sync-deploy.sh push 192.168.2.140 --key ~/.ssh/my_key --action worker --gateway http://10.0.0.1:8282
```

### 7.2 执行流程详解

```
1. SSH 连接远程主机
2. 检测远程架构 (uname -m)
3. 找对应平台的编译产物
4. SCP 传输 binary → ~/computehub-v{VERSION}
5. 验证文件大小（本地 vs 远程，防传输损坏）
6. 安装到 PATH (/usr/local/bin/computehub)
7. 验证版本 (computehub version)
8. 停旧 + 启动新 (原子化 SSH 命令)
9. Gallery 上传（供其他 Worker 下载）
```

### 7.3 远程启动细节

`sync-deploy.sh` 的远程启动命令是**原子化**的（一条 SSH 命令完成所有操作）：

```bash
pkill -f 'computehub gateway' 2>/dev/null || true
pkill -f 'computehub worker'  2>/dev/null || true
sleep 1
NODE_ID=$(hostname)-worker
nohup ~/computehub gateway --port 8282 > /tmp/gateway.log 2>&1 &
sleep 1
nohup ~/computehub worker --gw http://${REMOTE_GW}:8282 --node-id ${NODE_ID} \
  --interval 3 --concurrent 8 > /tmp/worker.log 2>&1 &
```

**注意**: 远程 push 的 `pkill` 走的是 SSH 通道，被杀的进程是远程机器的，不是本地 Worker，所以不存在"自杀"问题。

---

## 8. 回滚流程

### 8.1 Windows 回滚

```powershell
# 如果有旧的 computehub.exe，备份在 C:\
# 检查是否有备份文件
dir C:\computehub-v1.0.1.exe

# 手动替换回旧版
taskkill /f /im computehub.exe
move /y C:\computehub-v1.0.1.exe C:\computehub.exe
start /B C:\computehub.exe worker --gateway http://<GW>:8282 --node-id "windows-mobile"
```

### 8.2 Linux 回滚

```bash
# 检查备份
ls -la /home/computehub/computehub.bak.*

# 替换回旧版
pkill -f "computehub.*worker" 2>/dev/null
mv /home/computehub/computehub.bak.1.0.1 /home/computehub/computehub
chmod +x /home/computehub/computehub
nohup /home/computehub/computehub worker --gw http://localhost:8282 --node-id ecs-p2ph > /tmp/worker.log 2>&1 &
```

### 8.3 Gallery 版本管理

Gallery 中的文件是按名称存取的（无版本区分）。如果需要回滚：
1. 从 `deploy/` 目录的历史版本目录（如 `deploy/1.0.1/`）找到旧版
2. 重新上传到 Gallery（覆盖同名文件）
3. 修改 `deploy/version.txt` 为旧版本号
4. 手动执行回滚

---

## 9. 常见问题与深度排查

### 🔴 问题 1：下载超时 / 下载失败

**现象**: `context deadline exceeded (Client.Timeout)` 或 Windows curl 报错

**检查清单**：
- [ ] Worker IP 是否被 fail2ban 封了？（`sudo fail2ban-client status sshd-aggressive`）
- [ ] ufw 规则是否拦了来源 IP？（`sudo ufw status`）
- [ ] 文件是否已在 Gallery 中？（`ls -la /home/computehub/gallery/`）
- [ ] deploy 目录是否有对应平台的 worker 文件？
- [ ] 磁盘空间是否充足？（Windows 上尤其 C 盘）
- [ ] timeout 是否设得够大（建议 ≥ 120s 对 10MB 文件）
- [ ] Windows curl 是否已安装？（`where curl`）

**Windows curl 特有坑**：
```
现象: curl 显示错误但文件已下载
原因: Windows 的 curl.exe 在某些情况下返回 exit code != 0
      即使文件已成功写入磁盘
解决: 不要只看命令退出码，用 dir 验证文件存在
```

**解决方案**：
```bash
# 解封误封的 IP
sudo fail2ban-client set sshd-aggressive unbanip <IP>
# 加白名单（永久）
sudo fail2ban-client set sshd-aggressive addignoreip <IP>

# 检查 Gallery 文件状态
curl -sI http://localhost:8282/api/v1/files/computehub-windows-amd64.exe

# 检查 deploy 目录
ls -la /home/computehub/OPC/deploy/windows-amd64/
cat /home/computehub/OPC/deploy/version.txt
```

### 🔴 问题 2：Worker 自杀导致替换失败

**现象**: 文件下载完成但版本号没变，旧文件还在

**原因**: `taskkill /f /im computehub.exe` 把 Worker 自己杀了，`move` 没执行

**检查**：
```bash
# Windows：看临时文件还在不在
dir C:\computehub-v1.1.1.exe  # 如果还在说明没替换
dir C:\computehub.exe         # 看看当前版本的修改时间
```

**根本解决方案**: **必须用 `schtasks` 独立调度**（Windows）或 `nohup`（Linux）。

**验证 schtasks 是否执行成功**：
```bash
# 查看 Windows 计划任务历史
schtasks /query /tn "ComputeHubUpgrade" /v /fo LIST 2>nul

# 如果任务已删除（正常情况），说明已执行
# 如果任务还在，说明 create 后忘了 run 和 delete
```

### 🔴 问题 3：节点名被截断

**现象**: `Windows-mobile-01` 注册成 `Windows-mobile-`

**原因**: Go 代码中获取主机名时，Windows API `gethostname()` 受 NetBIOS 限制只返回前 15 字符。但 `--node-id` 显式参数不受此限制。

```go
// 如果没用 --node-id，Worker 会调用 os.Hostname()
// Windows 上 os.Hostname() → GetComputerNameEx
// GetComputerNameEx(ComputerNameDnsHostname) 被截断到 15 字符（NetBIOS 限制）
hostname, _ := os.Hostname()        // "Windows-mobile-0" (15 chars)
nodeID = hostname                   // → 被截断
```

**解决方案**:
```bash
# ✅ 正确：显式用 --node-id，≤15 字符
--node-id "windows-mobile"      # 14 字符，安全

# ✅ 也可以超过 15 字符（Go 层面不限制，只是默认取主机名才受限）
--node-id "Windows-mobile-01"   # 19 字符，Go 代码完全支持

# ❌ 错误：依赖默认主机名
# 如果 Windows 主机名 > 15 字符，自动截断
```

### 🔴 问题 4：active_tasks=-1

**现象**: Worker 状态显示 `active_tasks=-1`

**原因**: `taskkill` 或 `pkill` 打断了正在执行的任务，`activeTasks` 计数器未归零（任务开始 +1，完成 -1，被 kill 少了 -1 那步）

**影响**: 轻微，不影响 Worker 功能（任务仍可正常执行），但调度器可能因为 `active_tasks < 0` 跳过某些调度逻辑

**解决方案**: 重启 Worker 即可重置计数器为 0

### 🔴 问题 5：版本号不一致（deploy/version.txt vs 实际编译版本）

**现象**: `build_all.sh` 显示 v1.1.1，但 `computehub version` 显示 v1.0.1

**根因分析**：
```
build_all.sh 的版本来源：
  VERSION=$(git describe --tags --abbrev=0 | sed 's/^v//')
  
如果 git tag 和编译不在同一个操作中完成：
  1. 编译时 git tag = v1.0.1  → VERSION = "1.0.1"
  2. 后续打了 v1.1.1 tag
  3. 手动改了 version.txt = "1.1.1"
  4. Worker 启动显示 v1.0.1，但 Gateway 说最新版是 1.1.1
  5. Worker 永远以为自己落后版本 → 每次检查都触发更新 → 覆盖旧版

根本解决：版本号只能从 git tag 来，不要手动改 version.txt
sync-deploy.sh 会自动从 git tag 同步 version.txt
```

### 🔴 问题 6：Windows curl exit code 非零的真相

```bash
# 现象：curl 报错但文件下载成功
curl -sL http://<GW>:8282/api/v1/files/computehub-windows-amd64.exe -o C:\computehub.exe
# 输出类似: curl: (56) Recv failure: Connection was reset
# 但 dir C:\computehub.exe 显示文件大小正常

# 原因：curl 库在处理 HTTP response body 时的特定 bug
# HTTP 层面文件已完整传输并写入磁盘
# curl 的 exit code 检查的是 SSL/TLS 层关闭握手，不影响 payload
```

**验证方法**: 不依赖 exit code，用文件大小验证：

```bash
dir C:\computehub.exe
# 确认文件大小 > 9MB 即为成功
```

### 🔴 问题 7：fail2ban 误封 Worker IP

**现象**: ARM Worker (112.48.77.200) 无法下载更新

**排查步骤**：
```bash
# 1. 检查 fail2ban 状态
sudo fail2ban-client status sshd-aggressive

# 2. 检查是否被封
sudo fail2ban-client status sshd-aggressive | grep "Banned IP list"

# 3. 解封
sudo fail2ban-client set sshd-aggressive unbanip 112.48.77.200

# 4. 加入白名单（避免再次被封）
sudo fail2ban-client set sshd-aggressive addignoreip 112.48.77.200

# 同时检查 ufw
sudo ufw status
```

---

## 10. 附录

### 10.1 常用检查命令速查

```bash
# === Gateway 状态 ===
curl http://localhost:8282/api/v1/nodes/list | python3 -m json.tool
curl http://localhost:8282/api/health

# === 节点列表 ===
curl "http://localhost:8282/api/v1/nodes/list?alive=true"

# === 任务查询 ===
curl "http://localhost:8282/api/v1/tasks/list?node_id=<NODE>&limit=5"
curl "http://localhost:8282/api/v1/tasks/detail?task_id=<TASK_ID>&node_id=<NODE>"

# === 提交任务 ===
curl -X POST http://localhost:8282/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{"command":"ver","node_id":"windows-mobile","timeout":30}'

# === 升级检查（模拟 Worker） ===
curl "http://localhost:8282/api/v1/upgrade/check?current_version=1.0.1&node_id=test&platform=linux/amd64"

# === 设置最新版本号 ===
curl -X POST http://localhost:8282/api/v1/upgrade/config \
  -H "Content-Type: application/json" \
  -d '{"version":"1.1.1"}'

# === 下载验证 ===
curl -sI http://localhost:8282/api/v1/download?file=computehub-windows-amd64.exe

# === Gallery 文件列表 ===
curl http://localhost:8282/api/v1/gallery/list

# === fail2ban 管理 ===
sudo fail2ban-client status sshd-aggressive
sudo fail2ban-client set sshd-aggressive unbanip <IP>
sudo fail2ban-client set sshd-aggressive addignoreip <IP>

# === 本地 deploy 目录验证 ===
cat /home/computehub/OPC/deploy/version.txt
ls -la /home/computehub/OPC/deploy/
find /home/computehub/OPC/deploy -name "computehub*" | xargs ls -lh

# === 节点注册信息 ===
curl "http://localhost:8282/api/v1/nodes/list" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for n in data.get('data', []):
    tasks = n.get('active_tasks', '?')
    print(f\"{n.get('node_id','?'):25s} v{n.get('version','?'):8s} tasks={tasks}\")
"
```

### 10.2 Windows 标准更新模板（Python）

```python
#!/usr/bin/env python3
"""
OPC Worker 远程更新脚本
用法: python3 update_worker.py <gateway_url> <node_id> <new_version>
"""
import sys, json, base64, time, urllib.request, urllib.error

GATEWAY = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8282"
NODE = sys.argv[2] if len(sys.argv) > 2 else "windows-mobile"
NEW_VERSION = sys.argv[3] if len(sys.argv) > 3 else "1.1.1"

def submit_task(cmd, node, timeout=120):
    data = json.dumps({"command": cmd, "node_id": node, "timeout": timeout}).encode()
    req = urllib.request.Request(f"{GATEWAY}/api/v1/tasks/submit", data=data,
                                 headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def wait_task(task_id, node, poll=3, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        resp = urllib.request.urlopen(
            f"{GATEWAY}/api/v1/tasks/detail?task_id={task_id}&node_id={node}")
        data = json.loads(resp.read())
        t = data.get("data", {})
        status = t.get("status", t.get("state", "unknown"))
        if status in ("completed", "success"):
            print(f"  ✅ Task {task_id}: {t.get('result', {}).get('stdout', '')[:200]}")
            return True
        if status in ("failed", "error"):
            print(f"  ❌ Task {task_id} failed: {t.get('result', {}).get('stderr', '')[:200]}")
            return False
        print(f"  ⏳ Task {task_id}: {status}...")
        time.sleep(poll)
    print(f"  ⚠️  Task {task_id} timeout after {timeout}s")
    return False

def update_windows():
    print(f"🚀 更新 {NODE} 到 v{NEW_VERSION}")

    # Step 1: 下载
    print(f"\n[1/4] 下载新版本...")
    resp = submit_task(
        f"curl -sL {GATEWAY}/api/v1/files/computehub-windows-amd64.exe "
        f"-o C:\\computehub-v{NEW_VERSION}.exe",
        NODE, timeout=120)
    if not wait_task(resp['data']['task_id'], NODE, timeout=130):
        print("  ⚠️  下载状态不确定，继续检查文件...")

    # Step 2: 验证下载
    print(f"\n[2/4] 验证下载...")
    resp = submit_task(f"dir C:\\computehub-v{NEW_VERSION}.exe", NODE)
    wait_task(resp['data']['task_id'], NODE)

    # Step 3: 写 bat 脚本（三层 base64 编码）
    print(f"\n[3/4] 写入更新脚本...")
    batch = f"""@echo off
echo [1/3] Stop old...
taskkill /f /im computehub.exe 2>nul
timeout /t 2 /nobreak >nul
echo [2/3] Replace...
move /y C:\\computehub-v{NEW_VERSION}.exe C:\\computehub.exe
echo [3/3] Start new...
start /B C:\\computehub.exe worker --gateway {GATEWAY} --node-id "{NODE}"
echo Done!
"""
    b64_batch = base64.b64encode(batch.encode()).decode()
    ps = f"$c=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64_batch}'));Set-Content C:\\update.bat -Value $c -Encoding ASCII"
    b64_ps = base64.b64encode(ps.encode('utf-16le')).decode()
    submit_task(f"powershell -EncodedCommand {b64_ps}", NODE, timeout=30)

    # Step 4: schtasks 独立调度执行
    print(f"\n[4/4] 调度执行（schtasks 独立进程）...")
    cmd = ('schtasks /create /sc once /tn Upd /tr "cmd /c C:\\update.bat" /st 00:00 /f'
           ' & schtasks /run /tn Upd'
           ' & schtasks /delete /tn Upd /f')
    resp = submit_task(cmd, NODE, timeout=30)
    wait_task(resp['data']['task_id'], NODE)

    print(f"\n✅ 更新完成！等待 Worker 重连...")

if __name__ == "__main__":
    update_windows()
```

### 10.3 自动更新代码关键位置

| 文件 | 关键函数 | 用途 |
|------|----------|------|
| `src/workercmd/auto_upgrade.go` | `checkUpgrade()` | 检查新版本 |
| `src/workercmd/auto_upgrade.go` | `performUpgrade()` | 执行更新（分发 Unix/Windows） |
| `src/workercmd/auto_upgrade.go` | `performWindowsUpgrade()` | Windows 专用：写 bat + schtasks |
| `src/workercmd/auto_upgrade.go` | `restartWorker()` | Unix 专用：rename + StartProcess |
| `src/workercmd/auto_upgrade.go` | `upgradeLoop()` | 每5分钟的检查循环 |
| `src/gateway/gateway_upgrade.go` | `handleUpgradeCheck()` | Gateway 端版本对比响应 |
| `src/gateway/gateway_upgrade.go` | `handleUpgradeConfig()` | 设置 version.txt |
| `src/gateway/gateway_upgrade.go` | `upgradeBinaryName()` | 平台→文件名映射 |
| `src/version/version.go` | `Short()` | 返回当前版本号 |

### 10.4 文件命名规范

| 平台 | 文件名（Gallery） | 文件名（自动更新 tmp） |
|------|------------------|----------------------|
| Linux amd64 | `computehub-linux-amd64` | `.computehub-worker-linux-amd64.upgrade` |
| Linux arm64 | `computehub-linux-arm64` | `.computehub-worker-linux-arm64.upgrade` |
| Windows amd64 | `computehub-windows-amd64.exe` | `.computehub-worker-win-amd64.exe.upgrade` |
| macOS amd64 | (未在自动更新列表中) | - |
| macOS arm64 | (未在自动更新列表中) | - |

### 10.5 `&` vs `&&` 在 Windows CMD 中的区别

```
CMD 操作符:
  cmd1 && cmd2   → cmd1 成功（exit 0）才执行 cmd2
  cmd1 & cmd2    → 无论 cmd1 成功与否都执行 cmd2
  cmd1 || cmd2   → cmd1 失败（exit ≠0）才执行 cmd2

在 schtasks 场景中：
  ✅ schtasks /create ... & schtasks /run ... & schtasks /delete ...
     最安全：每个命令独立执行，互不影响
     
  ❌ schtasks /create ... && schtasks /run ... && schtasks /delete ...
     有风险：/create 可能返回非零（task 已存在），后续全断

  ❌ schtasks /create ... & schtasks /run ... && schtasks /delete ...
     混合风格：容易搞混，不要用
```

### 10.6 Windows PID 命名建议

| 节点名 | 长度 | 状态 | 说明 |
|--------|------|------|------|
| `windows-mobile` | 14 | ✅ 推荐 | 刚好不超限 |
| `windows-dev-01` | 14 | ✅ 推荐 | 开发机 |
| `win-server-01` | 13 | ✅ 推荐 | 服务器 |
| `Windows-mobile-01` | 19 | ⚠️ 可用但要显式指定 | Go 支持，主机名不会截断 |
| (默认主机名 >15) | - | ❌ 不要依赖 | 会被 NetBIOS 截断 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.1 | 2026-05-29 | **验证修正**: 下载端点差异（download vs files 是不同的文件！）; /api/v1/download 去掉 &platform= 参数（405 修复）; /api/v1/health → /api/health; 补充 deploy 目录结构说明 |
| v2.0 | 2026-05-29 | **全面升级**: 新增自动更新机制详解、版本注入原理、sync-deploy.sh 远程推送、回滚流程、两个下载端点差异、Win curl exit code 陷阱、PID 命名规范、代码自动更新的完整流程图 |
| v1.0 | 2026-05-28 | 初始版本，基于 Windows Worker v1.1.1 升级实战经验 |
