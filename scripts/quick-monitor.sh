#!/bin/bash
# 临时监控脚本 - 系统 + 项目 + API
# 可撤销: 删除此文件即可

echo "=== 系统监控 ==="
echo "负载: $(uptime | awk -F'load average:' '{print $2}')"
free -h | grep Mem
df -h / | tail -1
echo ""

echo "=== Ollama 模型 ==="
curl -s http://127.0.0.1:11434/api/tags 2>/dev/null | python3 -c "import sys,json; [print(f'  - {m[\"name\"]}') for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null || echo "  Ollama 未运行"
echo ""

echo "=== Computehub 测试 ==="
cd /root/.openclaw/workspace/projects/computehub && CGO_ENABLED=0 go test ./... 2>&1 | grep -E "(PASS|FAIL|ok|---)"
echo ""

echo "=== Git 最近提交 ==="
cd /root/.openclaw/workspace && git log --oneline -5
echo ""
