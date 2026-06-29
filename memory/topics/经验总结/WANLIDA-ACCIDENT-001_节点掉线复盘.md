# 🚨 WANLIDA-ACCIDENT-001: wanlida-opc01 节点掉线复盘

**日期**: 2026-06-10 17:13-18:06  
**节点**: wanlida-opc01 (Windows, admin 账号, 192.168.2.134)  
**操作者**: 端智  
**严重程度**: 🔴 高 — 节点离线需人工恢复

---

## 📋 时间线

| 时间 | 事件 |
|------|------|
| 17:13 | 开始装 Node.js v22.14.0 (ComputeHub Worker 注册任务) |
| 17:17 | n22.zip 解压到 C:\nodejs ✅ |
| 17:18 | npm 从 registry.npmjs.org 下包失败，cmd 用完整路径含参数错误 |
| 17:18-17:22 | 多次尝试 PowerShell 调 npm，registry.npmjs.org 极慢，卡 5 分钟无输出 |
| 17:22 | ❌ **Stop-Process -Name node -Force** — 所有 node.exe 进程被强杀 |
| 17:26 | 切换 npmmirror 镜像重新 npm install，又卡 7 分钟 |
| 17:30-17:33 | 多次 Stop-Process -Id xxx -Force 强杀残留 node 进程 |
| 17:34 | npm install --ignore-scripts 成功（579 packages, 18s）✅ |
| 17:37 | 开新线程测 npm bin -g，响应变慢（5s→30s+）⚠️ 第1个报警 |
| ~17:50 | openclaw.mjs --help 卡 2 分钟 |
| ~18:00 | **节点彻底失联** — 所有新任务报 "node is not online" |
| 18:06 | windows-mobile 节点 ping 192.168.2.134 不通 |

## 🔍 根因分析

### 直接原因
`Stop-Process -Name node -Force` 的连带影响：
1. npm install 的 preinstall script 正在写入 node_modules 时被杀，目录不一致
2. Worker 通过 PowerShell 执行任务，内部杀 node 时 PowerShell 退出码/管道句柄出问题

### 根本原因
**PowerShell over Task 的固有脆弱性**：
```
Worker (Go binary)
  └─ spawn cmd.exe / PowerShell
       └─ Stop-Process -Name node -Force  ← 杀子进程，影响 Worker
```
- 每次 PS 输出混在 CLIXML 里，Worker 解析可能卡住
- 大量（~12KB）base64 命令体嵌套 PS 脚本，出问题后无处排查

### 间接原因
- Worker crash 后没有自动重启机制（非 Windows Service）
- 无法 SSH 到 192.168.2.134
- Worker 启动方式未知（手动/服务/计划任务）

## 💥 损失
- ❌ `C:\Users\admin\.openclaw\openclaw.json` 未写入
- ❌ OpenClaw CLI 首次启动未验证
- ❌ 节点离线，需人工到机器前重启 Worker

## 🧠 教训（WANLIDA-ACCIDENT-001 标准预防流程）

### 未来操作该节点时必须遵守

```
┌─────────────────────────────────────────────────┐
│ WANLIDA-ACCIDENT-001 预防检查清单                │
├─────────────────────────────────────────────────┤
│ □ 1. 操作前先确认 Worker 进程保护机制            │
│ □ 2. 操作前先做心跳检查（任务 echo ALIVE）      │
│ □ 3. 绝对禁止 Stop-Process / taskkill            │
│ □ 4. 长任务用 schtasks 后台启动，不 inline 执行  │
│ □ 5. 文件传输走 ECS 中转 → certutil -urlcache    │
│ □ 6. >60s 无输出的任务中断→换策略，不杀进程      │
│ □ 7. 复杂操作写 .py/.ps1 文件传到节点再执行       │
└─────────────────────────────────────────────────┘
```

| # | 教训 | 改进方案 |
|---|------|----------|
| 1 | 不要在 Worker 任务里杀进程 | 远程管理进程用 schtasks 或 wmic，禁止 Stop-Process |
| 2 | PowerShell 做长时间任务风险大 | 短命令用 PS，长任务（>30s）用 cmd 直跑或 schtasks 后台 |
| 3 | 配置传输不该走 base64 内嵌 | scp 到 ECS → certutil -urlcache 从 ECS 下载 |
| 4 | Worker 无心跳自愈 | 关键节点注册 Windows Service 自动重启 |
| 5 | 操作前未检查 Worker 容错 | 操作前先验证心跳 + 确认 Worker 进程保护 |

## 📎 相关文件
- `memory/2026-06-10.md` — 当日操作记录
- `MEMORY.md` — 长期记忆（精简条目）