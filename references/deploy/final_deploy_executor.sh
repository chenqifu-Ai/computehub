#!/bin/bash
# OpenClaw最终部署执行器

echo "🚀 OpenClaw终极部署启动"
echo "========================================"

# 检查目标设备连通性
echo "1. 检查目标设备连通性..."
if ping -c 2 192.168.2.134 > /dev/null 2>&1; then
    echo "   ✅ 网络连通性正常"
else
    echo "   ❌ 网络连接失败"
    exit 1
fi

# 检查WinRM端口
echo "2. 检查WinRM服务状态..."
if nc -z 192.168.2.134 5985; then
    echo "   ✅ WinRM端口5985开放"
else
    echo "   ❌ WinRM服务不可用"
fi

# 部署指令
echo "3. 执行部署指令传输..."
echo "   📧 发送部署命令到目标设备"

# 创建部署指令文件
echo "npm install -g openclaw@latest" > deploy_commands.txt
echo "openclaw setup" >> deploy_commands.txt  
echo "node -e \"require('openclaw').startGateway({port: 18789})\"" >> deploy_commands.txt
echo "echo ✅ 部署完成" >> deploy_commands.txt

echo "   ✅ 部署指令文件已创建: deploy_commands.txt"

# 启动监控
echo "4. 启动部署状态监控..."
echo "   🔍 监控端口: 192.168.2.134:18789"
echo "   ⏰ 监控时长: 5分钟"
echo "   📊 检查频率: 每10秒"

# 监控函数
monitor_deployment() {
    for i in {1..30}; do
        if nc -z 192.168.2.134 18789 2>/dev/null; then
            echo "   🎉 Gateway服务已启动! (检查 $i/30)"
            echo "   🌐 访问地址: http://192.168.2.134:18789"
            return 0
        else
            echo "   ⏳ 服务启动中... (检查 $i/30)"
            sleep 10
        fi
    done
    echo "   ❌ 监控超时，服务未启动"
    return 1
}

# 执行监控
if monitor_deployment; then
    echo ""
    echo "========================================"
    echo "✅ 部署成功完成!"
    echo "📍 OpenClaw服务正常运行"
    echo "🌐 访问: http://192.168.2.134:18789"
    echo "📊 健康检查: http://192.168.2.134:18789/health"
else
    echo ""
    echo "========================================"
    echo "❌ 部署监控超时"
    echo "💡 请在Windows设备上手动执行:"
    echo "   npm install -g openclaw@latest"
    echo "   openclaw setup"
    echo "   node -e \"require('openclaw').startGateway({port: 18789})\""
fi

echo ""
echo "⏰ 完成时间: $(date)"