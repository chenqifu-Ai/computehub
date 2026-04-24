#!/bin/bash
# Git 记忆系统一键安装脚本
# 使用: bash setup.sh [目标目录]
# 示例: bash setup.sh /root/.openclaw/workspace

set -e

TARGET_DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧠 正在安装 Git 记忆系统..."
echo "   目标目录: $TARGET_DIR"

# 1. 初始化 Git 仓库（如果不存在）
if [ ! -d "$TARGET_DIR/.git" ]; then
    echo "   📦 初始化 Git 仓库..."
    git -C "$TARGET_DIR" init
    git -C "$TARGET_DIR" config user.name "AI Assistant"
    git -C "$TARGET_DIR" config user.email "ai@openclaw.ai"
fi

# 2. 复制工具脚本
echo "   📋 复制工具脚本..."
mkdir -p "$TARGET_DIR/scripts"
cp "$SCRIPT_DIR/scripts/git-memory-search.py" "$TARGET_DIR/scripts/"
cp "$SCRIPT_DIR/scripts/git-memory-manager.py" "$TARGET_DIR/scripts/"
chmod +x "$TARGET_DIR/scripts/git-memory-search.py"
chmod +x "$TARGET_DIR/scripts/git-memory-manager.py"

# 3. 创建配置
echo "   ⚙️  创建配置文件..."
cp "$SCRIPT_DIR/templates/.gitmemory-config.json" "$TARGET_DIR/.gitmemory-config.json"

# 4. 创建 .gitignore
echo "   🚫 创建 .gitignore..."
cp "$SCRIPT_DIR/templates/.gitignore" "$TARGET_DIR/.gitignore"

# 5. 创建目录结构
echo "   📁 创建目录结构..."
mkdir -p "$TARGET_DIR/memory/daily"
mkdir -p "$TARGET_DIR/memory/topics"
mkdir -p "$TARGET_DIR/memory/search-index"
mkdir -p "$TARGET_DIR/projects"

# 6. 创建初始记忆文件
echo "   📝 创建记忆文件..."
cat > "$TARGET_DIR/memory/INDEX.md" << 'EOF'
# 📋 记忆索引

**创建日期**: $(date +%Y-%m-%d)

## 目录结构
- `daily/` - 每日记忆
- `topics/` - 主题分类记忆
- `search-index/` - 搜索索引

## 快速搜索
```bash
# 关键词搜索
python3 scripts/git-memory-search.py keyword "关键词"

# 提交搜索
python3 scripts/git-memory-search.py commit "提交关键词"

# 时间搜索
python3 scripts/git-memory-search.py time --since="2026-04-20"
```
EOF

# 7. 创建项目索引
echo "   📊 创建项目索引..."
cat > "$TARGET_DIR/projects/INDEX.md" << 'EOF'
# 📋 项目索引

**创建日期**: $(date +%Y-%m-%d)

## 进行中项目
| 项目 | 目录 | 状态 |
|------|------|------|
| (添加项目) | `(project-name/)` | 🟡 进行中 |

## 检索项目
```bash
ls projects/
git ls-files projects/
git grep -l "关键词" projects/
```
EOF

# 8. 首次提交
echo "   📸 首次提交..."
cd "$TARGET_DIR"
git add .
git commit -m "初始化: Git 记忆系统 - 搜索、管理、快照" 2>/dev/null || true

# 9. 显示安装结果
echo ""
echo "✅ Git 记忆系统安装完成！"
echo ""
echo "📚 快速开始:"
echo "   python3 scripts/git-memory-search.py keyword \"你的关键词\""
echo "   python3 scripts/git-memory-manager.py status"
echo "   python3 scripts/git-memory-manager.py commit -m \"描述\""
echo ""
echo "📁 目录结构:"
echo "   memory/          ← 记忆目录"
echo "   projects/        ← 项目目录"
echo "   scripts/         ← 工具脚本"
echo ""
echo "🔍 搜索示例:"
echo "   git-memory-search.py keyword \"关键词\""
echo "   git-memory-search.py commit \"提交关键词\""
echo "   git-memory-search.py time --since=\"2026-04-20\""
echo ""
