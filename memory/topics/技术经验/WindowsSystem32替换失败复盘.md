# 复盘：Windows System32 binary 替换失败事件

**事件ID**: INC-2026-0606-001
**发生**: 2026-06-06 02:00-02:50
**报告**: 2026-06-06 02:54
**涉及节点**: Windows-mobile (v1.3.16, C:\Windows\System32\computehub.exe)

---

## 📊 事件全景

```
02:00 ─── Windows-mobile online ✅, Worker 正常运行 ─── 空闲
  │
02:07 ─── TUI session 开始替换操作
  │        方法: 先下载 .ps1 脚本 → 再执行
  │        ① DownloadFile(url, '$env:TEMP\replace.ps1')
  │           ↓  cmd 把 $env:TEMP 展开为空
  │           → 实际路径 'C:eplace.ps1' ❌
  │        ② 执行 replace.ps1 → 找不到文件 → 卡住
  │
02:10 ─── 49s 超时 → SIGTERM → Worker 进程被杀 💀
  │
02:10-50 ─── Gateway 显示 "online" (缓存注册信息)
  │            5 个 task 全部 pending
  │            task-87a50d (EncodedCommand) = 正确代码但执行不了
  │
02:54 ─── 复盘完成 ─── 等待人工恢复
```

---

## 🔑 根因链（3层）

### 根因①：cmd/TUI 的 `$` 变量展开（触发因子）

```
TUI session → cmd管道 → $env:TEMP 被cmd解释为环境变量 → 展开为空
                                                              ↓
路径 C:\Users\xxx\AppData\Local\Temp\replace.ps1 → C:eplace.ps1
```

**关键点**: `$` 在 cmd 中表示环境变量引用。`$env:TEMP` 在 cmd 上下文中展开为空。
这导致 .ps1 脚本写到了错误路径，替换流程从第一步就歪了。

### 根因②：Task 超时杀死 Worker 进程（致命因子）

这是最严重的问题。**SIGTERM 应该只杀 task 子进程，不应该杀 Worker 主进程。**

```
task timeout 49s
    ↓
SIGTERM 发送给整个进程树
    ↓
Worker 主进程 (computehub.exe) 被杀死
    ↓
Gateway 收不到 heartbeat，但注册信息还在缓存
    ↓
所有后续 task 卡 pending
```

**这暴露了 Worker 进程隔离的 bug**：子进程超时不应波及父进程。

### 根因③：Gateway 无 zombie 节点检测（放大因子）

Worker 死后 40+ 分钟，Gateway 仍然显示 `online`（`active_tasks=5`）。
没有心跳超时自动标记 `offline` + 任务重排机制。

---

## 💡 三个层次的解决方案

### 🔴 P0：即刻恢复（手动）

需要有人在 Windows 机器上：
```cmd
cd C:\Windows\System32
computehub.exe worker --gw http://36.250.122.43:8282 --node-id Windows-mobile --interval 3 --concurrent 4 --heartbeat 10
```

### 🟡 P1：Worker 进程隔离修复（代码）

- **问题**: `execShell()` 的 maxWait 超时 → SIGTERM 杀死整个进程树
- **目标**: Subprocess kill 不应波及 Worker 主进程
- **办法**: 用 Job Object (Windows) / Process Group (Linux) 隔离 task 子进程

### 🟢 P2：Gateway zombie 节点检测（代码）

- heartbeat 连续 3 次未到 → 自动标记 offline
- 该节点的 pending task → 自动重排到其他节点或返回失败
- 从注册表移除 zombie 节点

### 🟢 P3：标准化 $ 变量处理

- **所有含 `$` 的 PowerShell 命令 → 强制 -EncodedCommand**
- TUI session 发送 PowerShell 命令时自动检测 `$` 并转码

---

## 🧪 这次做对了的事（要保留）

| 做对了 | 具体 |
|--------|------|
| ✅ EncodedCommand task (task-87a50d) | 代码完全正确，下载→验证大小→kill→copy→备份→exit 0 |
| ✅ 有后备替换路径 (`$alt`) | 除了 System32，还备了 `C:\computehub\computehub.exe` |
| ✅ 文件大小校验 | 下载后检查 ≥5MB，防损坏 |

## ❌ 做错了的事（要杜绝）

| 做错了 | 根因 | 以后 |
|--------|------|------|
| ❌ TUI 用 `$env:TEMP` 构造路径 | cmd 吃掉 `$` | 全部走 -EncodedCommand |
| ❌ 同时提交两种替换方案 | 自相矛盾 | 一次只走一条路径 |
| ❌ SIGTERM 杀死整个 Worker | 进程隔离缺失 | 只杀子进程不杀父进程 |
| ❌ 超时 49s 太短 | 下载 10MB+ 不够 | 设 ≥120s |

---

## 🔗 关联文档

- [WIN-REPL-001] Windows System32 binary 替换标准流程 ✅ 已更新至 v1.1
- 本文件: memory/topics/技术经验/WindowsSystem32替换失败复盘.md ✅

---

*报告完毕。核心教训：cmd + $ = 灾难，-EncodedCommand 是唯一安全路径。*
