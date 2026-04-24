#!/bin/bash
# 一键恢复最新备份

echo "🔄 正在恢复最新的 OpenClaw 配置..."

# 找到最新的备份
LATEST_BACKUP=$(ls -t /root/.openclaw/backups/openclaw_backup_*.json 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 没有找到备份文件"
    exit 1
fi

# 备份当前配置（如果存在）
if [ -f "/root/.openclaw/openclaw.json" ]; then
    cp "/root/.openclaw/openclaw.json" "/root/.openclaw/openclaw.json.emergency.$(date +%s)"
    echo "💾 当前配置已紧急备份"
fi

# 恢复最新备份
cp "$LATEST_BACKUP" "/root/.openclaw/openclaw.json"

echo "✅ 配置已恢复到: $(basename "$LATEST_BACKUP")"
echo "💡 请重启 OpenClaw 以应用新配置"
echo ""
echo "可用命令:"
echo "  oc-config list     # 查看所有备份"
echo "  oc-config restore N # 恢复指定备份"