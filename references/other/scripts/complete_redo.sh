#!/bin/bash
# 完整重做华为手机OpenClaw配置

echo "🎯 开始完整重做华为手机OpenClaw配置..."

# 1. 首先停止所有服务
echo "🛑 停止所有OpenClaw服务..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "pkill -f 'openclaw\|node' && sleep 2"

echo "✅ 服务已停止"

# 2. 备份当前配置
echo "📦 备份当前配置..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "cp -r ~/.openclaw ~/.openclaw.backup.$(date +%Y%m%d_%H%M%S)"

echo "✅ 配置已备份"

# 3. 彻底卸载OpenClaw
echo "🗑️ 彻底卸载OpenClaw..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "npm uninstall -g openclaw && pnpm uninstall -g openclaw 2>/dev/null || true"

echo "✅ OpenClaw已卸载"

# 4. 清理缓存和残留文件
echo "🧹 清理缓存和残留..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "rm -rf ~/.local/share/pnpm/global/5/.pnpm/openclaw* ~/.npm/_cacache/*openclaw* 2>/dev/null || true"

echo "✅ 缓存已清理"

# 5. 重新安装指定版本
echo "📥 重新安装OpenClaw 2026.3.13..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "npm install -g openclaw@2026.3.13"

echo "✅ OpenClaw已安装"

# 6. 同步本机配置
echo "🔄 同步本机配置..."
sshpass -p "123" scp -P 8022 -o StrictHostKeyChecking=no \
    /root/.openclaw/openclaw.json \
    u0_a46@192.168.1.9:~/.openclaw/openclaw.json

echo "✅ 配置已同步"

# 7. 简化模型配置
echo "🎨 简化模型配置..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "sed -i '/\"models\": {/,/^      }/{/\"models\": {/b;/^      }/b;/\"modelstudio\\/qwen3\\.5-flash\": {}/b;/\"modelstudio\\/qwen3\\.5-plus\": {}/b;/\"ollama-cloud\\/deepseek-v3\\.1:671b\": {}/b;/\"ollama\\/llama3:latest\": {}/b;d}' ~/.openclaw/openclaw.json"

echo "✅ 模型配置已简化"

# 8. 重新启动服务
echo "🚀 启动Gateway服务..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "cd ~ && nohup openclaw gateway --allow-unconfigured > redo_start.log 2>&1 &"

echo "✅ 服务启动中"

# 9. 等待并验证
echo "⏳ 等待服务启动..."
sleep 8

echo "🔍 验证安装结果..."
sshpass -p "123" ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "openclaw --version && echo '---' && grep 'primary' ~/.openclaw/openclaw.json && echo '---' && ps aux | grep openclaw | grep -v grep | head -2"

echo "🎉 完整重做完成！"
echo "📋 下一步: 检查健康监控显示"