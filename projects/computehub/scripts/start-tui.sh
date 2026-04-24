#!/bin/bash

# OpenPC TUI 启动脚本
# 版本: 1.0
# 描述: 自动启动OpenPC TUI客户端

set -e

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUI_BINARY="$SCRIPT_DIR/opc-tui"
CONFIG_FILE="$SCRIPT_DIR/config.json"
LOG_FILE="$SCRIPT_DIR/tui.log"
PID_FILE="$SCRIPT_DIR/tui.pid"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 错误处理
error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# 检查依赖
check_dependencies() {
    if [ ! -f "$TUI_BINARY" ]; then
        error "TUI二进制文件不存在: $TUI_BINARY"
    fi
    
    if [ ! -x "$TUI_BINARY" ]; then
        chmod +x "$TUI_BINARY"
    fi
}

# 获取网关端口
get_gateway_port() {
    if [ -f "$CONFIG_FILE" ]; then
        local port=$(grep -o '"port":[[:space:]]*[0-9]*' "$CONFIG_FILE" | grep -o '[0-9]*' | head -1)
        if [ -n "$port" ]; then
            echo "$port"
            return
        fi
    fi
    echo "8181"  # 默认端口
}

# 检查网关服务是否运行
check_gateway_health() {
    local port=$1
    local max_retries=10
    local retry_interval=1
    
    for i in $(seq 1 $max_retries); do
        if curl -s "http://localhost:$port/api/health" >/dev/null 2>&1; then
            return 0
        fi
        sleep $retry_interval
    done
    
    return 1
}

# 停止服务
stop_service() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "停止运行中的TUI服务 (PID: $pid)"
            kill "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid"
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # 额外清理可能存在的进程
    pkill -f "opc-tui" 2>/dev/null || true
}

# 启动服务
start_service() {
    local port=$(get_gateway_port)
    
    log "检查网关服务是否可用 (端口: $port)..."
    if ! check_gateway_health "$port"; then
        error "网关服务未运行或不可用，请先启动网关服务"
    fi
    
    log "启动 OpenPC TUI 客户端..."
    log "网关地址: http://localhost:$port"
    log "日志文件: $LOG_FILE"
    
    # 启动TUI
    nohup "$TUI_BINARY" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    log "TUI启动中 (PID: $pid)..."
    sleep 2
    
    # 检查服务是否启动成功
    if ! kill -0 "$pid" 2>/dev/null; then
        error "TUI启动失败，请检查日志: $LOG_FILE"
    fi
    
    log "TUI启动成功!"
    log "PID: $pid"
    log "查看日志: tail -f $LOG_FILE"
}

# 显示服务状态
show_status() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            local port=$(get_gateway_port)
            log "TUI运行中 (PID: $pid)"
            log "网关端口: $port"
            log "启动时间: $(ps -p $pid -o lstart=)"
            return 0
        else
            log "PID文件存在但进程未运行"
            rm -f "$PID_FILE"
        fi
    fi
    
    log "TUI未运行"
    return 1
}

# 显示使用帮助
show_usage() {
    echo "OpenPC TUI 管理脚本"
    echo "用法: $0 [command]"
    echo ""
    echo "命令:"
    echo "  start     启动TUI客户端"
    echo "  stop      停止TUI客户端"
    echo "  restart   重启TUI客户端"
    echo "  status    查看TUI状态"
    echo "  logs      查看TUI日志"
    echo "  help      显示帮助信息"
    echo ""
    echo "注意: TUI需要先启动网关服务"
    echo "示例:"
    echo "  $0 start    # 启动TUI"
    echo "  $0 status   # 查看状态"
    echo "  $0 logs     # 查看日志"
}

# 查看日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "=== 最后20行日志 ==="
        tail -20 "$LOG_FILE"
    else
        log "日志文件不存在: $LOG_FILE"
    fi
}

# 主程序
case "${1:-help}" in
    start)
        check_dependencies
        stop_service
        start_service
        ;;
    stop)
        stop_service
        log "TUI服务已停止"
        ;;
    restart)
        check_dependencies
        stop_service
        start_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|*)
        show_usage
        ;;
esac

exit 0