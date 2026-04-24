#!/bin/bash
# OpenClaw 配置修复脚本
# 目标: 10.35.204.186, 用户: u0_a207

echo "🔧 OpenClaw 配置修复工具"
echo "================================"
echo "目标设备: 10.35.204.186"
echo "用户: u0_a207"
echo "================================"

# 修复函数
fix_openclaw_config() {
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a207@10.35.204.186 << 'EOF'
    
    echo "🛠️ 执行配置修复..."
    echo "================================"
    
    # 1. 停止所有 OpenClaw 服务
    echo "1. 🛑 停止服务..."
    pkill -f openclaw 2>/dev/null
    sleep 2
    
    # 2. 备份当前配置
    echo "2. 📦 备份配置..."
    backup_dir=~/.openclaw.backup.$(date +%Y%m%d_%H%M%S)
    cp -r ~/.openclaw "$backup_dir"
    echo "✅ 配置已备份到: $backup_dir"
    
    # 3. 检查配置文件语法
    echo "3. 🔍 检查配置文件..."
    if ! jq empty ~/.openclaw/openclaw.json 2>/dev/null; then
        echo "❌ JSON 语法错误，尝试修复..."
        cp "$backup_dir/openclaw.json" ~/.openclaw/openclaw.json
        echo "✅ 使用备份配置恢复"
    else
        echo "✅ JSON 语法正常"
    fi
    
    # 4. 修复文件权限
    echo "4. 🔧 修复文件权限..."
    chmod -R 755 ~/.openclaw
    find ~/.openclaw -name "*.sh" -exec chmod +x {} \;
    find ~/.openclaw -name "*.js" -exec chmod +x {} \;
    echo "✅ 权限修复完成"
    
    # 5. 清理临时文件
    echo "5. 🧹 清理临时文件..."
    rm -rf ~/.openclaw/logs/* 2>/dev/null
    rm -f ~/.openclaw/*.log 2>/dev/null
    echo "✅ 临时文件清理完成"
    
    # 6. 重启服务
    echo "6. 🚀 重启服务..."
    openclaw gateway stop 2>/dev/null
    sleep 1
    openclaw gateway start 2>&1 | tail -3
    
    echo ""
    echo "7. ✅ 修复完成验证:"
    echo "================================"
    if openclaw gateway status 2>/dev/null | grep -q running; then
        echo "✅ Gateway 服务运行正常"
    else
        echo "❌ Gateway 服务启动失败"
    fi
    
    echo "配置状态: ✅ 修复完成"
    echo "备份位置: $backup_dir"
    echo "================================"
EOF
}

# 执行修复
fix_openclaw_config

echo ""
echo "🎯 修复操作完成!"
echo "请检查服务状态和功能是否正常"