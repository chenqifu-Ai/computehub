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
- [x] 今日产出: **视频管线音频三大bug修复 + v0.7.13 发布** ✅
- [x] 修复1: 声音快进 → 统一采样率44100Hz ✅
- [x] 修复2: 声音重复播 → 解除BGM双循环 ✅
- [x] 修复3: 片段重复 → 拆分段编码累加bug ✅
- [x] GitHub提交 7cbcead ✅
- [x] linux-amd64/linux-arm64 编译通过 ✅

### 财务部（财务专家）
- [ ] 当日成本支出: 待更新
- [ ] 收入数据跟踪: 待更新
- [ ] ROI计算: 待更新
- [ ] 风险预警: 待更新

### 数据部（网络专家）
- [x] 竞品动态监控: ✅ 已完成
- [x] 热点话题识别: ✅ 已完成
- [x] 数据报告生成: ✅ 已完成
- [x] 市场趋势分析: ✅ 已完成

### 风控部（法务专家）
- [x] 内容合规检查: ✅ 已完成
- [x] 版权风险扫描: ✅ 已完成
- [x] 平台政策更新: ✅ 已完成
- [x] 风险预警: ✅ 已完成

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
- **今日产出**: 待更新（新的一天）
- **今日收入**: 待更新
- **今日成本**: 待更新
- **ROI**: 待更新

### 周目标进度
- **周播放目标**: 10万
- **当前进度**: 待更新
- **完成率**: 待更新

---

## 🔄 自动化任务

### 每日检查 (上午9:00)
- [x] 数据看板更新 ✅ (2026-06-01 09:12)
- [x] KPI监控 ✅
- [x] 异常预警 ✅ (ecs-p2ph offline → 自动恢复)

### 每日报告
- 早9:00: 昨日数据汇总和当日计划
- 下午15:00: 下午运营状态报告 ✅ 已发送至 19525456@qq.com
- 下午16:07: 下午运营状态报告 ✅ 已发送
- 下午15:04: 下午运营状态报告 ✅ 已发送至 19525456@qq.com (2026-05-30)

### 自动化任务执行记录 (2026-05-31 更新)
- 05:40 | ✅ 百炼 API 用量日报 — 已发送 (同昨日数据, 无新用量)
- 12:00 | ✅ 法海法律顾问风险评估 — LOW风险，4个问题
- 15:00 | ✅ 下午公司脉搏报告 — 已发送至 19525456@qq.com
- 20:02 | ✅ 百炼 API 用量日报 — 6,639 tokens (17次), ¥0.05
- 20:02 | ✅ 每日投资日报 — 已发送至 19525456@qq.com

---

## 🚨 系统状态监控

### 实时系统状态 (2026-06-02 16:59 心跳)
- **本机负载**: 🔴 20.55/20.48/21.23 — **持续严重高负载** (编译进程)
- **本机内存**: ⚠️ 202MB free / 11G (2.8G available)
- **本地磁盘**: ⚠️ 85% (391G/463G)
- **当前模型**: ollama-cloud-2/deepseek-v4-flash
- **模型配置**: ✅ 正常
- **NewAPI key**: ✅ 正常

### ECS-2 (36.250.122.43) 生产状态
- **ComputeHub Gateway**: ✅ **v1.3.5** (8282端口)
- **Worker (ecs-p2ph)**: ✅ v1.3.5 (linux/amd64)
- **Worker (Windows-mobile)**: ✅ **v1.3.5** (windows/amd64) — Agent在线，health/status正常
- **SSH**: ✅ 8022端口 (computehub 用户，ed25519 key)
- **活跃任务**: 0 tasks

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

## 🔒 锁定工程：OPC 主工程
**老大明确：所有精力集中于此工程**
- **路径**: `/data/data/com.termux/files/home/OPC/`
- **版本**: v1.3.3 (git: f250209)
- **最新**: Phase 3 test-register 零断联升级
- **注意**: workspace/computehub 已停用，不关注
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

## 📋 待办事项

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
