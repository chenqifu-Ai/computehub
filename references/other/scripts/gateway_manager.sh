#!/bin/bash
# OpenClaw Gateway高级管理脚本

case "$1" in
    start)
        echo "🚀 启动Gateway服务..."
        nohup openclaw gateway start --bind auto > ~/gateway.out 2> ~/gateway.err &
        echo "✅ 启动命令已发送"
        ;;
    stop)
        echo "🛑 停止Gateway服务..."
        pkill -f "openclaw-gateway"
        pkill -f "openclaw gateway"
        echo "✅ 服务已停止"
        ;;
    restart)
        echo "🔄 重启Gateway服务..."
        pkill -f "openclaw-gateway"
        pkill -f "openclaw gateway"
        sleep 2
        nohup openclaw gateway start --bind auto > ~/gateway.out 2> ~/gateway.err &
        echo "✅ 重启完成"
        ;;
    status)
        echo "🔍 Gateway服务状态:"
        ps aux | grep -E "(openclaw|gateway)" | grep -v grep
        echo "🌐 网络状态:"
        netstat -tlnp 2>/dev/null | grep :18789 || echo "端口未监听"
        ;;
    logs)
        echo "📋 Gateway日志:"
        tail -20 ~/gateway.out 2>/dev/null || echo "无输出日志"
        echo "❌ 错误日志:"
        tail -20 ~/gateway.err 2>/dev/null || echo "无错误日志"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo "   start    - 启动Gateway服务"
        echo "   stop     - 停止Gateway服务"
        echo "   restart  - 重启Gateway服务"
        echo "   status   - 查看服务状态"
        echo "   logs     - 查看日志"
        ;;
esac
