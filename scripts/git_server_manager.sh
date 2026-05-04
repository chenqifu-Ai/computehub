#!/bin/bash
# Git服务器管理脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建新仓库
create_repo() {
    local repo_name="$1"
    
    if [ -z "$repo_name" ]; then
        read -p "请输入仓库名称: " repo_name
    fi
    
    if [[ ! "$repo_name" == *.git ]]; then
        repo_name="${repo_name}.git"
    fi
    
    log_info "创建仓库: $repo_name"
    
    cd /srv/git
    git init --bare "$repo_name"
    
    # 设置权限
    chmod -R 755 "$repo_name"
    
    log_info "仓库创建成功: /srv/git/$repo_name"
    echo "克隆地址: file:///srv/git/$repo_name"
}

# 列出所有仓库
list_repos() {
    log_info "Git仓库列表:"
    echo "================================"
    
    cd /srv/git
    for repo in *.git; do
        if [ -d "$repo" ]; then
            size=$(du -sh "$repo" | cut -f1)
            echo "📦 $repo ($size)"
        fi
    done
    
    echo "================================"
    echo "总仓库数: $(ls -d *.git 2>/dev/null | wc -l)"
}

# 删除仓库
delete_repo() {
    local repo_name="$1"
    
    if [ -z "$repo_name" ]; then
        read -p "请输入要删除的仓库名称: " repo_name
    fi
    
    if [[ ! "$repo_name" == *.git ]]; then
        repo_name="${repo_name}.git"
    fi
    
    if [ ! -d "/srv/git/$repo_name" ]; then
        log_error "仓库不存在: $repo_name"
        return 1
    fi
    
    read -p "确认删除仓库 $repo_name? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "取消删除"
        return
    fi
    
    log_info "删除仓库: $repo_name"
    rm -rf "/srv/git/$repo_name"
    log_info "仓库删除成功"
}

# 启动Git守护进程
start_git_daemon() {
    log_info "启动Git守护进程..."
    
    # 检查是否已运行
    if pgrep -f "git daemon" >/dev/null; then
        log_warn "Git守护进程已在运行"
        return
    fi
    
    # 启动守护进程
    git daemon --base-path=/srv/git --export-all --enable=receive-pack --reuseaddr &
    
    log_info "Git守护进程已启动"
    echo "访问地址: git://localhost/"
}

# 停止Git守护进程
stop_git_daemon() {
    log_info "停止Git守护进程..."
    
    if pgrep -f "git daemon" >/dev/null; then
        pkill -f "git daemon"
        log_info "Git守护进程已停止"
    else
        log_warn "Git守护进程未运行"
    fi
}

# 仓库状态检查
repo_status() {
    local repo_name="$1"
    
    if [ -z "$repo_name" ]; then
        read -p "请输入仓库名称: " repo_name
    fi
    
    if [[ ! "$repo_name" == *.git ]]; then
        repo_name="${repo_name}.git"
    fi
    
    if [ ! -d "/srv/git/$repo_name" ]; then
        log_error "仓库不存在: $repo_name"
        return 1
    fi
    
    log_info "仓库状态: $repo_name"
    echo "================================"
    
    # 检查仓库大小
    size=$(du -sh "/srv/git/$repo_name" | cut -f1)
    echo "📊 大小: $size"
    
    # 检查分支信息
    cd "/srv/git/$repo_name"
    branches=$(git branch -a | wc -l)
    echo "🌿 分支数: $branches"
    
    # 检查最近提交
    latest_commit=$(git log --oneline -1 2>/dev/null || echo "无提交记录")
    echo "📝 最新提交: $latest_commit"
    
    echo "================================"
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}Git服务器管理脚本${NC}"
    echo "================================"
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  create [名称]   创建新仓库"
    echo "  list            列出所有仓库"
    echo "  delete [名称]   删除仓库"
    echo "  start           启动Git守护进程"
    echo "  stop            停止Git守护进程"
    echo "  status [名称]   查看仓库状态"
    echo "  help            显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 create my-project"
    echo "  $0 list"
    echo "  $0 start"
    echo ""
    echo "仓库位置: /srv/git/"
}

# 主函数
main() {
    local command="$1"
    local argument="$2"
    
    case "$command" in
        "create")
            create_repo "$argument"
            ;;
        "list")
            list_repos
            ;;
        "delete")
            delete_repo "$argument"
            ;;
        "start")
            start_git_daemon
            ;;
        "stop")
            stop_git_daemon
            ;;
        "status")
            repo_status "$argument"
            ;;
        "help"|""|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"