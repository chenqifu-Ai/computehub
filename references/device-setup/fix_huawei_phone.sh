#!/bin/bash

# 华为手机OpenClaw修复脚本
# 目标: 192.168.1.9:8022 用户: u0_a46 密码: 123

echo "🔧 开始修复华为手机OpenClaw问题..."

# 检查连接性
ping -c 1 192.168.1.9 >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 华为手机离线"
    exit 1
fi

echo "✅ 华为手机在线"

# 检查SSH连接
sshpass -p 123 ssh -p 8022 -o ConnectTimeout=5 u0_a46@192.168.1.9 "echo SSH连接测试成功" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ SSH连接失败"
    exit 1
fi

echo "✅ SSH连接正常"

# 检查OpenClaw安装
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "ls /data/data/com.termux/files/usr/bin/openclaw" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ OpenClaw未安装"
    exit 1
fi

echo "✅ OpenClaw已安装"

# 检查版本
version=$(sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "/data/data/com.termux/files/usr/bin/openclaw version 2>/dev/null | head -1")
if [ -z "$version" ]; then
    echo "⚠️ 版本检查失败，尝试修复..."
    
    # 重新安装OpenClaw
    echo "🔄 重新安装OpenClaw..."
    sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "npm install -g openclaw@latest" >/dev/null 2>&1
    
    # 再次检查版本
    version=$(sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "/data/data/com.termux/files/usr/bin/openclaw version 2>/dev/null | head -1")
    if [ -z "$version" ]; then
        echo "❌ 重新安装失败"
        exit 1
    fi
fi

echo "✅ OpenClaw版本: $version"

# 停止现有服务
echo "🛑 停止现有服务..."
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "pkill -f openclaw" >/dev/null 2>&1

# 启动网关服务
echo "🚀 启动网关服务..."
sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "nohup /data/data/com.termux/files/usr/bin/openclaw gateway start > ~/.openclaw/logs/startup.log 2>&1 &"

# 等待服务启动
sleep 5

# 检查服务状态
echo "📊 检查服务状态..."
ps_count=$(sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "ps aux | grep -i openclaw | grep -v grep | wc -l")

if [ "$ps_count" -gt 0 ]; then
    echo "✅ OpenClaw服务运行中 ($ps_count 个进程)"
    
    # 检查端口监听
    port_listen=$(sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "netstat -tln 2>/dev/null | grep :18789 || echo '未监听'")
    if [[ "$port_listen" != *"未监听"* ]]; then
        echo "✅ 端口18789监听正常"
    else
        echo "⚠️ 端口18789未监听"
    fi
    
else
    echo "❌ 服务启动失败"
    
    # 查看启动日志
    echo "📝 查看启动日志..."
    sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "tail -10 ~/.openclaw/logs/startup.log 2>/dev/null || echo '无启动日志'"
    exit 1
fi

# 测试服务连接
echo "🔗 测试服务连接..."
response=$(sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 "curl -s http://localhost:18789/health 2>/dev/null || echo '连接失败'")

if [[ "$response" == *"ok"* ]]; then
    echo "✅ 服务健康检查通过"
else
    echo "⚠️ 服务连接测试失败: $response"
fi

echo ""
echo "🎉 华为手机修复完成!"
echo "📱 设备: HUAWEI HWI-AL00"
echo "🌐 IP: 192.168.1.9:8022"
echo "🔧 状态: 服务已启动"
echo "📊 版本: $version"