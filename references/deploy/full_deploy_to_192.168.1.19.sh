#!/bin/bash
# OpenClaw 完整部署脚本 - 将整只小龙虾复制到 192.168.1.19

echo "🚀 开始完整部署 OpenClaw 到 192.168.1.19..."

# 检查目标服务器连接
echo "🔍 检查目标服务器连接..."
ping -c 3 192.168.1.19

# 创建完整部署包
echo "📦 创建完整部署包..."
cd /root/.openclaw

# 创建包含所有必要文件的部署包
tar -czf openclaw_full_deploy.tar.gz \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='ai_agent/results/*.txt' \
    --exclude='ai_agent/results/*.json' \
    workspace/

echo "📊 部署包大小: $(du -h openclaw_full_deploy.tar.gz | cut -f1)"

echo "📤 传输完整部署包到目标服务器..."
scp -P 8022 openclaw_full_deploy.tar.gz u0_a207@192.168.1.19:/data/data/com.termux/files/home/

echo "🔧 在目标服务器上完整安装..."
ssh -p 8022 u0_a207@192.168.1.19 << 'EOF'
cd /data/data/com.termux/files/home

echo "解压完整部署包..."
tar -xzf openclaw_full_deploy.tar.gz

echo "安装系统依赖..."
pkg update -y
pkg install -y nodejs python git openssh

# 安装 OpenClaw
echo "安装 OpenClaw..."
npm install -g openclaw

# 复制配置
echo "复制配置文件..."
cp -r workspace/config/* ~/.openclaw/config/ 2>/dev/null || mkdir -p ~/.openclaw/config
cp workspace/SOUL.md ~/.openclaw/
cp workspace/AGENTS.md ~/.openclaw/
cp workspace/USER.md ~/.openclaw/
cp workspace/TOOLS.md ~/.openclaw/
cp workspace/HEARTBEAT.md ~/.openclaw/

# 创建启动脚本
cat > start_openclaw.sh << 'SCRIPT'
#!/bin/bash
echo "🦞 小龙虾启动中..."
cd ~/.openclaw
openclaw
SCRIPT

chmod +x start_openclaw.sh

# 创建服务脚本
cat > openclaw_service.sh << 'SCRIPT'
#!/bin/bash
while true; do
    echo "$(date): 启动 OpenClaw..."
    cd ~/.openclaw
    openclaw
    echo "$(date): OpenClaw 退出，10秒后重启..."
    sleep 10
done
SCRIPT

chmod +x openclaw_service.sh

echo "✅ 完整部署完成！"
echo "启动命令: ./start_openclaw.sh"
echo "后台服务: nohup ./openclaw_service.sh &"
echo "小龙虾已成功复制到本机！"
EOF

echo "🎉 完整部署脚本创建完成！"
echo "运行命令: bash full_deploy_to_192.168.1.19.sh"
echo "这将把整只小龙虾（包括记忆、配置、技能）完整复制过去"