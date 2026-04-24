#!/bin/bash
# 同步本机配置到华为手机

HUAWEI_IP="192.168.1.9"
HUAWEI_USER="u0_a46"
HUAWEI_PASSWORD="123"
SSH_PORT="8022"

echo "🚀 开始同步配置到华为手机..."

# 检查华为手机连接
if ! ping -c 2 $HUAWEI_IP > /dev/null 2>&1; then
    echo "❌ 华为手机无法连接，请检查网络"
    exit 1
fi

# 同步openclaw.json配置文件
echo "📋 同步openclaw.json配置文件..."
if sshpass -p "$HUAWEI_PASSWORD" scp -P $SSH_PORT -o StrictHostKeyChecking=no ~/.openclaw/openclaw.json $HUAWEI_USER@$HUAWEI_IP:~/.openclaw/openclaw.json; then
    echo "✅ openclaw.json 同步成功"
else
    echo "❌ openclaw.json 同步失败"
fi

# 同步config目录
echo "📁 同步config目录..."
if sshpass -p "$HUAWEI_PASSWORD" scp -P $SSH_PORT -o StrictHostKeyChecking=no -r ~/.openclaw/config/ $HUAWEI_USER@$HUAWEI_IP:~/.openclaw/; then
    echo "✅ config目录同步成功"
else
    echo "❌ config目录同步失败"
fi

# 同步重要配置文件
echo "🔧 同步其他重要配置..."

# 同步email配置
if [ -f ~/.openclaw/workspace/config/email.conf ]; then
    sshpass -p "$HUAWEI_PASSWORD" scp -P $SSH_PORT -o StrictHostKeyChecking=no ~/.openclaw/workspace/config/email.conf $HUAWEI_USER@$HUAWEI_IP:~/.openclaw/workspace/config/
    echo "✅ email.conf 同步成功"
fi

# 同步163邮箱配置
if [ -f ~/.openclaw/workspace/config/163_email.conf ]; then
    sshpass -p "$HUAWEI_PASSWORD" scp -P $SSH_PORT -o StrictHostKeyChecking=no ~/.openclaw/workspace/config/163_email.conf $HUAWEI_USER@$HUAWEI_IP:~/.openclaw/workspace/config/
    echo "✅ 163_email.conf 同步成功"
fi

# 检查同步后的配置
echo "🔍 验证同步结果..."
if sshpass -p "$HUAWEI_PASSWORD" ssh -p $SSH_PORT -o StrictHostKeyChecking=no $HUAWEI_USER@$HUAWEI_IP "ls -la ~/.openclaw/openclaw.json ~/.openclaw/config/" > /dev/null 2>&1; then
    echo "🎉 配置同步完成！"
    echo "💡 现在可以在华为手机上运行: openclaw gateway --allow-unconfigured"
else
    echo "⚠️  同步完成，但建议手动验证配置"
fi