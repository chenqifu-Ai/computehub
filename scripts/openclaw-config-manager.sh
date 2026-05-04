#!/bin/bash

# OpenClaw 配置管理脚本
# 作者: 小智
# 日期: 2026-03-24

CONFIG_DIR="/root/.openclaw"
CONFIG_FILE="$CONFIG_DIR/openclaw.json"
BACKUP_DIR="$CONFIG_DIR/backups"
WORKSPACE_BACKUP_DIR="/root/.openclaw/workspace/config/backups"

# 创建备份目录
mkdir -p "$BACKUP_DIR" "$WORKSPACE_BACKUP_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}💡 $1${NC}"
}

# 备份配置
backup_config() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/openclaw_backup_${timestamp}.json"
    local workspace_backup="$WORKSPACE_BACKUP_DIR/openclaw_backup_${timestamp}.json"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi
    
    # 创建备份
    cp "$CONFIG_FILE" "$backup_file"
    cp "$CONFIG_FILE" "$workspace_backup"
    
    # 清理旧备份（保留最近10个）
    ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null
    
    print_status "配置已备份到:"
    print_info "  $backup_file"
    print_info "  $workspace_backup"
    
    # 显示最近的备份
    print_info "最近5个备份:"
    ls -lt "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null | head -5 | awk '{print "  " $6 " " $7 " " $9}'
}

# 列出所有备份
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

# 恢复指定备份
restore_backup() {
    local backup_number=$1
    
    if [ -z "$backup_number" ]; then
        print_error "请指定要恢复的备份序号"
        list_backups
        return 1
    fi
    
    # 获取备份文件列表
    local backups=($(ls -t "$BACKUP_DIR"/openclaw_backup_*.json 2>/dev/null))
    
    if [ ${#backups[@]} -eq 0 ]; then
        print_error "没有找到备份文件"
        return 1
    fi
    
    if [ "$backup_number" -lt 1 ] || [ "$backup_number" -gt ${#backups[@]} ]; then
        print_error "无效的备份序号: $backup_number (有效范围: 1-${#backups[@]})"
        return 1
    fi
    
    local selected_backup="${backups[$((backup_number-1))]}"
    local current_backup="$CONFIG_FILE.bak.$(date +%s)"
    
    # 备份当前配置
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "$current_backup"
        print_info "当前配置已备份到: $current_backup"
    fi
    
    # 恢复选中的备份
    cp "$selected_backup" "$CONFIG_FILE"
    
    print_status "配置已恢复到: $(basename "$selected_backup")"
    print_info "重启 OpenClaw 以应用新配置"
}

# 验证配置文件
validate_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi
    
    # 使用 Python 验证 JSON 格式
    if python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
        print_status "配置文件格式正确"
        
        # 检查关键字段
        local default_model=$(python3 -c "
import json
config = json.load(open('$CONFIG_FILE'))
print(config.get('agents', {}).get('defaults', {}).get('model', {}).get('primary', 'N/A'))
" 2>/dev/null)
        
        if [ "$default_model" != "N/A" ]; then
            print_info "默认模型: $default_model"
        else
            print_warning "未找到默认模型配置"
        fi
        
        local provider_count=$(python3 -c "
import json
config = json.load(open('$CONFIG_FILE'))
print(len(config.get('models', {}).get('providers', {})))
" 2>/dev/null)
        
        print_info "Provider 数量: $provider_count"
    else
        print_error "配置文件 JSON 格式错误"
        return 1
    fi
}

# 显示帮助
show_help() {
    echo "OpenClaw 配置管理工具"
    echo ""
    echo "用法: $0 <命令>"
    echo ""
    echo "命令:"
    echo "  backup     - 备份当前配置"
    echo "  list       - 列出所有备份"
    echo "  restore N  - 恢复第 N 个备份"
    echo "  validate   - 验证当前配置"
    echo "  help       - 显示此帮助"
    echo ""
    echo "示例:"
    echo "  $0 backup          # 备份配置"
    echo "  $0 list            # 查看备份列表"  
    echo "  $0 restore 1       # 恢复最新的备份"
    echo "  $0 validate        # 验证配置是否正确"
}

# 主程序
case "${1:-help}" in
    backup)
        backup_config
        ;;
    list)
        list_backups
        ;;
    restore)
        restore_backup "$2"
        ;;
    validate)
        validate_config
        ;;
    help)
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac