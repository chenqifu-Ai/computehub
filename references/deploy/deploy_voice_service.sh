#!/bin/bash
# 语音接收服务部署脚本

echo "🎤 开始部署语音接收服务..."

# 1. 检查Python环境
echo "🔧 检查Python环境..."
python3 --version

# 2. 启动语音服务器
echo "🚀 启动语音服务器..."
cd /root/.openclaw/workspace

# 后台启动语音服务器
nohup python3 voice_server.py > voice_server.log 2>&1 &
SERVER_PID=$!

echo "✅ 语音服务器已启动 (PID: $SERVER_PID)"
echo "📋 服务日志: /root/.openclaw/workspace/voice_server.log"

# 3. 获取服务器信息
echo "🌐 服务器信息:"
echo "   - 监听端口: 9999"
echo "   - 支持协议: TCP"
echo "   - 客户端: 手机网络调试助手"

# 4. 显示连接说明
echo ""
echo "📱 手机连接方法:"
echo "   1. 下载'网络调试助手'APP"
echo "   2. 创建TCP客户端"
echo "   3. 输入服务器IP和端口9999"
echo "   4. 连接后即可发送文字命令"

echo ""
echo "💡 支持命令:"
echo "   - 你好"
echo "   - 时间"  
echo "   - 日期"
echo "   - 测试"
echo "   - 退出"

echo ""
echo "✅ 语音接收服务部署完成!"
echo "📞 现在可以用手机连接并发送语音转文字的命令了"