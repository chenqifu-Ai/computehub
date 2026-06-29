# WIN-REPL-001：Windows System32 binary 替换标准流程

**版本**: v1.1 | **制定**: 2026-06-06 | **更新**: 2026-06-06 (复盘后增补) | **状态**: ✅ 生效

---

## 1. 适用范围

替换 Windows 节点上位于 `C:\Windows\System32` 下的 Worker binary（或其他关键系统目录 binary）。

## 2. 核心原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **永远不用 cmd 传 PowerShell 含 `$` 的命令** | cmd 把 `$var` 解释成环境变量，值为空 |
| 2 | **不用 certutil 下载大文件(>5MB)** | 不稳定，可能 hang 死进程 |
| 3 | **替换前先启动新进程** | kill Worker → 复制 → 再启动，防止断联 |
| 4 | **走 -EncodedCommand（推荐）或 .ps1 文件** | 绕开 cmd 解析陷阱 |
| 5 | **提交 task 后监控 Worker 恢复** | 替换后 Worker 重启需要时间 |
| 6 | **🚨 Task 超时只杀子进程，不杀 Worker** | SIGTERM 不应波及 Worker 主进程（进程隔离） |
| 7 | **🚨 不同时走两条替换路径** | 统一用单一方案，避免冲突 |

## 2b. 🚨 新增经验（2026-06-06 复盘增补）

### ⚡ 经验 #1：`$` 变量被 cmd 吃掉的精确机制

```
TUI session → cmd 管道 → cmd 解释 $var 为环境变量
                  ↓
          $env:TEMP 在 cmd 上下文中展开为空
                  ↓
          路径 'C:\Users\xxx\Temp\replace.ps1' → 'C:eplace.ps1'
```

**后果**: 文件写到了错误路径，替换流程从第一步就偏了，没有报错。

### ⚡ 经验 #2：Task 超时杀整个进程树 = 致命

```
task 超时 49s → SIGTERM → 杀死整个进程树
                  ↓
           Worker 主进程 computehub.exe 被杀 💀
                  ↓
           Gateway 还显示 "online"（缓存注册信息）
                  ↓
           所有后续 task 卡 pending，无法恢复
```

**后果**: Worker 死后，远程替换再也做不了了——因为没人接 task 了。
**解决办法**: Worker 的 task 执行器必须用进程组/Job Object 隔离。

### ⚡ 经验 #3：Gateway zombie 节点无检测

Worker 死后 40+ 分钟，Gateway 仍显示 `online`（`active_tasks=5`）。
需要：heartbeat 连续 3 次未达 → 自动标记 offline → pending task 重排

## 3. 方法一：PowerShell -EncodedCommand（推荐）

### 3.1 生成编码命令

```python
# 本地 Linux 终端执行
ps_code = '''
$url = "http://GATEWAY_IP:PORT/api/v1/files/WORKER_BINARY.exe"
$out = "C:\\Windows\\System32\\worker.exe.new"
$old = "C:\\Windows\\System32\\worker.exe"
Write-Host "[1] Downloading..."
(New-Object Net.WebClient).DownloadFile($url, $out)
if (-not (Test-Path $out)) { Write-Host "FAIL download"; exit 1 }
$sz = (Get-Item $out).Length; Write-Host "[2] Size: $sz"
if ($sz -lt 5MB) { Write-Host "FAIL too small"; Remove-Item $out -Force; exit 1 }
Write-Host "[3] Killing old..."
taskkill /f /im worker.exe 2>$null; Start-Sleep 2
Write-Host "[4] Copying..."
Copy-Item $out $old -Force; Remove-Item $out -Force
Write-Host "[DONE]"
exit 0
'''

import base64
utf16 = ps_code.encode('utf-16-le')
encoded = base64.b64encode(utf16).decode()
print(f'powershell -EncodedCommand {encoded}')
```

### 3.2 提交 task

```python
import json, urllib.request

task = {
    "node_id": "Windows-mobile",
    "command": f"powershell -EncodedCommand {encoded}",
    "timeout": 120,          # 含下载时间，≥120s
    "priority": 8,
    "max_retries": 3         # 自动重试
}
```

### 3.3 监控恢复

```bash
# 每 10s 检查节点是否恢复
while true; do
  curl -s http://GATEWAY:PORT/api/v1/nodes/list | grep -i windows
  sleep 10
done
```

## 4. 方法二：PS1 文件上传 + 执行

### 4.1 写 PS1 脚本

**⚠️ 必须用单引号字符串，不使用 `$` 变量**：

```powershell
# replace_worker.ps1
$url = "http://GATEWAY:PORT/api/v1/files/worker.exe"
$out = "C:\Windows\System32\worker.exe.new"
$old = "C:\Windows\System32\worker.exe"
$alt = "C:\worker\worker.exe"

Write-Host "[1] Downloading..."
(New-Object Net.WebClient).DownloadFile($url, $out)
if (-not (Test-Path $out)) { Write-Host "FAIL"; exit 1 }
$sz = (Get-Item $out).Length; Write-Host "[2] Size: $sz"
if ($sz -lt 5MB) { Write-Host "FAIL"; Remove-Item $out; exit 1 }

Write-Host "[3] Killing..."
taskkill /f /im worker.exe 2>$null
Start-Sleep 2

Write-Host "[4] Copying..."
Copy-Item $out $old -Force
Remove-Item $out -Force
if (Test-Path $alt) { Copy-Item $old $alt -Force }

Write-Host "[DONE]"
exit 0
```

### 4.2 上传到 Gallery

```bash
curl -s -X POST "http://GATEWAY:PORT/api/v1/gallery/upload" \
  -F "file=@replace_worker.ps1;filename=replace_worker.ps1"
```

### 4.3 分两步执行

因为 cmd 没有可靠的下载工具，需要分两步：

**Step A**: 通过 Gateway API 直接下载 PS1 到 Windows（用 curli 或 built-in file fetch）
**Step B**: 执行 PS1 脚本

## 5. 方法三：Worker 内置升级机制（最佳实践）

如果 Worker 支持 `--upgrade-exec` 或 `test-register` 模式，直接用：

### 原理

1. 新 binary 上传到 Gateway gallery
2. Worker 下载到 `%TEMP%\worker.exe.new`
3. 以 `--test-register` 参数 spawn 子进程
4. 子进程注册到 Gateway → 验证成功
5. 父进程备份旧 binary
6. 子进程复制到 System32 + 退出父进程
7. Worker 重新注册

**这需要 Worker 代码支持**，详见 `computehub` 的 `UpgradeEngine` 实现。

## 6. 验证清单

| # | 检查项 | 命令 |
|---|--------|------|
| 1 | System32 binary 版本 | `powershell -c "(Get-Item C:\\Windows\\System32\\worker.exe).VersionInfo"` |
| 2 | 文件大小 | `powershell -c "(Get-Item C:\\Windows\\System32\\worker.exe).Length"` |
| 3 | 节点心跳 | `curl -s http://GATEWAY:PORT/api/v1/nodes/list` |
| 4 | 功能测试 | `health` / `status` 端点 |

## 7. 🚨 禁忌清单

| ❌ 不要做 | 为什么 |
|----------|--------|
| ❌ `certutil -urlcache` 下载 >5MB | 可能 hang，Worker 进程被杀 |
| ❌ `cmd /c powershell $var` | cmd 吃掉 `$` 变量 |
| ❌ 不 spawn 新进程直接 kill Worker | 断联，后续 task 收不到 |
| ❌ 链式 `&&` 含 url 参数 | cmd 中的 `&` 截断 URL |
| ❌ `timeout < 60s` | 下载 10MB 可能超过 30s，timeout 不足直接失败 |
| ❌ **不同时走两条替换路径** | EncodedCommand task + TUI 手动替换冲突，Worker 死得更快 |
| ❌ **Task 超时不隔离进程** | SIGTERM 杀死整个进程树→Worker 陪葬→无法恢复 |

## 7b. ✅ 反复检查清单（每次替换前过一遍）

| # | 检查项 | 状态 |
|---|--------|:----:|
| 1 | 选定单一方案（EncodedCommand / PS1 / 内置升级），不走两条路 | ⬜ |
| 2 | 所有 `$` 变量被 `-EncodedCommand` 保护，不经过 cmd 解析 | ⬜ |
| 3 | `timeout` 设置 ≥120s（含 10MB 下载时间） | ⬜ |
| 4 | 提交 task 前确认 Worker 进程活着（health/status 端点） | ⬜ |
| 5 | 新 binary 已上传到 Gallery / deploy 目录 | ⬜ |
| 6 | 替换后会 `Start-Process` 重启 Worker（不是 kill 完事） | ⬜ |

## 8. 恢复步骤（替换失败时）

### 8.1 Worker 进程被杀（zombie 节点）

**症状**: Gateway 显示 `online` 但心跳收不到，task 全部 pending

```cmd
# Windows 终端手动重启
cd C:\Windows\System32
computehub.exe worker --gw http://GATEWAY:PORT --node-id NODE_ID --interval 3 --concurrent 4 --heartbeat 10
```

**如果忘记参数**:
```cmd
# 查注册信息
computehub.exe worker --help
# 或直接查看 Gateway 节点列表中的参数
```

### 8.2 Task 坏掉了但 Worker 活着

```
# 直接提交 EncodedCommand 替换 task，timeout=120s
# 先确认二进制文件路径
powershell -c "Get-Item C:\Windows\System32\worker.exe"
```

### 8.3 备份恢复（若有 .bak）

```cmd
copy /Y C:\Windows\System32\worker.exe.bak C:\Windows\System32\worker.exe
computehub.exe worker --gw http://GATEWAY:PORT --node-id NODE_ID ...
```

---

*文档版本: v1.1 | 最后更新: 2026-06-06 (2026-06-06 事件复盘增补) | 作者: 小智*