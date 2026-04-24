#!/bin/bash
# Ollama Router - 自动切换脚本
# 监控Ollama服务状态，主服务器掉线时自动切换到备用服务器

set -e

# 配置
PRIMARY_HOST="192.168.1.7"
PRIMARY_PORT="11434"
BACKUP_HOST="ollama.com"  # 官方云端API作为备用
BACKUP_PORT="443"  # HTTPS端口
BACKUP_PROTO="https"  # 使用HTTPS
LOG_FILE="/var/log/ollama-router.log"
PID_FILE="/var/run/ollama-router.pid"
CHECK_INTERVAL=10  # 检查间隔（秒）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# 检查Ollama服务是否可用
check_ollama() {
    local host=$1
    local port=$2
    
    if curl -s "http://${host}:${port}/api/tags" --connect-timeout 3 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取可用模型列表
get_models() {
    local host=$1
    local port=$2
    
    curl -s "http://${host}:${port}/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "无法获取模型列表"
}

# 测试模型生成
test_model() {
    local host=$1
    local port=$2
    local model=$3
    
    curl -s "http://${host}:${port}/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"${model}\",\"prompt\":\"hi\",\"stream\":false}" \
        --connect-timeout 5 \
        -w "\nHTTP_CODE:%{http_code}" 2>/dev/null | grep "HTTP_CODE:200" >/dev/null
}

# 主循环
main_loop() {
    local current_host=$PRIMARY_HOST
    local current_port=$PRIMARY_PORT
    local switched=false
    
    log_info "Ollama Router 启动"
    log_info "主服务器: ${PRIMARY_HOST}:${PRIMARY_PORT}"
    log_info "备用服务器: ${BACKUP_HOST}:${BACKUP_PORT}"
    log_info "检查间隔: ${CHECK_INTERVAL}秒"
    
    while true; do
        # 检查当前服务器
        if check_ollama "$current_host" "$current_port"; then
            if [ "$switched" = true ]; then
                log_info "✅ 当前服务器 ${current_host}:${current_port} 恢复正常"
                switched=false
            fi
            log "心跳检测: ${current_host}:${current_port} - 正常"
        else
            log_error "❌ 当前服务器 ${current_host}:${current_port} 无响应"
            
            # 尝试切换到备用服务器
            if [ "$current_host" = "$PRIMARY_HOST" ]; then
                log_warn "🔄 尝试切换到备用服务器 ${BACKUP_HOST}:${BACKUP_PORT}"
                if check_ollama "$BACKUP_HOST" "$BACKUP_PORT"; then
                    current_host=$BACKUP_HOST
                    current_port=$BACKUP_PORT
                    switched=true
                    log_info "✅ 已切换到备用服务器 ${BACKUP_HOST}:${BACKUP_PORT}"
                    log_info "可用模型: $(get_models "$current_host" "$current_port" | head -5 | tr '\n' ', ')"
                else
                    log_error "❌ 备用服务器也不可用"
                fi
            else
                # 已经在备用服务器，尝试切回主服务器
                log_warn "🔄 尝试切回主服务器 ${PRIMARY_HOST}:${PRIMARY_PORT}"
                if check_ollama "$PRIMARY_HOST" "$PRIMARY_PORT"; then
                    current_host=$PRIMARY_HOST
                    current_port=$PRIMARY_PORT
                    switched=true
                    log_info "✅ 已切回主服务器 ${PRIMARY_HOST}:${PRIMARY_PORT}"
                else
                    log_error "❌ 主服务器仍不可用，继续使用备用服务器"
                fi
            fi
        fi
        
        # 显示当前状态
        echo ""
        echo "========================================"
        echo "当前活跃服务器: ${current_host}:${current_port}"
        echo "========================================"
        
        sleep $CHECK_INTERVAL
    done
}

# 一键测试所有服务器
test_all() {
    echo "🧪 测试所有Ollama服务器"
    echo "========================================"
    
    # 测试主服务器
    echo -n "主服务器 ${PRIMARY_HOST}:${PRIMARY_PORT} ... "
    if check_ollama "$PRIMARY_HOST" "$PRIMARY_PORT"; then
        echo -e "${GREEN}✅ 正常${NC}"
        echo "可用模型:"
        get_models "$PRIMARY_HOST" "$PRIMARY_PORT" | head -10 | sed 's/^/  - /'
    else
        echo -e "${RED}❌ 不可用${NC}"
    fi
    
    echo ""
    
    # 测试备用服务器
    echo -n "备用服务器 ${BACKUP_HOST}:${BACKUP_PORT} ... "
    if check_ollama "$BACKUP_HOST" "$BACKUP_PORT"; then
        echo -e "${GREEN}✅ 正常${NC}"
        echo "可用模型:"
        get_models "$BACKUP_HOST" "$BACKUP_PORT" | head -10 | sed 's/^/  - /'
    else
        echo -e "${RED}❌ 不可用${NC}"
    fi
}

# 显示状态
show_status() {
    echo "📊 Ollama Router 状态"
    echo "========================================"
    echo "主服务器: ${PRIMARY_HOST}:${PRIMARY_PORT}"
    echo "备用服务器: ${BACKUP_HOST}:${BACKUP_PORT}"
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

# 帮助信息
show_help() {
    cat << EOF
Ollama Router - 自动切换脚本

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
    编辑脚本修改 PRIMARY_HOST, BACKUP_HOST 等变量

示例:
    $0 start     # 后台启动监控
    $0 test      # 测试服务器连通性
    $0 status    # 查看运行状态

日志:
    tail -f $LOG_FILE

EOF
}

# 命令行处理
case "${1:-run}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 1
        start_service
        ;;
    status)
        show_status
        ;;
    test)
        test_all
        ;;
    run)
        main_loop
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac