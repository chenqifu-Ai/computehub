#!/bin/bash
# 全面测试所有可能的SSH连接方式

echo "🔍 全面SSH连接测试 - 192.168.1.19:8022"
echo "============================================"

HOST="192.168.1.19"
PORT="8022"

# 测试函数
test_connection() {
    local desc="$1"
    local cmd="$2"
    
    echo -n "测试: $desc..."
    
    eval "$cmd" >/dev/null 2>&1
    local result=$?
    
    if [ $result -eq 0 ]; then
        echo " ✅ 成功"
        return 0
    else
        echo " ❌ 失败"
        return 1
    fi
}

# 1. 测试网络连通性
echo "1. 网络连通性测试:"
test_connection "Ping测试" "ping -c 2 $HOST"
test_connection "端口扫描" "nc -z -w 2 $HOST $PORT"

# 2. 测试现有密钥认证
echo -e "\n2. 密钥认证测试:"
test_connection "id_openclaw密钥" "ssh -o BatchMode=yes -o ConnectTimeout=5 -p $PORT -i ~/.ssh/id_openclaw u0_a207@$HOST echo '测试成功'"
test_connection "id_ed25519密钥" "ssh -o BatchMode=yes -o ConnectTimeout=5 -p $PORT -i ~/.ssh/id_ed25519 u0_a207@$HOST echo '测试成功'"

# 3. 测试密码认证（使用sshpass）
echo -e "\n3. 密码认证测试:"
if command -v sshpass >/dev/null 2>&1; then
    test_connection "u0_a207/123" "sshpass -p '123' ssh -p $PORT u0_a207@$HOST echo '测试成功'"
    test_connection "u0_a46/123" "sshpass -p '123' ssh -p $PORT u0_a46@$HOST echo '测试成功'"
    test_connection "root/123" "sshpass -p '123' ssh -p $PORT root@$HOST echo '测试成功'"
else
    echo "sshpass未安装，跳过密码测试"
fi

# 4. 测试SSH配置
echo -e "\n4. SSH配置测试:"
test_connection "mi-pad主机配置" "ssh -o BatchMode=yes -o ConnectTimeout=5 mi-pad echo '测试成功'"

# 5. 详细错误诊断
echo -e "\n5. 详细错误诊断:"
echo "测试详细连接输出:"
ssh -v -p $PORT u0_a207@$HOST echo '详细测试' 2>&1 | head -10

echo -e "\n============================================"
echo "测试完成！建议根据上述结果进行相应配置"