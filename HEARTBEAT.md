# 💓 小智影业 - 公司脉搏（Stream管理）

**CEO**: 小智  
**管理模式**: 数据驱动 + 定期心跳检查  
**更新频率**: 每天一次脉搏

---

## 📊 每日脉搏检查清单

### 营销部（营销专家）
- [ ] 今日发布内容数量: 待更新（无数据源）
- [ ] 播放量数据: 待更新（无数据源）
- [ ] 粉丝增长数据: 待更新（无数据源）
- [ ] 爆款内容识别: 待更新（无数据源）

### 制作部（HR专家）
- [ ] 今日产出: 待更新（新的一天）

### 财务部（财务专家）
- [ ] 当日成本支出: 待更新
- [ ] 收入数据跟踪: 待更新
- [ ] ROI计算: 待更新
- [ ] 风险预警: 待更新

### 数据部（网络专家）
- [ ] 数据监控: 待检查

### 风控部（法务专家）
- [ ] 合规检查: 待检查

---

## 🚨 预警阈值

| 部门 | 预警指标 | 阈值 | 响应时间 |
|------|----------|------|----------|
| 营销部 | 播放量低于均值 | <50% | 立即汇报 |
| 制作部 | 产出低于目标 | <2条/天 | 立即汇报 |
| 财务部 | 成本超支 | >¥15/天 | 立即汇报 |
| 数据部 | 热点漏报 | >2小时 | 立即汇报 |
| 风控部 | 合规问题 | 任何违规 | 立即处理 |

---

## 📈 数据看板

### 关键指标（实时更新）
- **粉丝数**: 待更新
- **总播放量**: 待更新
- **今日产出**: 待更新
- **今日收入**: 待更新
- **今日成本**: 待更新
- **ROI**: 待更新

### 周目标进度
- **周播放目标**: 10万
- **当前进度**: 待更新
- **完成率**: 待更新

---

## 🚨 系统状态监控 (2026-06-26 14:55 更新)

- **当前模型**: ollama-cloud-2/deepseek-v4-flash
- **ECS OpenClaw Gateway** (36.250.122.43:18789): ⚠️ 无响应（空响应）
- **ECS SSH** (36.250.122.43:8022): ✅ 可达（可用）
- **ECS ComputeHub Gateway** (36.250.122.43:8282): ⚠️ 404 page not found（进程可能已换端口或重启）
- **ECS ecs-p2ph Agent** (36.250.122.43:8383): ⚠️ 空响应（进程可能已重启）
- **wanlida-opc01**: 🔴 OFFLINE (183.251.21.92, SSH/CLOSED, GW CLOSED) — ⚠️ 从 ✅ 变为离线
- **wanlida-ubuntu**: 🔴 OFFLINE (112.48.4.56, SSH TIMEOUT, 从 ECS ping 100% loss) — ⚠️ 从 ✅ 变为离线
- **xingke-work01**: 🔴 OFFLINE (120.41.115.133, SSH CLOSED) — ⚠️ 从 ✅ 变为离线
- **windows-mobile01**: 🔴 OFFLINE (112.48.104.210, SSH CLOSED) — ⚠️ 从 ✅ 变为离线
- **local-arm**: ✅ online (36.248.233.177, linux/arm64) — 本机
- **xiaomi-table**: ⚠️ 未检测 (112.48.48.185)
- **wanlida-temp**: 🔴 OFFLINE
- **本地 OpenClaw Gateway** (127.0.0.1:18789): ✅ 200 响应正常
- **ComputeHub Gateway 本地** (127.0.0.1:8282): ❌ DOWN
- **Tailscale**: 已登出（ECS）

## 🔒 锁定工程：ComputeHub_new 主工程
- **路径**: `/data/data/com.termux/files/home/ComputeHub_new/`
- **最新版本**: v1.3.46 ✅ 本地已编译
- **新功能**: openclaw_chat 持久化管道集成（v1.3.41）
- **文档**: `docs/SHELL-ARCH-v1.md` + 通信架构说明 → 已发邮件
- **远端仓库**: `ssh://computehub@36.250.122.43:8022/home/computehub/ComputeHub.git` ⏳ 离线

---

### ✅ 今日完成 (2026-06-20)
- 🏆 **首次跨 Agent 通讯成功** — 端智(Android ARM64) ↔ 小智(ECS x86_64) 通过 sessions_send 握手
- 🧩 **openclaw_chat 持久化管道集成** — v1.3.41，省掉每次 proot 启动开销
- 📄 **CLU-STM-001 标准文档** — 集群跨Agent通信标准流程 v1.0
- 🐍 **贪吃蛇协作开发** — 端智写前端(snake.html)，小智编译运行(ECS:8080)
- 📋 **咨询服务协议审阅** — 希投科技并购居间协议逐条分析
- 🔍 **windows-mobile 状态确认** — v1.3.30 存活，HTTP轮询正常，WS间歇超时
- 📝 **本周工作复盘** — 6/15-6/20 完整总结
- 📝 **历史时刻归档** — 首次跨Agent通讯写入 MEMORY.md + git commit
- 🕵️ **ECS 凌晨异常排查** — 根因：Ubuntu 自动安全更新升级内核 `6.8.0-117→124`，06:08 自动重启
- 🐛 **修复 Windows SYSTEM 账户升级路径 bug** — 新增 `getWorkerHomeDir()`，三处硬编码路径替换
- 🆕 **v1.3.7 发布** — 双平台编译 (win/linux amd64)，deploy 同步，Gateway + Worker 已升级
- ⚙️ **systemd 开机自启修复** — `systemctl enable computehub-gateway` + `computehub-worker`
- 📦 **git push** — commit a7df0bf 推送到 ECS
- 🪟 **Windows-mobile 升级验证** — 已确认 Agent 在跑（health/status 正常），v1.3.5→1.3.6 因路径 bug 卡住，v1.3.7 已修复
- **API Key管理**: ✅ 从config.json读取（`composer.api_key`），不再硬编码
- **LLM Proxy**: ✅ Gateway中转端点`/api/v1/llm/chat/completions`

---

### ✅ 今日完成 (2026-06-02 18:00-19:00)
- 🎯 **Agent 智能度评估 + 三大卡点修复** ✅
- 📄 Agent 智能度评估报告 → 发到 19525456@qq.com ✅
- 🔧 修复 #1: **30s硬超时** — `execShell` 的 `maxWait` 从硬编码30s改为 `step.Timeout`(默认300s) ✅
- 🔧 修复 #2: **JSON解析脆弱** — 新增 `extractJSON()`：去代码块包裹 + 括号平衡法截取 ✅
- 🌐 新增 #3: **web_search 工具** — DuckDuckGo免费API，Agent能联网查资料 ✅
- 📊 改动: 2 files, +218/-16 lines, `go build ✅`

### ✅ 今日完成 (2026-06-02 20:15-20:46)
- 🗔 **Windows-mobile v1.3.4→v1.3.5 升级** ✅
- 📝 **WIN-UPG-002 标准流程** — 精简版，`&`链黄金规则 + Phase2超时45s
- 📧 WIN-UPG-002 → 已发邮件到 19525456@qq.com
- 📦 WIN-UPG-002 → git commit `ace167d` + push ✅
- 🤖 **Windows-mobile Worker Agent 沟通测试** — health✅ status✅ think✅(LLM超时，Agent本体正常)
- 📝 踩坑记录：cmd转义地狱，最终certutil解码payload绕开JSON嵌套问题

### ✅ 今日完成 (2026-06-02 16:00-17:00)
- 🎯 **v1.3.3: Phase 3 Zero-Downtime 升级 (test-register模式)** ✅
- 🆕 `worker_upgrade_executor.go` — 父进程：下载→spawn→TCP IPC 仲裁→备份→exit(0)
- 🆕 `worker_upgrade_test_register.go` — 子进程：`--test-register` 注册验证→替换→正式运行
- ✅ UpgradeManager 改用 UpgradeExecutor，不再依赖外部脚本
- ✅ 核心流程：子进程先注册验证成功 → 父进程备份退出 → 子进程替换binary + 重新注册
- ✅ ECS Gateway v1.3.3 (port 8282) — 升级通道 1.3.2→1.3.3 ✅
- ✅ Git commit `f250209` + push to server ✅
- 💡 这版解决了老方案"先死再升"的断联窗口问题

### ✅ 今日完成 (2026-06-02 07:00-07:30)
- 🎯 **v1.3.0 Phase 2 Upgrade Engine 发布** ✅
- ✅ `UpgradeEngine` — SHA256验证/独立脚本/回滚/多策略
- ✅ 18 files, +1334/-829 lines, git commit 878c15f
- ✅ 全平台交叉编译 5/5 (linux/darwin/windows × amd64/arm64)
- ✅ ECS Gateway/Worker 升级到 v1.3.0 (systemd重启)
- ✅ Worker (ecs-p2ph) 已在 v1.3.0 运行
- ✅ Windows-mobile 远程触发重启，等待自动检测升级
- ✅ deploy/version.txt = 1.3.0, SHA256校验和已上传

## 🔒 锁定工程：ComputeHub_new 主工程
**老大明确：所有精力集中于此工程 (2026-06-13 更新)**
- **路径**: `/data/data/com.termux/files/home/ComputeHub_new/`
- **版本**: v1.3.46
- **结构**: `cmd/ src/ deploy/ scripts/`，独立 Go 工程
- **远端仓库**: `ssh://computehub@36.250.122.43:8022/home/computehub/ComputeHub.git`
- **部署**: ECS 36.250.122.43:8282 (Gateway) + Workers

### 废弃路径
- `~/ComputeHub/`（旧克隆，不再使用）
- `~/OPC/`（同一仓库旧克隆，不再使用）
- **任何其他项目/任务/建议** 除非老大主动提，否则一律不碰

### ✅ 今日完成 (2026-06-02 12:00-13:45)
- 🐛 **修复 ActiveTasks 双倍递增 bug** — `findPendingTaskForNode` 中冗余的 `ActiveTasks++` 已移除
- ✅ compile + deploy linux-amd64 v1.3.1 → ECS
- ✅ systemd restart → ActiveTasks 已清零
- ✅ 根因：SubmitTask 时已++，Worker poll 时又++，净效果每任务多1
- 🐛 **修复 Gallery 前端上传文件看不见** — `renderFileList()` 缺 `classList.remove("hidden")`，用户上传成功但看不到
- ✅ 编译部署 v1.3.2 到 ECS Gateway + ecs-p2ph Worker
- 🆕 **Worker Agent Dashboard** — 加了个漂亮状态页面（`/` 根路径），Windows 浏览器打开 `localhost:8383` 就能看到 Workers 状态
- ⚠️ **windows-mobile Worker 被杀挂了**（升级命令下载失败且进程被 kill）
  - 状态: offline，需要手动重新启动
  - 下载地址: http://36.250.122.43:8282/api/v1/download?file=computehub-windows-amd64.v1.3.2.exe
  - 启动指令: `computehub.exe worker --gw http://36.250.122.43:8282 --node-id Windows-mobile --interval 3 --concurrent 4 --heartbeat 10`

## 🔒 跨 Agent 互备监控（2026-06-13 新增）

**根因**: 上次 ECS gateway 因配置错误反复重启 3 天无人发现

**方案**: 每次心跳自动检查所有 gateway 健康状态

### 实时监控清单
- [ ] ECS main gateway (36.250.122.43:18789) — 通过 SSH 检查
- [ ] win 节点 gateway (192.168.2.134:18789) — 通过 ECS SSH 检查
- [ ] 本地 gateway (127.0.0.1:18789) — 直接检查

### 告警机制
- 连续 2 次检测失败 → 邮件告警到 19525456@qq.com
- 自动修复: ECS gateway 支持 `--auto-fix` 自动重启
- 报告保存: `reports/daily/gateway_health_YYYY-MM-DD.json`

### 配置文件
- 脚本: `scripts/gateway_health.py`
- 状态: `reports/daily/gateway_health_state.json`

## 🤖 Agent 集群管控系统（2026-06-13 新增）

**目标**: 让 4 个物理独立的 agent 能相互协商、协同管控集群

### 核心组件

| 组件 | 文件 | 功能 |
|---|---|---|
| 集群控制器 | `scripts/agent_coordinator.py` | 统一管理 4 个 agent |
| 心跳监控 | `scripts/gateway_health.py` | 每分钟检查 gateway 健康 |
| 定时巡检 | cron: Gateway 健康检查 | 每 10 分钟自动检查 |
| 状态存储 | `reports/cluster/` | 集群状态持久化 |

### 4 个 Agent 角色

| Agent | 节点 | 角色 | 能力 |
|---|---|---|---|
| main (端智) | 本地 | Coordinator | monitor, control, notification |
| arm | ECS | Monitor | health_check, remote_exec, config_update |
| win | Windows | Compute | windows_exec, gpu_tasks, remote_control |
| mi | 待配置 | Scheduler | task_dispatch, load_balance, resource_mgmt |

### 协商协议

1. **心跳协议**: 每 60 秒广播状态
2. **故障转移**: 检测异常 → 自动通知 → 切换备用
3. **任务分发**: 基于能力匹配的任务调度
4. **配置同步**: 变更通知 + 状态共享

---

### ✅ 今日完成 (2026-05-31)

### 本周事项
- [ ] Gallery 路径问题排查（联农丢失根因）
- [ ] Gallery 帮助页面 / 使用说明书
- [ ] ComputeHub Sprint 6 — 任务超时/重试机制
- [ ] 将 192.168.2.140 注册为 Worker 节点接入主集群
- [ ] GitHub 公开 ComputeHub 仓库
- [ ] Worker Agent → 部署到真实GPU服务器测试
- [ ] 自举验证：所有代码传输/部署通过 ComputeHub 自身完成
- [ ] Windows 节点部署 `computehub.exe worker --agent`（旧 WMI 已退役）

### ✅ 今日完成 (2026-05-31)
- 🎯 **ComputeHub 全链路算力分发压测** ✅
- ✅ 14 个集群任务，13 完成，0 待处理
- ✅ 4 节点跨平台算力分发（Android/Linux/Windows）
- ✅ Worker Agent SIGSYS crash 修复（faccessat2 + shell路径）
- ✅ 8383 Agent 端口联调：health/status/think 正常
- ✅ Windows 节点 OpenClaw 2026.3.12 安装（npm install -g）
- ✅ 集群容量管控验证（max_concurrent=4 生效）

### ✅ 本周完成 (2026-05-27)
- 🎯 **OPC v1.1.0 发布 — SSE 流式 AI 对话** ✅
- ✅ `composer/client.go`: 新增 `ChatStream()` 流式 LLM 调用
- ✅ `agent/agent.go`: 新增 `ThinkStream()` 逐步推送
- ✅ `gateway/gateway.go`: 新增 `POST /api/v1/agent/stream` SSE 端点
- ✅ `gallery.go` + `/ai` 页面: 前端改用流式渲染（逐字显示）
- ✅ Windows worker 交叉编译 v1.1.0 + deploy 更新
- ✅ 服务器 SSH 8022 端口 + iptables 排查确认
- ✅ OPC 项目 git 提交 + 推送到服务器
/v1/agent/stream` SSE 端点
- ✅ `gallery.go` + `/ai` 页面: 前端改用流式渲染（逐字显示）
- ✅ Windows worker 交叉编译 v1.1.0 + deploy 更新
- ✅ 服务器 SSH 8022 端口 + iptables 排查确认
- ✅ OPC 项目 git 提交 + 推送到服务器
t 提交 + 推送到服务器
