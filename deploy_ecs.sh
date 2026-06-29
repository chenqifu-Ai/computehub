#!/bin/bash
# 部署 v1.3.7 到 ECS
set -e

SSH="ssh -p 8022 -i /root/.ssh/id_ed25519_computehub -o StrictHostKeyChecking=no -o ConnectTimeout=10 computehub@36.250.122.43"

# 1. 部署新的 flat binary
$SSH "mv /home/computehub/computehub.new /home/computehub/computehub && /home/computehub/computehub version"

# 2. 启动 Gateway
$SSH "nohup /home/computehub/computehub gateway --port 8282 > /home/computehub/gateway.log 2>&1 &
sleep 3
curl -s http://127.0.0.1:8282/api/health
echo 'gateway OK'"

# 3. 启动 Worker
$SSH "nohup /home/computehub/computehub worker --gw http://localhost:8282 --node-id ecs-p2ph --interval 3 --concurrent 8 --heartbeat 10 > /home/computehub/worker.log 2>&1 &
sleep 4
curl -s http://127.0.0.1:8282/api/v1/nodes/list | python3 -c 'import sys,json;d=json.load(sys.stdin).get(\"data\",[]);[print(f\"{n[\"node_id\"]} v{n.get(\"version\",\"-\")}\") for n in d]'"

echo "DONE"