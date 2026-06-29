#!/bin/bash
echo "=== Phase 1: Kill old server ==="
pkill -f three-kingdoms-server 2>/dev/null
echo "Killed old processes"
sleep 1

echo "=== Phase 2: Build ==="
cd ~/three-kingdoms/backend
go build -o ../three-kingdoms-server . 2>&1
if [ $? -ne 0 ]; then
    echo "BUILD FAILED"
    exit 1
fi
echo "Build OK"

echo "=== Phase 3: Start ==="
cd ~/three-kingdoms
setsid ./three-kingdoms-server > server.log 2>&1 &
sleep 2

echo "=== Phase 4: Verify ==="
curl -s http://localhost:8080/api/health
echo ""
curl -s -o /dev/null -w "Frontend: HTTP %{http_code} (%{size_download}B)\n" http://localhost:8080/
echo "PID: $(pgrep -f three-kingdoms-server)"
echo "DONE"