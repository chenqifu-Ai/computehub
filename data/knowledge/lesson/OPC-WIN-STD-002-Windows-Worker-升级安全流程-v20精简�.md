# Knowledge: OPC-WIN-STD-002: Windows Worker 升级安全流程 v2.0（精简版）
> Type: lesson
> Source: local-arm
> Confidence: 0.8
> TTL: 30 days
> Tags: OPC-WIN-STD-002, v2.0, Windows, Worker升级, 致命教训, 零停机, PowerShell, EncodedCommand, SOP, 精简版
> Timestamp: 2026-07-07T08:13:28+08:00

## Content

# OPC-WIN-STD-002 v2.0 — Windows Worker 升级安全流程（精简版）

**更新**: 2026-07-07 | **作者**: 端智 💻

## 12 条致命教训速查

| # | 教训 | 一句话规则 |
|---|------|-----------|
| 💀1 | 自动升级=自杀 | 永远手动两步走 |
| 💀2 | exit_code=7不是命令问题 | 网络不通，等15s重试 |
| 💀3 | 不探测语法就动手 | 先echo probe_check |
| 💀4 | 链式操作=盲人摸象 | 每步独立提交 |
| 💀5 | 走非Gateway通道 | 唯一通道=Gateway task |
| 💀6 | Task超时不隔离进程 | 必须进程组隔离 |
| 💀7 | 不验证SHA就替换 | certutil算SHA比对 |
| 💀8 | 不确认新旧并存就杀旧 | 新旧都在线才能动手 |
| 💀9 | 下载时间给不够 | timeout≥300s |
| 💀10 | &在cmd里是命令分隔符 | 直接上PowerShell -EncodedCommand |
| 💀11 | PS远程执行必须用-EncodedCommand | 所有PS脚本用base64(UTF16LE)编码 |
| 💀12 | task的duration字段是金矿 | duration<1s→瞬间失败 |

## 升级 SOP（12步）

**Step 0**: Gateway健康检查 → 确认binary就位 → 确认节点在线
**Step 1**: 语法探测（echo probe_check）
**Step 2**: 查旧Worker信息（路径、PID、tmp目录）
**Step 3**: 下载新binary（PowerShell -EncodedCommand，不杀旧进程）
**Step 4**: 验证完整性（SHA256 + version）
**Step 5**: 启动新进程（node-id: xxx-new）
**Step 6**: 验活（新Worker能干活）
**Step 7**: 确认新旧都在线
**Step 8**: 精准杀旧PID（通过新Worker执行）
**Step 9**: 验下线（旧节点消失）
**Step 10**: 替换binary + 启动原node-id + 清理幽灵节点
**Step 11**: 终验（版本号正确 + 任务能跑）

## 回滚预案
- 新节点没注册上 → 清理临时文件，旧Worker活着
- 双亡 → 通过中转节点重启Worker
- move失败 → 跳过，下次重启处理
- 语法探测失败 → 不猜了，找老大
