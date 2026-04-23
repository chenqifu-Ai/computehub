#!/bin/bash
# ComputeHub v2.0 - Start Gateway
# Inherited from OpenPC System management pattern

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/computehub.log"
PID_FILE="$PROJECT_DIR/computehub.pid"

cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    . venv/bin/activate
fi

start() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Starting ComputeHub Gateway..."
    nohup python3 main.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ Gateway started (PID: $(cat $PID_FILE))"
    echo "📋 Logs: $LOG_FILE"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "✅ Gateway stopped (PID: $PID)"
        else
            echo "⚠️  Process $PID not running"
        fi
        rm -f "$PID_FILE"
    else
        echo "⚠️  No PID file found"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Gateway running (PID: $PID)"
        else
            echo "❌ Gateway not running (stale PID file)"
        fi
    else
        echo "❌ Gateway not running"
    fi
}

health() {
    PORT=$(grep -oP 'port: \K[0-9]+' config.yaml 2>/dev/null || echo 8000)
    curl -s "http://localhost:$PORT/api/health" | python3 -m json.tool
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    status)  status ;;
    health)  health ;;
    logs)    tail -f "$LOG_FILE" ;;
    *)       echo "Usage: $0 {start|stop|status|health|logs}" ;;
esac
