#!/bin/bash
# Ollama Router - 自动切换脚本 (支持API Key认证)
# 监控Ollama服务状态，主服务器掉线时自动切换到备用服务器
# 备用服务器运行时，定期检查主服务器是否恢复

set -e

# 配置
PRIMARY_HOST="192.168.1.7"
PRIMARY_PORT="11434"
PRIMARY_PROTO="http"
PRIMARY_KEY=""  # 本地无需API Key

BACKUP_HOST="ollama.com"
BACKUP_PORT="443"
BACKUP_PROTO="https"
BACKUP_KEY="c9fc9f"  # API Key

LOG_FILE="/var/log/ollama-router.log"
PID_FILE="/var/run/ollama/router.pid"
CHECK_INTERVAL=10

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
log_info() { echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

# 检查服务是否可用
check_server() {
    local host=$1
    local port=$2
    local proto=$3
    local key=$4
    
    local url
    
    if [ "$proto" = "https" ]; then
        url="https://${host}/api/tags"
    else
        url="http://${host}:${port}/api/tags"
    fi
    
    if [ -n "$key" ]; then
        curl -sk "$url" -H "Authorization: Bearer $key" --connect-timeout 5 -o /dev/null 2>/dev/null
    else
        curl -s "$url" --connect-timeout 3 -o /dev/null 2>/dev/null
    fi
}

# 获取URL
get_url() {
    local host=$1
    local port=$2
    local proto=$3
    
    if [ "$proto" = "https" ]; then
        echo "https://${host}"
    else
        echo "http://${host}:${port}"
    fi
}

# 主循环
main_loop() {
    local current_host=$PRIMARY_HOST
    local current_port=$PRIMARY_PORT
    local current_proto=$PRIMARY_PROTO
    local current_key=$PRIMARY_KEY
    local check_primary_counter=0
    
    log_info "Ollama Router 启动"
    log_info "主服务器: ${PRIMARY_PROTO}://${PRIMARY_HOST}:${PRIMARY_PORT}"
    log_info "备用服务器: ${BACKUP_PROTO}://${BACKUP_HOST} (带认证)"
    log_info "检查间隔: ${CHECK_INTERVAL}秒"
    
    while true; do
        # 检查当前服务器
        if check_server "$current_host" "$current_port" "$current_proto" "$current_key"; then
            log "心跳检测: $(get_url "$current_host" "$current_port" "$current_proto") - 正常"
            
            # 如果在备用服务器，定期检查主服务器是否恢复
            if [ "$current_host" = "$BACKUP_HOST" ]; then
                check_primary_counter=$((check_primary_counter + 1))
                if [ $check_primary_counter -ge 3 ]; then
                    check_primary_counter=0
                    log "检查主服务器状态..."
                    if check_server "$PRIMARY_HOST" "$PRIMARY_PORT" "$PRIMARY_PROTO" "$PRIMARY_KEY"; then
                        log_warn "🔄 主服务器已恢复，切回: ${PRIMARY_PROTO}://${PRIMARY_HOST}:${PRIMARY_PORT}"
                        current_host=$PRIMARY_HOST
                        current_port=$PRIMARY_PORT
                        current_proto=$PRIMARY_PROTO
                        current_key=$PRIMARY_KEY
                        log_info "✅ 已切回主服务器"
                    else
                        log "主服务器仍不可用，继续使用备用服务器"
                    fi
                fi
            fi
        else
            log_error "❌ 当前服务器无响应: $(get_url "$current_host" "$current_port" "$current_proto")"
            
            # 尝试切换
            if [ "$current_host" = "$PRIMARY_HOST" ]; then
                # 主服务器挂了，切到备用
                log_warn "🔄 切换到备用服务器: ${BACKUP_PROTO}://${BACKUP_HOST}"
                if check_server "$BACKUP_HOST" "$BACKUP_PORT" "$BACKUP_PROTO" "$BACKUP_KEY"; then
                    current_host=$BACKUP_HOST
                    current_port=$BACKUP_PORT
                    current_proto=$BACKUP_PROTO
                    current_key=$BACKUP_KEY
                    check_primary_counter=0
                    log_info "✅ 已切换到备用服务器 (带API Key认证)"
                else
                    log_error "❌ 备用服务器也不可用"
                fi
            else
                # 备用也挂了，尝试切回主服务器
                log_warn "🔄 尝试切回主服务器: ${PRIMARY_PROTO}://${PRIMARY_HOST}:${PRIMARY_PORT}"
                if check_server "$PRIMARY_HOST" "$PRIMARY_PORT" "$PRIMARY_PROTO" "$PRIMARY_KEY"; then
                    current_host=$PRIMARY_HOST
                    current_port=$PRIMARY_PORT
                    current_proto=$PRIMARY_PROTO
                    current_key=$PRIMARY_KEY
                    log_info "✅ 已切回主服务器"
                else
                    log_error "❌ 主服务器仍不可用，继续使用备用服务器"
                fi
            fi
        fi
        
        echo ""
        echo "========================================"
        echo "当前活跃服务器: $(get_url "$current_host" "$current_port" "$current_proto")"
        [ "$current_host" = "$BACKUP_HOST" ] && echo "(使用API Key认证)"
        echo "========================================"
        
        sleep $CHECK_INTERVAL
    done
}

# 测试所有服务器
test_all() {
    echo "🧪 测试所有Ollama服务器"
    echo "========================================"
    
    # 主服务器
    echo -n "主服务器 ${PRIMARY_PROTO}://${PRIMARY_HOST}:${PRIMARY_PORT} ... "
    if check_server "$PRIMARY_HOST" "$PRIMARY_PORT" "$PRIMARY_PROTO" "$PRIMARY_KEY"; then
        echo -e "${GREEN}✅ 正常${NC}"
    else
        echo -e "${RED}❌ 不可用${NC}"
    fi
    
    # 备用服务器
    echo -n "备用服务器 ${BACKUP_PROTO}://${BACKUP_HOST} (API Key认证) ... "
    if check_server "$BACKUP_HOST" "$BACKUP_PORT" "$BACKUP_PROTO" "$BACKUP_KEY"; then
        echo -e "${GREEN}✅ 正常${NC}"
    else
        echo -e "${RED}❌ 不可用${NC}"
    fi
}

# 显示状态
show_status() {
    echo "📊 Ollama Router 状态"
    echo "========================================"
    echo "主服务器: ${PRIMARY_PROTO}://${PRIMARY_HOST}:${PRIMARY_PORT} (无需认证)"
    echo "备用服务器: ${BACKUP_PROTO}://${BACKUP_HOST} (API Key认证)"
    echo "日志文件: ${LOG_FILE}"
    echo ""
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "状态: ${GREEN}运行中${NC} (PID: $PID)"
        else
            echo -e "状态: ${RED}已停止${NC}"
        fi
    else
        echo -e "状态: ${RED}未运行${NC}"
    fi
}

# 启动服务
start_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warn "服务已经在运行 (PID: $PID)"
            exit 0
        fi
    fi
    
    log_info "启动 Ollama Router 服务"
    nohup bash "$0" run > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    log_info "服务已启动 (PID: $!)"
}

# 停止服务
stop_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            rm -f "$PID_FILE"
            log_info "服务已停止"
        else
            log_warn "服务未运行"
            rm -f "$PID_FILE"
        fi
    else
        log_warn "PID文件不存在"
    fi
}

# 帮助
show_help() {
    cat << EOF
Ollama Router - 自动切换脚本 (支持API Key认证)

用法: $0 [命令]

命令:
    start       启动监控服务
    stop        停止监控服务
    restart     重启服务
    status      查看状态
    test        测试所有服务器
    run         运行主循环（前台）
    help        显示帮助

配置:
    主服务器: ${PRIMARY_PROTO}://${PRIMARY_HOST}:${PRIMARY_PORT} (无需认证)
    备用服务器: ${BACKUP_PROTO}://${BACKUP_HOST} (API Key认证)

特性:
    - 主服务器掉线自动切换到备用
    - 备用运行时每30秒检查主服务器是否恢复
    - 主服务器恢复后自动切回

示例:
    $0 start     # 后台启动监控
    $0 test      # 测试服务器连通性
    $0 status    # 查看运行状态

EOF
}

# 命令处理
case "${1:-run}" in
    start) start_service ;;
    stop) stop_service ;;
    restart) stop_service; sleep 1; start_service ;;
    status) show_status ;;
    test) test_all ;;
    run) main_loop ;;
    help|--help|-h) show_help ;;
    *) log_error "未知命令: $1"; show_help; exit 1 ;;
esac