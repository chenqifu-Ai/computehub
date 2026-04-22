#!/bin/bash
# Total Cleanup
pkill -f uvicorn || true
pkill -f "python3 gateway_final.py" || true
fuser -k 8000/tcp || true

# Setup Env
export PYTHONPATH=/root/GitHub/computehub
cd /root/GitHub/computehub

# Start Gateway
nohup python3 gateway_final.py > gateway_final.log 2>&1 &
echo "Waiting for Gateway to boot..."
sleep 5

# Run Test
PYTHONPATH=. python3 tests/admission_test.py
