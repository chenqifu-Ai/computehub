#!/bin/bash
# Kill old gateways
pkill -9 -f 'computehub gateway' 2>/dev/null
sleep 3
# Ensure port free
ss -tlnp | grep 8282 && sleep 2
echo "PORT OK"

# Deploy
mv ~/ComputeHub/deploy/computehub.new ~/ComputeHub/deploy/computehub
chmod +x ~/ComputeHub/deploy/computehub
rm -f ~/ComputeHub/deploy/hall_data.json

# Start
nohup ~/ComputeHub/deploy/computehub gateway --port 8282 > ~/ComputeHub/deploy/gateway.log 2>&1 &
echo $! > ~/ComputeHub/deploy/gateway.pid
sleep 5

echo "PID: $(cat ~/ComputeHub/deploy/gateway.pid)"
grep 'auto-reply' ~/ComputeHub/deploy/gateway.log
curl -s -m 5 http://localhost:8282/api/v1/hall/topics