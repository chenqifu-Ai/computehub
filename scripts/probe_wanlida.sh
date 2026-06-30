#!/bin/bash
# Probe wanlida-opc01 through the Gateway API
# This script submits tasks via Gateway to probe the wanlida node

GATEWAY="http://36.250.122.43:8282"
NODE="wanlida-opc01"

echo "=== Probing wanlida-opc01 ==="

# Use node -e to probe (simple direct .exe execution)
# Task 1: Check git version
curl -s -X POST "$GATEWAY/api/v1/tasks/submit" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"probe-git\",\"node_id\":\"$NODE\",\"command\":\"C:\\\\tools\\\\git\\\\bin\\\\git.exe --version\",\"timeout\":30}"

sleep 2

# Task 2: Check OpenClaw via npx
curl -s -X POST "$GATEWAY/api/v1/tasks/submit" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"probe-oc\",\"node_id\":\"$NODE\",\"command\":\"npx openclaw --version\",\"timeout\":60}"

sleep 5

echo "=== Tasks submitted ==="
echo "Check results at: curl $GATEWAY/api/v1/tasks/list?node_id=$NODE"
