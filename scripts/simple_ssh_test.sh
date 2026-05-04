#!/bin/bash
# 简单的SSH连接测试脚本

echo "🔍 测试SSH连接到192.168.1.19..."
echo "尝试常见用户名密码组合..."

HOST="192.168.1.19"
PORT="8022"

# 测试组合
test_combination() {
    local user="$1"
    local pass="$2"
    
    echo -n "测试 $user/$pass..."
    
    # 使用sshpass测试连接
    timeout 5 sshpass -p "$pass" ssh -p "$PORT" "$user@$HOST" "echo '成功'" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo " ✅ 成功!"
        echo "发现有效组合: $user/$pass"
        exit 0
    else
        echo " ❌ 失败"
    fi
}

# 测试已知和常见组合
test_combination "u0_a46" "123"
test_combination "u0_a207" "123"
test_combination "root" "123"
test_combination "root" "123456"
test_combination "admin" "123"
test_combination "admin" "123456"
test_combination "termux" "termux"
test_combination "android" "android"
test_combination "mi" "mi"
test_combination "xiaomi" "xiaomi"

echo "❌ 所有测试组合都失败"
echo "💡 请手动确认192.168.1.19的正确用户名和密码"