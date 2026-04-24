#!/bin/bash
# 强制部署SSH公钥 - 使用expect处理交互

echo "🚀 强制部署SSH公钥"
echo "===================="

# 检查expect是否安装
if ! command -v expect >/dev/null 2>&1; then
    echo "安装expect工具..."
    apt update && apt install -y expect
fi

# 读取公钥
PUBLIC_KEY=$(cat ~/.ssh/id_openclaw.pub)
if [ -z "$PUBLIC_KEY" ]; then
    echo "❌ 未找到公钥文件"
    exit 1
fi

echo "📋 公钥: ${PUBLIC_KEY:0:50}..."

# 获取用户名和密码
echo "💡 请输入用户名 (默认: u0_a207): "
read -r USERNAME
USERNAME=${USERNAME:-u0_a207}

echo "💡 请输入密码: "
read -rs PASSWORD
echo

HOST="192.168.1.19"
PORT="8022"

echo "部署公钥到 $USERNAME@$HOST:$PORT..."

# 使用expect自动化部署
/usr/bin/expect << EOF
set timeout 30
spawn ssh -p $PORT $USERNAME@$HOST

expect {
    "*password:" {
        send "$PASSWORD\r"
        exp_continue
    }
    "*$ " {
        send "mkdir -p ~/.ssh && chmod 700 ~/.ssh\r"
        expect "*$ "
        
        send "echo '$PUBLIC_KEY' > ~/.ssh/authorized_keys\r"
        expect "*$ "
        
        send "chmod 600 ~/.ssh/authorized_keys\r"
        expect "*$ "
        
        send "echo '✅ SSH公钥部署完成'\r"
        expect "*$ "
        
        send "exit\r"
        expect eof
    }
    "*Permission denied*" {
        puts "\n❌ 权限被拒绝，请检查密码"
        exit 1
    }
    timeout {
        puts "\n❌ 连接超时"
        exit 1
    }
}
EOF

if [ $? -eq 0 ]; then
    echo "✅ 公钥部署成功!"
    
    # 测试无密码连接
    echo "测试无密码连接..."
    ssh -o BatchMode=yes -o ConnectTimeout=5 -i ~/.ssh/id_openclaw -p $PORT $USERNAME@$HOST "echo '🎉 无密码连接成功!'"
    
    if [ $? -eq 0 ]; then
        echo "🎊 SSH密钥认证配置完成!"
        
        # 更新SSH配置
        cat > ~/.ssh/config << EOF
Host mi-pad
    HostName 192.168.1.19
    Port 8022
    User $USERNAME
    IdentityFile ~/.ssh/id_openclaw
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad
EOF
        
        echo "✅ SSH配置已更新"
        echo "📋 使用: ssh mi-pad"
    else
        echo "⚠️  无密码连接测试失败"
    fi
else
    echo "❌ 公钥部署失败"
    exit 1
fi