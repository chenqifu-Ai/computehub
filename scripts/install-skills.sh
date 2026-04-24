#!/bin/bash
# OpenClaw技能安装脚本
# 在新设备上运行，一键恢复技能

echo "========================================"
echo "  OpenClaw 技能安装工具"
echo "========================================"
echo ""

# 检查是否有技能包
if [ ! -f "openclaw-skills-*.tar.gz" ]; then
    echo "❌ 错误：未找到技能包文件"
    echo "   请将 openclaw-skills-*.tar.gz 放在当前目录"
    echo ""
    exit 1
fi

# 查找技能包
SKILL_PACKAGE=$(ls openclaw-skills-*.tar.gz 2>/dev/null | head -1)

if [ -z "$SKILL_PACKAGE" ]; then
    echo "❌ 错误：未找到技能包"
    exit 1
fi

echo "📦 发现技能包：$SKILL_PACKAGE"
echo ""

# 设置安装目录
INSTALL_DIR="${OPENCLAW_HOME:-$HOME/.openclaw/workspace}"

echo "📁 安装目录：$INSTALL_DIR"
echo ""

# 确认安装
read -p "确认安装？(y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 安装已取消"
    exit 1
fi

echo ""
echo "🔧 开始安装..."
echo ""

# 解压
echo "1️⃣ 解压技能包..."
tar -xzf "$SKILL_PACKAGE" -C /tmp/

# 备份现有文件
BACKUP_DIR="$HOME/.openclaw-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "2️⃣ 备份现有文件到：$BACKUP_DIR"
cp -r "$INSTALL_DIR/skills" "$BACKUP_DIR/" 2>/dev/null
cp "$INSTALL_DIR/MEMORY.md" "$BACKUP_DIR/" 2>/dev/null
cp "$INSTALL_DIR/USER.md" "$BACKUP_DIR/" 2>/dev/null
cp "$INSTALL_DIR/IDENTITY.md" "$BACKUP_DIR/" 2>/dev/null
cp "$INSTALL_DIR/SOUL.md" "$BACKUP_DIR/" 2>/dev/null
cp "$INSTALL_DIR/TOOLS.md" "$BACKUP_DIR/" 2>/dev/null
cp "$INSTALL_DIR/AGENTS.md" "$BACKUP_DIR/" 2>/dev/null

# 安装技能
echo "3️⃣ 安装技能文件..."
cd /tmp
SKILL_DIR=$(tar -tzf "$SKILL_PACKAGE" | head -1 | cut -d'/' -f1)
if [ -d "/tmp/$SKILL_DIR/openclaw-skills" ]; then
    cp -r "/tmp/$SKILL_DIR/openclaw-skills/"* "$INSTALL_DIR/skills/" 2>/dev/null
fi

# 安装配置文件
echo "4️⃣ 安装配置文件..."
cp "/tmp/$SKILL_DIR/MEMORY.md" "$INSTALL_DIR/" 2>/dev/null
cp "/tmp/$SKILL_DIR/USER.md" "$INSTALL_DIR/" 2>/dev/null
cp "/tmp/$SKILL_DIR/IDENTITY.md" "$INSTALL_DIR/" 2>/dev/null
cp "/tmp/$SKILL_DIR/SOUL.md" "$INSTALL_DIR/" 2>/dev/null
cp "/tmp/$SKILL_DIR/TOOLS.md" "$INSTALL_DIR/" 2>/dev/null
cp "/tmp/$SKILL_DIR/AGENTS.md" "$INSTALL_DIR/" 2>/dev/null

# 安装学习记录
echo "5️⃣ 安装学习记录..."
if [ -d "/tmp/$SKILL_DIR/memory" ]; then
    mkdir -p "$INSTALL_DIR/memory"
    cp -r "/tmp/$SKILL_DIR/memory/"* "$INSTALL_DIR/memory/" 2>/dev/null
fi

# 清理临时文件
rm -rf "/tmp/$SKILL_DIR"

echo ""
echo "========================================"
echo "✅ 安装完成！"
echo "========================================"
echo ""
echo "📊 安装统计："
SKILL_COUNT=$(ls -d "$INSTALL_DIR/skills"/*/ 2>/dev/null | wc -l)
MEMORY_COUNT=$(ls "$INSTALL_DIR/memory"/*.md 2>/dev/null | wc -l)

echo "   技能数量：$SKILL_COUNT 个"
echo "   学习记录：$MEMORY_COUNT 个文件"
echo ""
echo "📝 备份位置：$BACKUP_DIR"
echo ""
echo "🔄 如需恢复，请重启 OpenClaw"
echo ""

# 显示已安装技能
echo "📚 已安装技能："
ls -d "$INSTALL_DIR/skills"/*/ 2>/dev/null | xargs -n1 basename | while read skill; do
    echo "   - $skill"
done

echo ""
echo "========================================"