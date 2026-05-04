# 📦 Git 记忆管理系统规范

**创建日期**: 2026-04-24  
**版本**: v2.0 (全面重写)  
**制定人**: 小智

---

## 🎯 核心理念

**Git 不是版本控制工具，是记忆系统本身。**  
每一次 commit = 一次记忆固化。  
每一次 search = 一次记忆检索。

---

## 🔄 核心工作流程（SOP）

### 一、文件查找流程（最高优先级）

```
收到任务/查询 → git ls-files | grep 关键词 → 找到 → 读取操作
                                         → 未找到 → git grep 关键词 → 找到 → 读取操作
                                                         → 未找到 → find 文件系统 → 确认
```

**铁律**: 每次查找文件必须先走 git 查找，不能直接猜路径。

#### 具体命令

```bash
# 1. 按文件名搜索（最常用）
cd /root/.openclaw/workspace && git ls-files | grep "<关键词>"

# 2. 按文件内容搜索
cd /root/.openclaw/workspace && git grep -l "<关键词>"

# 3. 按提交历史搜索
cd /root/.openclaw/workspace && git log --all --oneline --grep="<关键词>" -10

# 4. 查看文件修改历史
cd /root/.openclaw/workspace && git log --oneline -- <文件路径>

# 5. 查看最近变更
cd /root/.openclaw/workspace && git log --oneline -5
```

---

### 二、记忆写入流程

```
学习/发现 → 写入对应文件 → git add → git commit → 完成
```

**commit 规范**:
```bash
# 日常记录
git add . && git commit -m "记录: <主题> - <具体发现/结论>"

# 经验教训
git add . && git commit -m "教训: <文件名> - <错误描述> - <修正方案>"

# 系统状态快照
git add . && git commit -m "快照: <日期> - <系统状态简述>"

# 规则更新
git add . && git commit -m "更新: <文件名> - <变更说明>"
```

---

### 三、记忆检索流程

```
查询需求 → 确定搜索维度 → 选择命令 → 获取结果 → 分析回答
```

**搜索维度选择**:
- 找文件 → `git ls-files | grep`
- 找内容 → `git grep -l`
- 找历史 → `git log --grep`
- 找时间 → `git log --since="YYYY-MM-DD"`
- 找配置 → `git grep -l "关键词" -- "*.conf" "*.md"`

---

## 📁 目录结构与 git 映射

```
/root/.openclaw/workspace/
├── HEARTBEAT.md          ← 心跳检查文件（实时状态）
├── MEMORY.md             ← 长期记忆（精炼版）
├── AGENTS.md             ← 行为规范
├── SOUL.md               ← 身份定义
├── USER.md               ← 用户信息
├── SOP.md                ← 执行规则（本文件）
├── TOOLS.md              ← 工具配置
├── memory/
│   ├── YYYY-MM-DD.md     ← 每日记录（git 追踪）
│   └── topics/
│       ├── 技术经验/     ← 技术相关记忆（git 追踪）
│       ├── 执行规则/     ← 规则相关记忆（git 追踪）
│       ├── 经验总结/     ← 经验教训（git 追踪）
│       ├── 项目/         ← 项目记录（git 追踪）
│       └── 投资/         ← 投资相关（git 追踪）
├── scripts/
│   ├── git-memory-search.py   ← Git搜索工具
│   └── git-memory-manager.py  ← Git管理工具
└── ai_agent/
    ├── code/             ← 执行脚本
    └── results/          ← 执行结果
```

---

## 🚦 操作分级与 Git 要求

### 🔴 红色操作（修改核心文件）
**文件**: AGENTS.md, SOUL.md, SOP.md, MEMORY.md
**要求**:
- 必须 commit 并添加详细描述
- 必须告知老大变更内容
- 格式: `更新: <文件名> - <变更说明> - <影响范围>`

### 🟡 黄色操作（修改配置/工具）
**文件**: TOOLS.md, HEARTBEAT.md, 配置文件
**要求**:
- 必须 commit
- 格式: `配置: <文件名> - <变更说明>`

### 🟢 绿色操作（日常记录）
**文件**: memory/YYYY-MM-DD.md, 临时文件
**要求**:
- 累积 3-5 条后统一 commit
- 格式: `记录: <主题> - <具体内容>`

---

## 📝 Commit Message 规范

```
类型: 文件/主题 - 具体内容 - 补充说明

类型: 更新 | 记录 | 教训 | 快照 | 配置 | 修复
```

**示例**:
```
教训: memory/2026-04-24.md - 先git查再操作 - weather skill路径错误
更新: HEARTBEAT.md - 系统状态更新 - 负载改善
记录: memory/2026-04-24.md - Ollama服务恢复
```

---

## ⚠️ 常见错误与防范

| 错误 | 后果 | 防范 |
|------|------|------|
| 猜路径不 git 查 | 读取错误文件 | 先 git ls-files 再操作 |
| 只修改不 commit | 记忆丢失 | 每次修改后立即 commit |
| commit 无描述 | 无法追溯 | 必须写描述 |
| 大改不验证 | 破坏系统 | commit 前验证 |
| 跨分支操作 | 冲突 | 同一分支操作 |

---

## 🔄 自动化记忆流程

### 每日自动 snapshot
```bash
git add . && git commit -m "每日快照 - 系统状态记录"
```

### 每次交互后
```bash
# 记录关键决策/发现
git add memory/YYYY-MM-DD.md && git commit -m "记录: 交互中的关键信息"
```

---

**生效日期**: 2026-04-24  
**审核人**: 老大
