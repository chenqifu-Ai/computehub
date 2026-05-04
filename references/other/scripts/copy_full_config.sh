#!/bin/bash
# 完整配置复制脚本 - 本机到目标设备
# 目标: 10.35.204.186, 用户: u0_a207

echo "🚀 OpenClaw 完整配置复制"
echo "================================"
echo "源: /root/.openclaw/"
echo "目标: u0_a207@10.35.204.186:~/.openclaw/"
echo "================================"

# 检查设备连接
check_device() {
    echo "🔍 检查设备连接..."
    if ! ping -c 2 10.35.204.186 >/dev/null 2>&1; then
        echo "❌ 设备 10.35.204.186 离线"
        return 1
    fi
    
    # 检查 SSH 连接
    if ! sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a207@10.35.204.186 "echo ✅ SSH连接正常" 2>/dev/null; then
        echo "❌ SSH 连接失败"
        return 1
    fi
    
    echo "✅ 设备连接正常"
    return 0
}

# 创建配置包
create_config_package() {
    echo "📦 创建配置包..."
    
    # 清理旧包
    rm -f /tmp/openclaw_full_config.tar.gz 2>/dev/null
    
    # 创建新包
    tar -czf /tmp/openclaw_full_config.tar.gz -C /root/.openclaw . 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ 配置包创建成功"
        echo "大小: $(du -h /极mp/openclaw_full_config.tar.gz | cut -f1)"
        return 0
    else
        echo "❌ 配置包创建失败"
        return 1
    fi
}

# 传输配置包
transfer_config() {
    echo "📡 传输配置包..."
    
    sshpass -p '123' scp -o StrictHostKeyChecking=no -P 8022 /tmp/openclaw_full_config.tar.gz u0_a207@10.35.204.186:/data/data/com.termux/files/home/ 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ 传输成功"
        return 0
    else
        echo "❌ 传输失败"
        return 1
    fi
}

# 在目标设备上解压配置
extract_on_target() {
    echo "🔧 在目标设备上解压配置..."
    
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a207@10.35.204.186 << 'EOF'
    
    echo "📦 开始解压完整配置..."
    echo "================================"
    
    if [ -f ~/openclaw_full_config.tar.gz ]; then
        # 备份现有配置
        if [ -d ~/.openclaw ]; then
            backup_dir=~/.openclaw.backup.full.$(date +%Y%m%d_%H%M%S)
            mv ~/.openclaw "$backup_dir"
            echo "✅ 现有配置已备份到: $backup_dir"
        fi
        
        # 创建目录并解压
        mkdir -p ~/.openclaw
        echo "解压中... (完整配置，请耐心等待)"
        tar -xzf ~/openclaw_full_config.tar.gz -C ~/.openclaw
        
        # 清理临时文件
        rm ~/openclaw_full_config.tar.gz
        
        echo "✅ 解压完成!"
        echo "文件数量: $(find ~/.openclaw -type f | wc -l)"
        echo "目录大小: $(du -sh ~/.openclaw | cut -f1)"
        
        # 设置权限
        echo ""
        echo "🔧 设置文件权限..."
        chmod -R 755 ~/.openclaw
        find ~/.openclaw -name "*.sh" -exec chmod +x {} \;
        find ~/.openclaw -name "*.js" -exec chmod +x {} \;
        
        echo "✅ 权限设置完成!"
        echo ""
        echo "🎉 完整配置复制完成!"
    else
        echo "❌ 配置包不存在"
    fi
    
    echo "================================"
EOF
}

# 主执行流程
echo "🎯 开始完整配置复制流程"
echo "================================"

# 1. 检查设备
if ! check_device; then
    exit 1
fi

# 2. 创建配置包
if ! create_config_package; then
    exit 1
fi

# 3. 传输配置包
if ! transfer_config; then
    exit 1
fi

# 4. 解压配置
if ! extract_on_target; then
    exit 1
fi

echo ""
echo "🎊 完整配置复制流程完成!"
echo "目标设备现在拥有与本机完全一致的 OpenClaw 配置"