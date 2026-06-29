#!/bin/bash
# ecs-p2ph 每30秒自检脚本
# 通过本机 Gateway 提交任务给自己，验证全链路畅通

NODE_ID="ecs-p2ph"
GW="http://127.0.0.1:8282"
LOG="$HOME/logs/ecs-p2ph-test.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date "+%Y-%m-%d %H:%M:%S")] ecs-p2ph 周期性自检启动 (间隔: 30s)" >> "$LOG"

while true; do
  TS=$(date "+%Y-%m-%d %H:%M:%S")

  # 1. 提交轻量级测试任务
  RESP=$(curl -s -X POST "$GW/api/v1/tasks/submit" \
    -H 'Content-Type: application/json' \
    -d '{"type":"exec","payload":"hostname && date +%H:%M:%S && free -m | awk '\''NR==2{printf \"MEM: %s/%s MB\\n\", $3, $2}'\''","node":"ecs-p2ph","timeout":10}' 2>/dev/null)

  TID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('task_id','FAIL'))" 2>/dev/null)

  if [ "$TID" = "FAIL" ]; then
    echo "$TS | SUBMIT_FAIL: $RESP" >> "$LOG"
    sleep 30
    continue
  fi

  # 2. 等任务完成
  sleep 4

  # 3. 查结果
  R=$(curl -s "$GW/api/v1/tasks/detail?task_id=$TID" 2>/dev/null)
  S=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('status','?'))" 2>/dev/null)
  E=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('exit_code',-1))" 2>/dev/null)
  O=$(echo "$R" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('stdout','').strip().replace(chr(10),' | ')[:80])" 2>/dev/null)

  echo "$TS | status=$S exit=$E | $O" >> "$LOG"

  sleep 30
done