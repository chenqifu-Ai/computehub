# 🏛️ AI 大厅记忆与经验系统总结

**创建时间**: 2026-06-27 06:37  
**部署位置**: ECS Gateway `http://36.250.122.43:8282/ai`  
**存储路径**: `~/memory/topics/`

---

## 📖 系统概述

ECS Gateway 的 AI 大厅（`/ai`）集成了三大核心模块：

| 模块 | 说明 | 存储 |
|------|------|------|
| 🧠 共享记忆 (Memory) | Agent 长期记忆，跨会话持久化 | `~/memory/` |
| 📖 经验 (Experience) | 从实践中提炼的最佳实践、教训 | `~/memory/topics/` |
| 🖥️ 节点 (Nodes) | 集群节点状态、健康、能力 | Gateway 内存 + 持久化 |

---

## 🧠 共享记忆 (Memory)

### 机制
- **跨会话持久化**：Agent 每次启动时读取 `MEMORY.md` + 最近 `memory/YYYY-MM-DD.md`
- **自动加载**：main session 加载 MEMORY.md，sub-session 只加载 daily notes
- **内容分类**：
  - **历史时刻**：重大事件（如首次跨 Agent 通讯）
  - **核心教训**：踩坑经验（如 System32 binary 替换、PATH 陷阱）
  - **配置备忘**：API Key、设备信息、模型配置
  - **待办跟踪**：未完成事项

### 当前内容
- 已归档 **10+ 条核心经验**（Windows 安装、邮件发送、Agent 通讯、Binary 替换等）
- 持仓记录（华联股份 000882）
- 模型规则锁定
- 设备连接管理

### 维护规则
- **Daily notes**：当天发生了什么，原始日志
- **MEMORY.md**：从 daily notes 中提炼的精华，定期整理
- **编辑需通知用户**：这是"灵魂文件"，修改要告知

---

## 📖 经验 (Experience)

### 机制
- **主题分类**：按领域组织到 `~/memory/topics/` 子目录
- **标准文档化**：每个经验提炼为可执行标准（如 WIN-STD-001）
- **可引用**：其他 Agent 或文档可引用这些标准

### 已有经验分类

| 领域 | 标准编号 | 说明 |
|------|----------|------|
| Windows 操作 | WIN-OPC-001 | Windows 远程操作前置检查清单 |
| Windows 安装 | WIN-STD-001 | 远程 Windows 软件安装标准流程 |
| Windows 替换 | WIN-REPL-001 | System32 binary 替换标准流程 |
| Windows 升级 | WIN-UPG-002 | Windows 节点升级标准流程 |
| 邮件发送 | STD-003 | 统一发邮件脚本使用规范 |
| 文件编辑 | — | edit 工具精确匹配陷阱 |
| 架构审查 | — | ComputeHub v1.0.0 架构审查报告 |

### 经验提炼流程
1. **踩坑** → 记录问题现象和根因
2. **提炼** → 抽象为通用规则（STAR/编号命名）
3. **文档化** → 写入 `memory/topics/执行规则/` 或 `技术经验/`
4. **固化** → 核心规则写进 AGENTS.md 铁律

---

## 🖥️ 节点 (Nodes)

### 集群拓扑
| 节点 | 位置 | 角色 | 状态 |
|------|------|------|------|
| ecs-p2ph | 36.250.122.43 | Gateway + Worker (Coordinator) | ⚠️ 间歇无响应 |
| local-arm | 本机 Termux | 端智 (LLM 重活) | ✅ Online |
| windows-mobile01 | 112.48.104.210 | Worker | 🔴 Offline |
| wanlida-opc01 | 183.251.21.92 | Worker | 🔴 Offline |
| wanlida-ubuntu | 112.48.4.56 | Worker | 🔴 Offline |

### 健康监控
- **心跳间隔**：Worker 10s，Gateway 15s
- **跨 Agent 互备**：每次心跳自动检查其他 Gateway 状态
- **告警**：连续 2 次检测失败 → 邮件告警

---

## 🔗 记忆系统价值

1. **知识沉淀**：踩过的坑变成团队资产，不再重复犯错
2. **标准执行**：核心规则写进 AGENTS.md，Agent 必须遵守
3. **跨 Agent 共享**：多个 Agent 通过统一 memory 目录协同
4. **审计追溯**：每日 memory 文件 = 完整操作日志
5. **持续进化**：MEMORY.md 定期整理 = 知识蒸馏

---

## 📋 改进建议

| 优先级 | 建议 | 说明 |
|--------|------|------|
| P0 | 经验自动归档 | Agent 完成重要任务后自动写入 topics/ |
| P1 | 经验引用链接 | 文档中用 `[WIN-STD-001]` 可跳转引用 |
| P1 | 经验时效性标注 | 过期经验标记 `[已过期]`，避免误导 |
| P2 | 经验搜索 | 按关键词搜索所有经验文档 |
| P2 | 经验贡献者 | 标注谁提炼的经验，便于追踪 |

---

*本文档部署到 ECS AI 大厅，供所有 Agent 查阅参考*
