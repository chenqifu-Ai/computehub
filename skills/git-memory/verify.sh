#!/bin/bash
# Git 记忆系统安装验证脚本
# 使用: bash verify.sh [目标目录]

TARGET_DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔍 验证 Git 记忆系统..."
echo ""

ERRORS=0

# 检查 git 仓库
if [ -d "$TARGET_DIR/.git" ]; then
    echo "✅ Git 仓库存在"
else
    echo "❌ Git 仓库不存在"
    ERRORS=$((ERRORS + 1))
fi

# 检查工具脚本
for script in git-memory-search.py git-memory-manager.py; do
    if [ -f "$TARGET_DIR/scripts/$script" ]; then
        echo "✅ $script 存在"
    else
        echo "❌ $script 不存在"
        ERRORS=$((ERRORS + 1))
    fi
done

# 检查配置文件
if [ -f "$TARGET_DIR/.gitmemory-config.json" ]; then
    echo "✅ 配置文件存在"
else
    echo "❌ 配置文件不存在"
    ERRORS=$((ERRORS + 1))
fi

# 检查 .gitignore
if [ -f "$TARGET_DIR/.gitignore" ]; then
    echo "✅ .gitignore 存在"
else
    echo "❌ .gitignore 不存在"
    ERRORS=$((ERRORS + 1))
fi

# 检查目录结构
for dir in memory/daily memory/topics projects; do
    if [ -d "$TARGET_DIR/$dir" ]; then
        echo "✅ 目录 $dir 存在"
    else
        echo "❌ 目录 $dir 不存在"
        ERRORS=$((ERRORS + 1))
    fi
done

# 测试搜索功能
echo ""
echo "🧪 测试搜索功能..."
if python3 "$TARGET_DIR/scripts/git-memory-search.py" keyword "初始化" 2>/dev/null | grep -q "初始化"; then
    echo "✅ 搜索功能正常"
else
    echo "⚠️  搜索功能需要更多数据"
fi

# 显示状态
echo ""
echo "📊 系统状态:"
cd "$TARGET_DIR"
git status --short | wc -l | xargs -I{} echo "   未提交文件: {} 个"
git log --oneline | wc -l | xargs -I{} echo "   提交总数: {} 个"

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ 验证通过！Git 记忆系统就绪。"
    exit 0
else
    echo "❌ 验证失败，有 $ERRORS 个错误。"
    exit 1
fi
