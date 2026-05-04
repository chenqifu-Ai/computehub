#!/bin/bash

# 为红茶的 Ubuntu 虚拟机 (192.168.1.3) 完整设置 OpenClaw 配置管理

echo "🔧 开始为红茶的虚拟机 (192.168.1.3) 设置 OpenClaw 配置管理..."

# 1. 同步修复后的配置文件
echo "1️⃣ 同步修复后的配置文件..."
sshpass -p "c9fc9f,." scp /root/.openclaw/openclaw.json chen@192.168.1.3:/home/chen/.openclaw/openclaw.json

# 2. 在目标机器上创建完整的管理脚本
echo "2️⃣ 创建配置管理工具..."
sshpass -p "c9fc9f,." ssh chen@192.168.1.3 << 'EOF'
mkdir -p ~/.openclaw/workspace/scripts ~/.openclaw/backups

cat > ~/.openclaw/workspace/scripts/oc-config << 'SCRIPT_EOF'
#!/bin/bash
CONFIG_DIR="/home/chen/.openclaw"
CONFIG_FILE="$CONFIG_DIR/openclaw.json"
BACKUP_DIR="$CONFIG_DIR/backups"
WORKSPACE_BACKUP_DIR="/home/chen/.openclaw/workspace/config/backups"

mkdir -p "$BACKUP_DIR" "$WORKSPACE_BACKUP_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}💡 $1${NC}"; }

backup_config() {
    timestamp=$(date +"%Y%m%d_%H%M%S")
    backup_file="$BACKUP_DIR/openclaw_backup_${timestamp}.json"
    workspace_backup="$WORKSPACE_BACKUP_DIR/openclaw_backup_${timestamp}.json"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi
    
    cp "$CONFIG_FILE" "$backup_file"
    cp "$CONFIG_FILE" "$workspace_backup"
    ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null
    print_status "配置已备份到: $backup_file"
}

list_backups() {
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR")" ]; then
        print_warning "没有找到备份文件"
        return 0
    fi
    print_info "可用的备份列表:"
    i=1
    for backup in $(ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null); do
        if [ -f "$backup" ]; then
            basename=$(basename "$backup")
            datetime=$(echo "$basename" | sed 's/openclaw_backup_\([0-9]*\)_[0-9]*\.json/\1/')
            formatted_date=$(date -d "${datetime:0:8}" +"%Y-%m-%d")" "${datetime:8:2}:${datetime:10:2}
            printf "%-4s  %-18s  %s\n" "$i" "$formatted_date" "$basename"
            i=$((i+1))
        fi
    done
}

restore_backup() {
    backup_number=$1
    backups=($(ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null))
    
    if [ ${#backups[@]} -eq 0 ]; then
        print_error "没有找到备份文件"
        return 1
    fi
    
    if [ "$backup_number" -lt 1 ] || [ "$backup_number" -gt ${#backups[@]} ]; then
        print_error "无效的备份序号: $backup_number"
        return 1
    fi
    
    selected_backup="${backups[$((backup_number-1))]}"
    current_backup="$CONFIG_FILE.bak.$(date +%s)"
    
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
        default_model=$(python3 -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('agents',{}).get('defaults',{}).get('model',{}).get('primary','N/A'))" 2>/dev/null)
        print_info "默认模型: $default_model"
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
echo "💡 请重启 OpenClaw 以应用新配置"
RESTORE_EOF

chmod +x ~/.openclaw/workspace/scripts/oc-restore-latest.sh

# 创建别名
echo 'alias oc-config="~/.openclaw/workspace/scripts/oc-config"' >> ~/.bashrc
echo 'alias oc-restore="~/.openclaw/workspace/scripts/oc-restore-latest.sh"' >> ~/.bashrc
EOF

echo "3️⃣ 验证安装..."
sshpass -p "c9fc9f,." ssh chen@192.168.1.3 "~/.openclaw/workspace/scripts/oc-config validate"

echo ""
echo "🎉 红茶的虚拟机 (192.168.1.3) OpenClaw 配置管理设置完成！"
echo ""
echo "📋 使用方法："
echo "   oc-config backup          # 备份配置"
echo "   oc-config list            # 查看备份"
echo "   oc-config restore 1       # 恢复第1个备份"
echo "   oc-restore                # 一键恢复最新备份"
echo ""
echo "🛡️  安全保障："
echo "   - 自动保留最近10个备份"
echo "   - 一键恢复脚本"
echo "   - 配置验证功能"