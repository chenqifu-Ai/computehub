#!/bin/bash

# 同步 OpenClaw 配置管理脚本到红茶的电脑
# 目标: 192.168.1.3 (Ubuntu 虚拟机)

TARGET_HOST="192.168.1.3"
TARGET_USER="chen"
TARGET_PASS="c9fc9f,."

echo "🔄 开始同步到红茶的电脑 ($TARGET_HOST)..."

# 创建本地临时脚本
cat > /tmp/oc-sync-remote.sh << 'EOF'
#!/bin/bash
# 在目标机器上执行的脚本

echo "📦 在目标机器上设置 OpenClaw 配置管理工具..."

# 创建目录
mkdir -p ~/.openclaw/workspace/scripts

# 创建配置管理脚本
cat > ~/.openclaw/workspace/scripts/oc-config << 'SCRIPT_EOF'
#!/bin/bash
# OpenClaw 配置管理工具 - 红茶电脑版本

CONFIG_DIR="/home/chen/.openclaw"
CONFIG_FILE="$CONFIG_DIR/openclaw.json"
BACKUP_DIR="$CONFIG_DIR/backups"
WORKSPACE_BACKUP_DIR="/home/chen/.openclaw/workspace/config/backups"

# 创建备份目录
mkdir -p "$BACKUP_DIR" "$WORKSPACE_BACKUP_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}💡 $1${NC}"; }

backup_config() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/openclaw_backup_${timestamp}.json"
    local workspace_backup="$WORKSPACE_BACKUP_DIR/openclaw_backup_${timestamp}.json"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi
    
    cp "$CONFIG_FILE" "$backup_file"
    cp "$CONFIG_FILE" "$workspace_backup"
    ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null
    
    print_status "配置已备份到:"
    print_info "  $backup_file"
    print_info "  $workspace_backup"
}

list_backups() {
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR")" ]; then
        print_warning "没有找到备份文件"
        return 0
    fi
    
    print_info "可用的备份列表:"
    echo "序号  日期时间            文件名"
    echo "----  ------------------  ----------------------------------------"
    local i=1
    for backup in $(ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null); do
        if [ -f "$backup" ]; then
            local basename=$(basename "$backup")
            local datetime=$(echo "$basename" | sed 's/openclaw_backup_\([0-9]*\)_[0-9]*\.json/\1/')
            local formatted_date=$(date -d "${datetime:0:8}" +"%Y-%m-%d")" "${datetime:8:2}:${datetime:10:2}
            printf "%-4s  %-18s  %s\n" "$i" "$formatted_date" "$basename"
            i=$((i+1))
        fi
    done
}

restore_backup() {
    local backup_number=$1
    local backups=($(ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null))
    
    if [ ${#backups[@]} -eq 0 ]; then
        print_error "没有找到备份文件"
        return 1
    fi
    
    if [ "$backup_number" -lt 1 ] || [ "$backup_number" -gt ${#backups[@]} ]; then
        print_error "无效的备份序号: $backup_number"
        return 1
    fi
    
    local selected_backup="${backups[$((backup_number-1))]}"
    local current_backup="$CONFIG_FILE.bak.$(date +%s)"
    
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "$current_backup"
        print_info "当前配置已备份到: $current_backup"
    fi
    
    cp "$selected_backup" "$CONFIG_FILE"
    print_status "配置已恢复到: $(basename "$selected_backup")"
}

validate_config() {
    if python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
        print_status "配置文件格式正确"
    else
        print_error "配置文件 JSON 格式错误"
        return 1
    fi
}

case "${1:-help}" in
    backup) backup_config ;;
    list) list_backups ;;
    restore) restore_backup "$2" ;;
    validate) validate_config ;;
    help|*) 
        echo "OpenClaw 配置管理工具"
        echo "用法: $0 <命令>"
        echo "命令: backup, list, restore N, validate"
        ;;
esac
SCRIPT_EOF

chmod +x ~/.openclaw/workspace/scripts/oc-config

# 创建一键恢复脚本
cat > ~/.openclaw/workspace/scripts/oc-restore-latest.sh << 'RESTORE_EOF'
#!/bin/bash
LATEST_BACKUP=$(ls -t /home/chen/.openclaw/backups/openclaw_backup_*.json 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 没有找到备份文件"
    exit 1
fi
if [ -f "/home/chen/.openclaw/openclaw.json" ]; then
    cp "/home/chen/.openclaw/openclaw.json" "/home/chen/.openclaw/openclaw.json.emergency.$(date +%s)"
    echo "💾 当前配置已紧急备份"
fi
cp "$LATEST_BACKUP" "/home/chen/.openclaw/openclaw.json"
echo "✅ 配置已恢复到: $(basename "$LATEST_BACKUP")"
RESTORE_EOF

chmod +x ~/.openclaw/workspace/scripts/oc-restore-latest.sh

echo "✅ OpenClaw 配置管理工具已安装完成！"
echo "使用方法:"
echo "  ~/.openclaw/workspace/scripts/oc-config backup"
echo "  ~/.openclaw/workspace/scripts/oc-restore-latest.sh"
EOF

chmod +x /tmp/oc-sync-remote.sh

# 使用 sshpass 进行同步（如果可用）
if command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$TARGET_PASS" scp /tmp/oc-sync-remote.sh "$TARGET_USER@$TARGET_HOST:/tmp/"
    sshpass -p "$TARGET_PASS" ssh "$TARGET_USER@$TARGET_HOST" "bash /tmp/oc-sync-remote.sh && rm /tmp/oc-sync-remote.sh"
    rm /tmp/oc-sync-remote.sh
    echo "✅ 同步完成！"
else
    # 如果没有 sshpass，提供手动步骤
    echo "⚠️  sshpass 未安装，需要手动同步"
    echo ""
    echo "请在红茶的电脑上执行以下命令："
    echo ""
    echo "curl -s https://your-server/oc-sync-remote.sh | bash"
    echo ""
    echo "或者手动创建脚本文件。"
fi