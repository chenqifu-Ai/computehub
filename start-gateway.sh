#!/bin/bash
# ComputeHub v3.0 - Gateway 生命周期管理
# 基于 OpenPC 工程规范

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="${PROJECT_DIR}/bin/computehub-gateway"
PID_FILE="${PROJECT_DIR}/gateway.pid"
LOG_FILE="${PROJECT_DIR}/gateway.log"
CONFIG_FILE="${PROJECT_DIR}/config.json"

log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] $*"
}

check_binary() {
    if [ ! -f "${BINARY}" ]; then
        log "⚠️  Binary not found, building..."
        bash "${PROJECT_DIR}/build.sh build"
    fi
}

start() {
    check_binary
    
    if [ -f "${PID_FILE}" ]; then
        local old_pid=$(cat "${PID_FILE}")
        if kill -0 "${old_pid}" 2>/dev/null; then
            log "📌 Gateway already running (PID: ${old_pid})"
            return 0
        else
            rm -f "${PID_FILE}"
        fi
    fi
    
    log "🚀 Starting ComputeHub Gateway..."
    nohup ${BINARY} serve >> "${LOG_FILE}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${PID_FILE}"
    
    # 等待启动
    sleep 2
    if kill -0 "${pid}" 2>/dev/null; then
        log "✅ Gateway started (PID: ${pid})"
        log "   Config: ${CONFIG_FILE}"
        log "   Log: ${LOG_FILE}"
    else
        log "❌ Gateway failed to start. Check: ${LOG_FILE}"
        rm -f "${PID_FILE}"
        return 1
    fi
}

stop() {
    if [ ! -f "${PID_FILE}" ]; then
        log "⚠️  No PID file found. Gateway may not be running."
        return 0
    fi
    
    local pid=$(cat "${PID_FILE}")
    if kill -0 "${pid}" 2>/dev/null; then
        log "📴 Stopping Gateway (PID: ${pid})..."
        kill "${pid}"
        sleep 2
        
        # 优雅停止超时后强制
        if kill -0 "${pid}" 2>/dev/null; then
            log "⏱  Force killing..."
            kill -9 "${pid}" 2>/dev/null || true
        fi
        
        log "✅ Gateway stopped."
        rm -f "${PID_FILE}"
    else
        log "⚠️  Gateway not running (stale PID file removed)."
        rm -f "${PID_FILE}"
    fi
}

restart() {
    log "🔄 Restarting Gateway..."
    stop
    sleep 1
    start
}

status() {
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            log "🟢 Gateway running (PID: ${pid})"
            return 0
        else
            log "🔴 Gateway not running (stale PID file)"
            rm -f "${PID_FILE}"
            return 1
        fi
    else
        log "🔴 Gateway not running"
        return 1
    fi
}

health() {
    local port=8282
    log "🩺 Health check..."
    local response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/api/health" 2>/dev/null || echo "000")
    if [ "${response}" = "200" ]; then
        log "✅ Gateway healthy (HTTP ${response})"
        curl -s "http://localhost:${port}/api/health" | python3 -m json.tool 2>/dev/null || true
    else
        log "❌ Gateway not healthy (HTTP ${response})"
        return 1
    fi
}

logs() {
    if [ -f "${LOG_FILE}" ]; then
        tail -20 "${LOG_FILE}"
    else
        log "⚠️  Log file not found: ${LOG_FILE}"
    fi
}

case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    health)
        health
        ;;
    logs)
        logs
        ;;
    help)
        echo "Usage: ./start-gateway.sh [start|stop|restart|status|health|logs|help]"
        echo ""
        echo "  start    Start the gateway"
        echo "  stop     Stop the gateway"
        echo "  restart  Restart the gateway"
        echo "  status   Show gateway status"
        echo "  health   Health check via API"
        echo "  logs     Show last 20 log lines"
        echo "  help     Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac
