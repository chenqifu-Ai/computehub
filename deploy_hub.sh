#!/bin/bash
echo "🚀 Starting ComputeHub Soul-Gateway Deployment..."

# Ensure dependencies are installed
pip install fastapi uvicorn requests psutil --break-system-packages

# Kill any existing gateway
pkill -f uvicorn || true

# Start Gateway in background with PYTHONPATH set
export PYTHONPATH=/root/GitHub/computehub
nohup python3 -m api.rest_api > /root/GitHub/computehub/gateway.log 2>&1 &

# Wait for boot
sleep 5

# Verify if it's running
if curl -s http://localhost:8000/api/health | grep -q "Healthy"; then
    echo "✅ ComputeHub Gateway is ONLINE on port 8000"
    echo "🌐 Local IP: $(hostname -I | awk '{print $1}')"
    echo "------------------------------------------------"
    echo "Quick Test: PYTHONPATH=. python3 tests/admission_test.py"
else
    echo "❌ Deployment failed. Check /root/GitHub/computehub/gateway.log"
    exit 1
fi
