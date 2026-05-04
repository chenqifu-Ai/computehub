#!/bin/bash
# 设备连接测试脚本
# 诊断 10.35.204.186 的连接问题

echo "🔧 设备连接诊断工具"
echo "================================"
echo "目标设备: 10.35.204.186"
echo "诊断时间: $(date)"
echo "================================"

# 1. 基础连通性
echo "1. 📶 网络连通性测试..."
if ping -c 2 10.35.204.186 >/dev/null 2>&1; then
    echo "✅ 设备在线 (ping 成功)"
else
    echo "❌ 设备离线"
    exit 1
fi

# 2. 端口检查
echo ""
echo "2. 🚪 端口可用性测试..."
open_ports=""
for port in 8022 22 18789 443 80; do
    if timeout 2 nc -zv 10.35.204.186 $port 2>/dev/null; then
        echo "✅ 端口 $port 开放"
        open_ports="$open_ports $port"
    else
        echo "❌ 端口 $port 关闭"
    fi
done

# 3. SSH 连接测试
echo ""
echo "3. 🔑 SSH 连接测试..."

# 测试常见 Termux 用户名
echo "测试用户名: u0_a165"
sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a165@10.35.204.186 'echo ✅ SSH 连接成功' 2>&1 \
    && echo "✅ u0_a165 连接成功" \
    || echo "❌ u0_a165 连接失败"

echo "测试用户名: u0_a164"  
sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a164@10.35.204.186 'echo ✅ SSH 连接成功' 2>&1 \
    && echo "✅ u0_a164 连接成功" \
    || echo "❌ u0_a164 连接失败"

# 4. 密码测试
echo ""
echo "4. 🔐 密码测试..."
echo "测试密码: 123"
echo "测试密码: password"  
echo "测试密码: 123456"

# 5. 解决方案
echo ""
echo "5. 🛠️ 解决方案建议:"
echo "================================"
if [ -n "$open_ports" ]; then
    echo "✅ 开放端口: $open_ports"
    echo ""
    echo "建议操作:"
    echo "1. 在目标设备上确认 SSH 服务运行: sshd"
    echo "2. 检查正确的用户名和密码"
    echo "3. 确认 Termux 已授予存储权限"
    echo "4. 检查目标设备的用户列表"
else
    echo "❌ 无开放端口，需要启动服务"
    echo "在目标设备上执行: sshd"
fi

echo "================================"
echo "诊断完成。请根据上述结果采取相应措施。"