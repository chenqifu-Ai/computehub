#!/bin/bash

# OpenPC Gateway 启动脚本
# 版本: 1.0
# 描述: 自动启动OpenPC Gateway服务

set -e

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEWAY_BINARY="$SCRIPT_DIR/opc-gateway"
CONFIG_FILE="$SCRIPT_DIR/config.json"
LOG_FILE="$SCRIPT_DIR/gateway.log"
PID_FILE="$SCRIPT_DIR/gateway.pid"
DEFAULT_PORT=8181

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 错误处理
error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

# 检查依赖
check_dependencies() {
    if ! command -v curl >/dev/null 2>&1; then
        error "curl 未安装，请先安装 curl"
    fi
    
    if [ ! -f "$GATEWAY_BINARY" ]; then
        error "网关二进制文件不存在: $GATEWAY_BINARY"
    fi
    
    if [ ! -x "$GATEWAY_BINARY" ]; then
        chmod +x "$GATEWAY_BINARY"
    fi
}

# 获取配置端口
get_config_port() {
    if [ -f "$CONFIG_FILE" ]; then
        local port=$(grep -o '"port":[[:space:]]*[0-9]*' "$CONFIG_FILE" | grep -o '[0-9]*' | head -1)
        if [ -n "$port" ]; then
            echo "$port"
            return
        fi
    fi
    echo "$DEFAULT_PORT"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if netstat -tuln | grep ":$port" >/dev/null 2>&1; then
        return 0 # 端口被占用
    else
        return 1 # 端口空闲
    fi
}

# 停止服务
stop_service() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "停止运行中的网关服务 (PID: $pid)"
            kill "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid"
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # 额外清理可能存在的进程
    pkill -f "opc-gateway" 2>/dev/null || true
}

# 启动服务
start_service() {
    local port=$(get_config_port)
    
    log "检查端口 $port 是否可用..."
    if check_port "$port"; then
        error "端口 $port 已被占用，请修改配置或停止占用进程"
    fi
    
    log "启动 OpenPC Gateway 服务..."
    log "配置文件: $CONFIG_FILE"
    log "日志文件: $LOG_FILE"
    log "监听端口: $port"
    
    # 启动服务
    nohup "$GATEWAY_BINARY" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    log "服务启动中 (PID: $pid)..."
    sleep 3
    
    # 检查服务是否启动成功
    if ! kill -0 "$pid" 2>/dev/null; then
        error "服务启动失败，请检查日志: $LOG_FILE"
    fi
    
    # 测试服务健康状态
    if check_service_health "$port"; then
        log "服务启动成功!"
        log "健康检查: http://localhost:$port/api/health"
        log "状态查询: http://localhost:$port/api/status"
        log "查看日志: tail -f $LOG_FILE"
    else
        error "服务启动但健康检查失败，请检查日志"
    fi
}

# 检查服务健康状态
check_service_health() {
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

# 显示服务状态
show_status() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            local port=$(get_config_port)
            log "服务运行中 (PID: $pid)"
            log "监听端口: $port"
            log "启动时间: $(ps -p $pid -o lstart=)"
            
            # 检查健康状态
            if check_service_health "$port"; then
                log "健康状态: 正常"
            else
                log "健康状态: 异常"
            fi
            return 0
        else
            log "${YELLOW}PID文件存在但进程未运行${NC}"
            rm -f "$PID_FILE"
        fi
    fi
    
    log "服务未运行"
    return 1
}

# 显示使用帮助
show_usage() {
    echo "OpenPC Gateway 管理脚本"
    echo "用法: $0 [command]"
    echo ""
    echo "命令:"
    echo "  start     启动网关服务"
    echo "  stop      停止网关服务"
    echo "  restart   重启网关服务"
    echo "  status    查看服务状态"
    echo "  logs      查看服务日志"
    echo "  health    检查服务健康"
    echo "  help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start    # 启动服务"
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
        log "服务已停止"
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
    health)
        port=$(get_config_port)
        if check_service_health "$port"; then
            log "服务健康检查通过"
        else
            log "服务健康检查失败"
        fi
        ;;
    help|*)
        show_usage
        ;;
esac

exit 0