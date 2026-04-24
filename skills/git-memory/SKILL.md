# 🧠 Git 记忆技能

**版本**: v1.0  
**创建日期**: 2026-04-24  
**描述**: 将 Git 变成记忆系统 — 搜索、管理、快照、恢复

---

## 安装

```bash
# 一键安装（推荐）
curl -sSL https://raw.githubusercontent.com/.../git-memory-setup.sh | bash

# 或手动安装
git clone <repo> && cd git-memory && ./setup.sh
```

## 快速使用

```bash
# 搜索记忆
python3 scripts/git-memory-search.py keyword "关键词"
python3 scripts/git-memory-search.py commit "提交关键词"
python3 scripts/git-memory-search.py time --since="2026-04-20"

# 管理记忆
python3 scripts/git-memory-manager.py commit -m "描述"
python3 scripts/git-memory-manager.py maintenance
python3 scripts/git-memory-manager.py status
```

## 核心能力

- 🔍 **关键词搜索**: 全文搜索所有记忆文件
- 📅 **时间搜索**: 按时间范围检索
- 📝 **提交搜索**: 搜索提交历史
- 📸 **快照**: 每日自动快照
- 🔄 **恢复**: 从 git 恢复任何文件
- 📊 **状态**: 查看系统状态

## 目录结构

```
git-memory/
├── SKILL.md              ← 本文件
├── README.md             ← 详细文档
├── setup.sh              ← 安装脚本
├── verify.sh             ← 验证脚本
├── scripts/
│   ├── git-memory-search.py    ← 搜索工具 (231 行)
│   └── git-memory-manager.py   ← 管理工具 (216 行)
├── templates/
│   ├── .gitignore          ← Git 忽略模板
│   └── .gitmemory-config.json ← 配置模板
└── docs/
    ├── 铁律.md             ← 使用规则
    └── 目录规范.md         ← 目录结构
```
