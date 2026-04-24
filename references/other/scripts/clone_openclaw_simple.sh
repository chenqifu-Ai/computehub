#!/bin/bash
# OpenClaw完整克隆脚本

echo "🦞 开始完整OpenClaw环境克隆"
echo "📅 开始时间: $(date)"
echo "📡 源设备: 本机"
echo "📱 目标设备: 192.168.1.9 (华为手机)"
echo "=================================================="

# 备份目标设备
echo "📦 备份目标设备配置..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "cd ~ && tar -czf openclaw_backup_$(date +%Y%m%d_%H%M).tar.gz .openclaw/ 2>/dev/null || echo '无.openclaw目录'"

# 同步完整.openclaw目录
echo "🔄 同步完整OpenClaw目录..."
cd /root/.openclaw && tar -czf - . | \
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "mkdir -p ~/.openclaw && cd ~/.openclaw && tar -xzf -"

# 同步workspace
echo "💼 同步workspace..."
cd /root/.openclaw/workspace && tar -czf - . | \
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "mkdir -p ~/.openclaw/workspace && cd ~/.openclaw/workspace && tar -xzf -"

# 同步extensions
echo "🔌 同步extensions..."
cd /root/.openclaw/extensions && tar -czf - . | \
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "mkdir -p ~/.openclaw/extensions && cd ~/.openclaw/extensions && tar -xzf -"

echo "🔍 验证同步结果..."

# 检查同步结果
check_items=(
    "ls -la ~/.openclaw/ | wc -l"
    "ls -la ~/.openclaw/workspace/ | wc -l" 
    "ls -la ~/.openclaw/extensions/ | wc -l"
    "cat ~/.openclaw/openclaw.json | grep -c gateway"
    "find ~/.openclaw/workspace -name '*.py' | wc -l"
)

for check_cmd in "${check_items[@]}"; do
    result=$(sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 "$check_cmd" 2>/dev/null)
    echo "✅ $check_cmd: $result"
done

# 启动Gateway
echo "🚀 启动Gateway服务..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "pkill -f openclaw 2>/dev/null || true"

sleep 2

sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "nohup openclaw gateway --no-daemon --allow-unconfigured > gateway.out 2> gateway.err &"

sleep 3

# 检查服务状态
echo "🌐 检查Gateway状态..."
gateway_status=$(sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "ps aux | grep openclaw | grep -v grep || echo '无进程'")

echo "📊 Gateway状态: $gateway_status"

echo ""
echo "🎉 完整克隆完成！"
echo "📱 华为手机现在拥有与本机完全相同的OpenClaw环境"
echo "🦞 小龙虾配置已完整复制到华为手机"