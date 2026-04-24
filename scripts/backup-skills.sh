#!/bin/bash
# OpenClaw技能打包脚本
# 打包所有自定义技能到单个安装包

echo "========================================"
echo "  OpenClaw 技能打包工具"
echo "========================================"
echo ""

# 设置输出目录
OUTPUT_DIR="/sdcard/openclaw-backup"
mkdir -p "$OUTPUT_DIR"

# 时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="openclaw-skills-${TIMESTAMP}"

echo "📦 打包内容："
echo ""

# 1. 用户自定义技能
echo "1. 用户技能 (workspace/skills/)"
echo "   - CEO战略顾问"
echo "   - 财务顾问"
echo "   - 财务专家"
echo "   - HR专家"
echo "   - 法律顾问"
echo "   - 营销专家"
echo "   - 网络专家"
echo "   - 安全专家"
echo "   - 小爱老师"
echo "   - 网页自动化"
echo ""

# 2. 配置文件
echo "2. 配置文件"
echo "   - MEMORY.md (长期记忆)"
echo "   - USER.md (用户信息)"
echo "   - IDENTITY.md (身份配置)"
echo "   - SOUL.md (性格配置)"
echo "   - TOOLS.md (本地工具配置)"
echo "   - AGENTS.md (代理配置)"
echo ""

# 3. 学习记录
echo "3. 学习记录"
echo "   - memory/ 目录下所有学习文件"
echo ""

# 创建临时目录
TEMP_DIR="/tmp/openclaw-package"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR/openclaw-skills"

# 复制技能文件
cp -r /root/.openclaw/workspace/skills/* "$TEMP_DIR/openclaw-skills/" 2>/dev/null

# 复制配置文件
cp /root/.openclaw/workspace/MEMORY.md "$TEMP_DIR/" 2>/dev/null
cp /root/.openclaw/workspace/USER.md "$TEMP_DIR/" 2>/dev/null
cp /root/.openclaw/workspace/IDENTITY.md "$TEMP_DIR/" 2>/dev/null
cp /root/.openclaw/workspace/SOUL.md "$TEMP_DIR/" 2>/dev/null
cp /root/.openclaw/workspace/TOOLS.md "$TEMP_DIR/" 2>/dev/null
cp /root/.openclaw/workspace/AGENTS.md "$TEMP_DIR/" 2>/dev/null

# 复制学习记录
cp -r /root/.openclaw/workspace/memory "$TEMP_DIR/" 2>/dev/null

# 创建安装说明
cat > "$TEMP_DIR/README.txt" << 'EOF'
=====================================
  OpenClaw 技能包安装说明
=====================================

安装步骤：

1. 解压文件
   tar -xzf openclaw-skills.tar.gz

2. 复制技能到新设备
   将 openclaw-skills/ 目录复制到：
   /root/.openclaw/workspace/skills/

3. 复制配置文件
   将以下文件复制到：
   /root/.openclaw/workspace/

4. 复制学习记录
   将 memory/ 目录复制到：
   /root/.openclaw/workspace/memory/

目录结构：
├── openclaw-skills/    # 技能文件
│   ├── ceo-advisor/
│   ├── finance-advisor/
│   ├── finance-expert/
│   ├── hr-expert/
│   ├── legal-advisor/
│   ├── marketing-expert/
│   ├── network-expert/
│   ├── security-expert/
│   ├── xiaoh-teacher/
│   └── web-automation/
├── MEMORY.md
├── USER.md
├── IDENTITY.md
├── SOUL.md
├── TOOLS.md
├── AGENTS.md
└── memory/             # 学习记录

注意事项：
- 确保目标设备已安装 OpenClaw
- 系统内置技能（如 healthcheck, tmux 等）无需迁移
- 如有冲突，可选择覆盖或保留原文件

=====================================
EOF

# 打包
cd "$TEMP_DIR"
tar -czf "${PACKAGE_NAME}.tar.gz" *

# 移动到输出目录
mv "${PACKAGE_NAME}.tar.gz" "$OUTPUT_DIR/"

# 计算大小
SIZE=$(du -h "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" | cut -f1)

echo "========================================"
echo "✅ 打包完成！"
echo "========================================"
echo ""
echo "📦 文件：$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"
echo "📊 大小：$SIZE"
echo ""
echo "📋 包含内容："
echo "   - 用户自定义技能 (11个)"
echo "   - 配置文件 (6个)"
echo "   - 学习记录 (memory/)"
echo ""
echo "📱 迁移方法："
echo "   1. 将文件传输到新设备"
echo "   2. 解压：tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "   3. 复制到相应目录"
echo ""

# 清理
rm -rf "$TEMP_DIR"

echo "========================================"
echo "  传输文件位置："
echo "  $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"
echo "========================================"