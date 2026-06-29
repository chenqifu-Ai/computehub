# ComputeHub 阶段性总结报告 (2026-06-03 ~ 2026-06-09)

**生成时间**: 2026-06-09 20:41  
**生成人**: 端智 (local-arm)  
**版本**: v1.3.24

---

## 一、概览

本周 ComputeHub 从 v1.3.15 迭代到 v1.3.24，共发布 5 个版本，修复 12+ 个线上 bug，新增两大功能模块：**Agent Registry** 和 **ARC-AI-NET 集群广播机制**。

| 日期 | 版本 | 主题 | 关键改动 |
|------|------|------|----------|
| 6/2 | v1.3.14 | 测试补全 + 文档完善 | README 重写、deploy 瘦身 |
| 6/2 | v1.3.13 | SIGSYS 根治 | SafeCommand 统一绕过 faccessat2 |
| 6/3 | v1.3.16 | 扑克牌桌 + 分布式联机 API | worker_table.html + game_* 端点 |
| 6/5 | v1.3.18 | Android DNS 修复 + TUI 增强 | 自定义 DNS 解析器、TUI 优化 |
| 6/6 | v1.3.19 | platform 感知升级 | arm64/amd64 各取正确 binary |
| 6/7 | v1.3.20 | **Agent Registry** | P0 智能体发现系统 |
| 6/7 | v1.3.22 | SHA256 平台匹配修复 | 去掉 ./ 前缀匹配 |
| 6/8 | v1.3.23 | ActiveTasks 重算 + TUI 分栏 | 防双次完成 + 欠额保护 |
| 6/9 | v1.3.24 | 版本号更新 + TUI 时间解析 | 重构时间显示逻辑 |

**累计改动**: ~2000 行代码，全平台 5/5 交叉编译通过

---

## 二、重大 Bug 修复

### 🐛 1. ARM64 Worker 下载 x86 binary → exec format error

- **现象**: ARM64 Worker 升级时拿到 amd64 binary，运行时 SIGSYS
- **根因**: `DownloadWithChecksum()` 和 `fetchSHA256()` 下载 URL 未传 platform 参数，Gateway 返回默认 amd64
- **修复**: 下载 URL + SHA256 查询都加 `&platform=linux/arm64`，Gateway 校验 API 解析 platform 做架构感知匹配
- **commit**: `c039bee` → `c1e69f8`
- **经验**: 升级链上的每个环节（Agent → HallClient → UpgradeManager → Download）都要传 platform

### 🐛 2. Android Worker SIGSYS crash (faccessat2)

- **现象**: v1.3.13→v1.3.15 升级后，Worker 收到消息触发 Agent → `exec.Command("bash")` → `LookPath` → `faccessat2` → SIGSYS
- **根因**: v1.3.13 SafeCommand 只修了 `upgrade_manager.go`，漏了 `worker_agent.go` 和 `worker_kernel.go` 两处
- **修复**: 两处都改 `executil.SafeLookPath("bash"/"sh")` → 绝对路径
- **commit**: `b2d8ed7`
- **经验**: SafeCommand 全面排查要全项目 grep，不只是改发现问题的文件

### 🐛 3. TUI 任务状态字段重复显示

- **现象**: 任务状态显示为 `completedcompleted` / `failedfailed`
- **根因**: `statusColor()` 已含状态文本，`visiblePad` 又拼一遍
- **修复**: 直接取 `statusColor()` 返回值 + padding，移除中间变量
- **commit**: `fe3cd7b`

### 🐛 4. ActiveTasks 双倍递增

- **现象**: 任务完成但 ActiveTasks 不降反升
- **根因**: SubmitTask 时已 `ActiveTasks++`，Worker poll 时 `pending→running` 又 `++`
- **修复**: 删除 `findPendingTaskForNode` 中冗余的 `ActiveTasks++`
- **commit**: `983a324`

---

## 三、新特性

### 🆕 Agent Registry (v1.3.20)

**P0 智能体发现系统** — 让集群内 Worker 可以互相发现

- **数据结构**: `kernel/agent_registry.go` — AgentRegistry 注册表
  - 注册 / 心跳 / 注销 / 列表 / 查询 / 30s 自动离线
- **API**: `gateway/gateway_agent.go` — 5 个 HTTP handlers
  - `GET /api/v1/agents` — 列出所有 Agent
  - `POST /api/v1/agents/register` — 注册
  - `POST /api/v1/agents/heartbeat` — 心跳
  - `POST /api/v1/agents/unregister` — 注销
  - `GET /api/v1/agents/:id` — 查询单个 Agent
- **集成**: OpcKernel.AgentReg + NewExtendedKernel 初始化 + 路由
- **测试**: 全量测试 15/15 通过 ✅

### 🆕 ARC-AI-NET 集群广播机制 (v1.3.18+)

- 两阶段离线检测 + 全量拓扑发现
- Worker 间自动组网，支持跨节点任务分发

---

## 四、部署状态 (2026-06-09)

| 节点 | 平台 | 版本 | 状态 |
|------|------|------|------|
| ECS (36.250.122.43) | linux/amd64 | v1.3.19 (Gateway) | ✅ systemd |
| ecs-p2ph | linux/amd64 | v1.3.19 (Worker) | ✅ systemd |
| local-arm (xiaomi-table) | linux/arm64 | v1.3.17 (Worker) | ⚠️ 待升级到 v1.3.24 |
| Windows-mobile | windows/amd64 | v1.3.15 (Worker) | ⚠️ 待升级 |

**新节点**: Windows 新节点 `computehub.v1.3.24.exe` 已就绪，等待老大指定节点名后部署。

---

## 五、经验教训沉淀

| 编号 | 教训 | 行动项 |
|------|------|--------|
| EXP-001 | SafeCommand 扫尾不干净 | 全面 grep exec.Command，逐文件确认 |
| EXP-002 | 升级链消息触发 Agent | 升级完成 → HallClient 通知 → Agent exec，链上每个环节都要传 platform |
| EXP-003 | Android seccomp 感知 | Go 1.26 `exec.Command` bare name → faccessat2 → Termux proot 必崩，统一用 SafeLookPath |
| EXP-004 | SHA256 匹配去 ./ 前缀 | resolveSHA256Checksum 去掉 `./` 前缀再做 basename 匹配 |
| EXP-005 | TUI 时间解析重构 | 避免硬编码字符串拼接，统一时间格式化函数 |

---

## 六、下周计划

1. **[P1] 全平台升级到 v1.3.24** — 覆盖 local-arm + Windows 新节点
2. **[P2] Windows 新节点部署** — 节点名确定后立即执行
3. **[P3] ARC-AI-NET 集群广播实测** — 跨节点任务分发验证
4. **[P4] Agent Registry API 文档** — 补充使用示例

---

*报告由端智 (local-arm) 自动生成*  
*ComputeHub 项目地址: ssh://computehub@36.250.122.43:8022/home/computehub/ComputeHub.git*
