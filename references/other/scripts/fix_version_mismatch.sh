#!/bin/bash
# 解决版本不匹配问题

echo "🔧 解决OpenClaw版本不匹配问题..."

# 1. 首先备份华为手机上的配置
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.version"

echo "✅ 配置已备份"

# 2. 将本机配置同步到华为手机
sshpass -p "123" scp -P 8022 -o StrictHostKeyChecking=no \
    /root/.openclaw/openclaw.json \
    u0_a46@192.168.1.9:~/.openclaw/openclaw.json

echo "✅ 本机配置已同步"

# 3. 在华为手机上降级OpenClaw到匹配版本
echo "📦 正在降级OpenClaw版本..."

sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 << 'EOF'
# 在华为手机上执行的命令
cd ~

# 卸载当前版本
pnpm uninstall -g openclaw

# 安装指定版本
pnpm install -g openclaw@2026.3.13

echo "OpenClaw已降级到2026.3.13"
EOF

echo "✅ 版本降级完成"

# 4. 重启服务
echo "🔄 重启Gateway服务..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "pkill -f openclaw && sleep 3 && cd ~ && nohup openclaw gateway --allow-unconfigured > restart.log 2>&1 &"

echo "🎯 解决方案执行完成"
echo "💡 版本已统一: 2026.3.13"
echo "📋 配置已同步"
echo "🔄 服务已重启"