#!/bin/bash
# OpenClaw 部署脚本 - 将小龙虾复制到 192.168.1.19

echo "🚀 开始部署 OpenClaw 到 192.168.1.19..."

# 检查目标服务器连接
ping -c 3 192.168.1.19

# 创建部署包
echo "📦 创建部署包..."
cd /root/.openclaw

tar -czf openclaw_deploy.tar.gz \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.log' \
    workspace/

echo "📤 传输部署包到目标服务器..."
scp -P 8022 openclaw_deploy.tar.gz u0_a207@192.168.1.19:/data/data/com.termux/files/home/

echo "🔧 在目标服务器上安装..."
ssh -p 8022 u0_a207@192.168.1.19 << 'EOF'
cd /data/data/com.termux/files/home

echo "解压部署包..."
tar -xzf openclaw_deploy.tar.gz

echo "安装依赖..."
pkg update -y
pkg install -y nodejs python

cd workspace
npm install

# 创建启动脚本
cat > start_openclaw.sh << 'SCRIPT'
#!/bin/bash
cd /data/data/com.termux/files/home/workspace
node /data/data/com.termux/files/usr/lib/node_modules/openclaw/dist/cli.js
SCRIPT

chmod +x start_openclaw.sh

echo "✅ 部署完成！"
echo "启动命令: ./start_openclaw.sh"
EOF

echo "🎉 部署脚本创建完成！"
echo "运行命令: bash deploy_to_192.168.1.19.sh"