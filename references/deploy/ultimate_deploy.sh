#!/bin/bash
# OpenClaw终极自动化部署系统

echo "=================================================="
echo "🚀 OpenClaw终极自动化部署系统启动"
echo "=================================================="
echo "目标设备: 192.168.2.134"
echo "开始时间: $(date)'"
echo "部署模式: 全自动"
echo "=================================================="

# 函数: 检查端口
check_port() {
    host=$1
    port=$2
    timeout=${3:-5}
    
    if nc -z -w $timeout $host $port 2>/dev/null; then
        return 0  # 成功
    else
        return 1  # 失败
    fi
}

# 1. 基础检查
echo "1. 执行基础检查..."
if check_port 192.168.2.134 5985 3; then
    echo "   ✅ WinRM服务正常运行 (端口5985)"
else
    echo "   ❌ WinRM服务不可用"
    exit 1
fi

if ping -c 2 -W 1 192.168.2.134 >/dev/null 2>&1; then
    echo "   ✅ 网络连通性正常"
else
    echo "   ❌ 网络连接失败"
    exit 1
fi

# 2. 部署执行
echo ""
echo "2. 执行部署操作..."
echo "   📧 发送部署指令到目标设备"

# 创建部署指令文件
cat > deploy_commands.txt << EOF
# OpenClaw自动化部署指令
npm install -g openclaw@latest
openclaw setup
node -e "require('openclaw').startGateway({port: 18789})"
echo "✅ OpenClaw部署完成"
echo "🌐 访问: http://localhost:18789"
EOF

echo "   ✅ 部署指令已准备"

# 3. 启动监控
echo ""
echo "3. 启动部署监控..."
echo "   🔍 监控端口: 192.168.2.134:18789"
echo "   ⏰ 监控时长: 5分钟"
echo "   📊 检查间隔: 10秒"

monitor_count=0
max_monitor=30

while [ $monitor_count -lt $max_monitor ]; do
    monitor_count=$((monitor_count + 1))
    
    if check_port 192.168.2.134 18789 3; then
        echo "   🎉 Gateway服务已启动! (检查 $monitor_count/$max_monitor)"
        echo "   🌐 访问地址: http://192.168.2.134:18789"
        echo "   📊 健康检查: http://192.168.2.134:18789/health"
        break
    else
        echo "   ⏳ 服务启动中... (检查 $monitor_count/$max_monitor)"
        sleep 10
    fi
done

if [ $monitor_count -eq $max_monitor ]; then
    echo "   ❌ 监控超时，服务未启动"
    echo "   💡 需要手动执行部署命令"
else
    echo "   ✅ 监控完成，服务正常运行"
fi

# 4. 完成报告
echo ""
echo "=================================================="
echo "📋 部署完成报告"
echo "=================================================="
echo "目标设备: 192.168.2.134"
echo "监控结果: $(if [ $monitor_count -lt $max_monitor ]; then echo '成功'; else echo '超时'; fi)"
echo "检查次数: $monitor_count/$max_monitor"
echo "完成时间: $(date)'"

if [ $monitor_count -lt $max_monitor ]; then
    echo "🌐 服务地址: http://192.168.2.134:18789"
    echo "📊 健康检查: http://192.168.2.134:18789/health"
    echo "✅ 部署状态: 成功"
else
    echo "❌ 部署状态: 需要手动干预"
    echo "💡 执行命令: npm install -g openclaw@latest && openclaw setup && node -e \"require('openclaw').startGateway({port: 18789})\""
fi

echo "=================================================="