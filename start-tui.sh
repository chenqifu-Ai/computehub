#!/bin/bash
# ComputeHub v3.0 - TUI 生命周期管理
# 基于 OpenPC 工程规范

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="${PROJECT_DIR}/bin/computehub-tui"
PID_FILE="${PROJECT_DIR}/tui.pid"
LOG_FILE="${PROJECT_DIR}/tui.log"

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
    
    log "🚀 Starting ComputeHub TUI..."
    log "   (Press Ctrl+C to exit)"
    echo ""
    ${BINARY}
}

stop() {
    if [ ! -f "${PID_FILE}" ]; then
        log "⚠️  No PID file found."
        return 0
    fi
    
    local pid=$(cat "${PID_FILE}")
    if kill -0 "${pid}" 2>/dev/null; then
        log "📴 Stopping TUI (PID: ${pid})..."
        kill "${pid}" 2>/dev/null || true
        rm -f "${PID_FILE}"
        log "✅ TUI stopped."
    else
        log "⚠️  TUI not running (stale PID file)."
        rm -f "${PID_FILE}"
    fi
}

status() {
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            log "🟢 TUI running (PID: ${pid})"
            return 0
        else
            log "🔴 TUI not running (stale PID file)"
            rm -f "${PID_FILE}"
            return 1
        fi
    else
        log "🔴 TUI not running"
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
    status)
        status
        ;;
    logs)
        logs
        ;;
    help)
        echo "Usage: ./start-tui.sh [start|stop|status|logs|help]"
        echo ""
        echo "  start    Start the TUI (interactive)"
        echo "  stop     Stop the TUI"
        echo "  status   Show TUI status"
        echo "  logs     Show last 20 log lines"
        echo "  help     Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac
