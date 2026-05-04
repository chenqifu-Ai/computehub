#!/bin/bash
# 小智远程访问一键连接脚本
# 自动检测网络状态，生成访问信息

echo "🔗 小智远程访问系统"
echo "========================"

# 获取IP地址
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$IP" ]; then
    IP="无法获取IP（请检查网络）"
fi

# 检查服务状态
echo "📊 系统状态检查："

# 检查OpenClaw Gateway
if pgrep -f "openclaw-gateway" > /dev/null; then
    echo "✅ OpenClaw Gateway: 运行中 (端口: 18789)"
else
    echo "❌ OpenClaw Gateway: 未运行"
fi

# 检查SSH服务
if pgrep -f "sshd" > /dev/null; then
    echo "✅ SSH服务: 运行中 (端口: 8022)"
else
    echo "❌ SSH服务: 未运行"
fi

# 检查Ollama
if pgrep -f "ollama" > /dev/null; then
    echo "✅ Ollama AI服务: 运行中 (端口: 11434)"
else
    echo "❌ Ollama AI服务: 未运行"
fi

echo ""
echo "🌐 访问方式："
echo "1. OpenClaw Web界面: http://$IP:18789"
echo "2. SSH命令行: ssh -p 8022 root@$IP"
echo "3. OpenClaw TUI: openclaw-tui --gateway http://$IP:18789"
echo "4. Ollama API: http://$IP:11434"

echo ""
echo "💡 提示："
echo "- 如果无法连接，请检查防火墙设置"
echo "- 确保设备在同一网络或可访问"
echo "- 使用 'chmod +x quick_connect.sh' 赋予执行权限"

# 生成QR码（如果支持）
if command -v qrencode > /dev/null; then
    echo ""
    echo "📱 QR码访问："
    qrencode -t ANSI "http://$IP:18789"
fi