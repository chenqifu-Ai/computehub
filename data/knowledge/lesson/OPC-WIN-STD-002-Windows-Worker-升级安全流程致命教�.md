# Knowledge: OPC-WIN-STD-002: Windows Worker 升级安全流程（致命教训版）v1.2
> Type: lesson
> Source: local-arm
> Confidence: 0.8
> TTL: 30 days
> Tags: OPC-WIN-STD-002, Windows, Worker升级, 致命教训, 零停机, PowerShell, EncodedCommand, SOP, 安全流程
> Timestamp: 2026-07-07T08:02:38+08:00

## Content

# OPC-WIN-STD-002 v1.2 — Windows Worker 升级安全流程

**版本**: v1.2 | **更新**: 2026-07-07 | **作者**: 端智 💻

## 12 条致命教训速查

| # | 致命教训 | 一句话规则 |
|---|---------|-----------|
| 💀1 | 自动升级=自杀 | 永远手动两步走 |
| 💀2 | exit_code=7不是命令问题 | 网络不通，等15s重试 |
| 💀3 | 不探测语法就动手 | 先echo probe_check |
| 💀4 | 链式操作=盲人摸象 | 每步独立提交 |
| 💀5 | 走非Gateway通道 | 唯一通道=Gateway task |
| 💀6 | Task超时不隔离进程 | 必须进程组隔离 |
| 💀7 | 不验证SHA就替换 | certutil算SHA比对 |
| 💀8 | 不确认新旧并存就杀旧 | 新旧都在线才能动手 |
| 💀9 | 下载时间给不够 | timeout≥300s，大文件≥600s |
| 💀10 | &在cmd里是命令分隔符 | 直接上PowerShell -EncodedCommand |
| 💀11 | PowerShell远程执行必须用-EncodedCommand | 所有PS脚本用base64(UTF16LE)编码 |
| 💀12 | task的duration字段是金矿 | duration<1s→瞬间失败，先查duration |

## 核心经验

### Windows 远程执行铁律
1. **所有包含 & 的 URL 必须用 PowerShell -EncodedCommand** — cmd 把 & 当命令分隔符，^&、%26、cmd /c 都不可靠
2. **所有 PowerShell 脚本用 base64(UTF16LE) 编码** — 绕过 shell/Python/JSON 三层转义
3. **tasklist | findstr 替代 tasklist /FI** — 避免引号被 cmd 吃掉
4. **限定搜索范围** — where /R C:\ 太慢，用 dir /s /b C:\Temp\

### 零停机升级 12 步 SOP
0. Gateway 健康检查 + 确认 binary 就位 + 确认节点在线
1. 语法探测（echo probe_check）
2. 查旧 Worker 信息（路径、PID、tmp目录）
3. 下载新 binary（不杀旧进程，PowerShell -EncodedCommand）
4. 验证完整性（SHA256 + version）
5. 启动新进程（不同 node-id，如 xxx-new）
6. 验活（新 Worker 能干活）
7. 确认新旧都在线
8. 精准杀旧进程（通过新 Worker 杀旧 PID）
9. 验下线（旧节点消失）
10. 替换 binary + 清理临时文件
11. 终验（版本号正确 + 任务能跑）

### 回滚预案
- 场景A: 新节点没注册上 → 清理临时文件，旧Worker活着
- 场景B: 双亡 → 通过中转节点重新启动Worker
- 场景C: move binary失败 → 跳过move，下次重启处理
- 场景D: 语法探测失败 → 不猜了，找老大
