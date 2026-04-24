#!/bin/bash
# OpenClaw SSH连接助手

echo "🔧 SSH连接问题诊断"
echo "===================="

# 1. 测试网络连通性
echo "1. 网络测试:"
ping -c 2 192.168.1.19 &>/dev/null && echo "  ✅ 网络通畅" || echo "  ❌ 网络问题"

# 2. 测试端口
echo "2. 端口测试:"
nc -z -w 2 192.168.1.19 8022 &>/dev/null && echo "  ✅ 端口8022开放" || echo "  ❌ 端口不可达"

# 3. 显示密钥信息
echo "3. 密钥信息:"
echo "   私钥: ~/.ssh/id_openclaw"
echo "   公钥: $(cat ~/.ssh/id_openclaw.pub | cut -d' ' -f1-2)"

# 4. 测试连接
echo "4. 连接测试:"
ssh -o BatchMode=yes -o ConnectTimeout=5 -i ~/.ssh/id_openclaw -p 8022 openclaw-tui@192.168.1.19 "echo 测试" &>/dev/null

if [ $? -eq 0 ]; then
    echo "  ✅ SSH密钥认证成功"
else
    echo "  ❌ SSH认证失败"
    echo ""
    echo "💡 解决方案:"
    echo "  在192.168.1.19上检查:"
    echo "  - ~/.ssh/authorized_keys 文件权限 (应为600)"
    echo "  - ~/.ssh/ 目录权限 (应为700)" 
    echo "  - 公钥内容是否匹配"
    echo "  - 运行: ls -la ~/.ssh/"
fi

echo "===================="
