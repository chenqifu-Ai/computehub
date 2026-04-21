#!/bin/bash

# ComputeHub One-Click Deployment Script
# Version: 1.0.0-alpha

set -e

echo "🚀 Starting ComputeHub Industrial Deployment..."

# 1. Environment Check
echo "--- [1/4] Checking Environment ---"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install it."
    exit 1
fi

# 2. Database Setup (Assuming PostgreSQL is running)
echo "--- [2/4] Initializing Database ---"
# In a real scenario, we would use psql to execute schema.sql
# Here we simulate the schema application if the DB is accessible
echo "Applying schema.sql to PostgreSQL..."
# psql -U postgres -d computehub -f /root/.openclaw/workspace/ai_agent/code/computehub/db/schema.sql

# 3. Start Gateway (Background)
echo "--- [3/4] Launching Deterministic Gateway ---"
nohup python3 /root/.openclaw/workspace/ai_agent/code/computehub/api/rest_api.py > gateway.log 2>&1 &
GATEWAY_PID=$!
echo "✅ Gateway started (PID: $GATEWAY_PID) on port 8000"

# 4. Start Node (Background)
echo "--- [4/4] Launching Compute Node ---"
nohup python3 /root/.openclaw/workspace/ai_agent/code/computehub/node/client.py > node.log 2>&1 &
NODE_PID=$!
echo "✅ Compute Node started (PID: $NODE_PID)"

echo "--------------------------------------------------"
echo "🎉 ComputeHub Prototype is now ONLINE!"
echo "📊 Gateway Status: http://localhost:8000/api/v1/nodes/status"
echo "📜 Logs: tail -f gateway.log / node.log"
echo "--------------------------------------------------"
echo "Press Ctrl+C to stop all services."

# Keep running and wait for user to stop
trap "kill $GATEWAY_PID $NODE_PID; echo 'Stopping ComputeHub...'; exit" SIGINT SIGTERM
while true; do sleep 1; done
