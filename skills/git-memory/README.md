# Git 记忆系统 - 完整文档

## 核心概念

Git 不只是版本控制工具，而是**记忆系统本身**:
- 每次 commit = 一次记忆固化
- 每次 search = 一次记忆检索
- 每次 restore = 一次记忆恢复

## 安装与配置

### 1. 安装

```bash
cd /root/.openclaw/workspace
bash setup.sh
```

### 2. 配置

编辑 `.gitmemory-config.json`:
```json
{
  "git": {
    "authorName": "你的名字",
    "authorEmail": "your@email.com",
    "pushToRemote": false,
    "remoteUrl": "你的仓库地址"
  }
}
```

### 3. 验证

```bash
bash verify.sh
```

## 搜索命令

### 关键词搜索
```bash
python3 scripts/git-memory-search.py keyword "关键词"
# 示例: python3 scripts/git-memory-search.py keyword "股票"
```

### 提交搜索
```bash
python3 scripts/git-memory-search.py commit "提交关键词"
# 示例: python3 scripts/git-memory-search.py commit "ComputeHub"
```

### 时间搜索
```bash
python3 scripts/git-memory-search.py time --since="2026-04-20"
# 搜索过去 N 天的文件变更
```

### 文件搜索
```bash
python3 scripts/git-memory-search.py file "文件名"
# 按文件名搜索
```

## 记忆管理

### 创建记忆
```bash
python3 scripts/git-memory-manager.py commit -m "描述记忆内容"
```

### 每日快照
```bash
python3 scripts/git-memory-manager.py snapshot
```

### 系统状态
```bash
python3 scripts/git-memory-manager.py status
```

### 维护
```bash
python3 scripts/git-memory-manager.py maintenance
```

## 目录规范

### 记忆目录
```
memory/
├── INDEX.md              # 记忆索引
├── daily/                # 每日记忆
│   ├── 2026-04-24.md
│   └── ...
├── topics/               # 主题记忆
│   ├── 技术经验/
│   ├── 执行规则/
│   └── ...
└── search-index/         # 搜索索引
```

### 项目目录
```
projects/
├── INDEX.md              # 项目索引
├── computehub/           # 项目 1
│   ├── README.md
│   ├── docs/
│   └── code/
├── stock-trading/        # 项目 2
└── ...
```

## 铁律

### 1. 先 Git 查，再操作
```bash
# ❌ 错误：猜路径
cat /path/to/file.md

# ✅ 正确：先 Git 查
git ls-files | grep 关键词
git grep -l 关键词
```

### 2. 每次修改必须 commit
```bash
# 任何文件修改后立即 commit
git add . && git commit -m "更新: 文件名 - 变更说明"
```

### 3. 项目必须纳入 Git
```bash
# 创建新项目后立即纳入管理
mkdir projects/new-project && cd projects/new-project
git add . && git commit -m "init: 项目名 - 初始化"
```

## 迁移到新服务器

### 备份
```bash
# 备份整个仓库
cd /root/.openclaw/workspace
git bundle create workspace-bundle.bundle --all
```

### 恢复
```bash
# 在新服务器创建 bundle
git clone --bundle=workspace-bundle.bundle <new-server>
cd <new-server>
bash skills/git-memory/setup.sh
```

### 一键迁移脚本
```bash
#!/bin/bash
# 迁移到新服务器
NEW_SERVER="$1"
cd /root/.openclaw/workspace

# 创建 bundle
git bundle create /tmp/workspace-bundle.bundle --all --branches --tags

# 推送到新服务器
scp /tmp/workspace-bundle.bundle $NEW_SERVER:/tmp/
ssh $NEW_SERVER "cd /root/.openclaw && git clone --bundle=/tmp/workspace-bundle.bundle . && cd /root/.openclaw/workspace && bash skills/git-memory/setup.sh"
```
