#!/bin/bash
# OpenClaw 备份定时任务设置脚本 - Termux兼容版本

echo "⏰ 设置OpenClaw定时备份任务"
echo "=============================="

# 检查Termux环境
if [ -d "/data/data/com.termux" ]; then
    echo "📱 检测到Termux环境"
    
    # 创建Termux定时任务目录
    TERMUX_CRON_DIR="/data/data/com.termux/files/usr/var/spool/cron/crontabs"
    mkdir -p "$TERMUX_CRON_DIR"
    
    # 设置每日备份任务
    CRON_JOB="0 2 * * * /root/.openclaw/workspace/scripts/backup-system.sh > /root/.openclaw/backups/logs/cron.log 2>&1"
    
    # 添加到crontab
    (crontab -l 2>/dev/null | grep -v "backup-system.sh"; echo "$CRON_JOB") | crontab -
    
    echo "✅ Termux定时任务设置完成"
    echo "📅 每日备份时间: 02:00"
    
else
    echo "💻 标准Linux环境"
    
    # 设置systemd定时任务
    SYSTEMD_SERVICE="/etc/systemd/system/openclaw-backup.service"
    SYSTEMD_TIMER="/etc/systemd/system/openclaw-backup.timer"
    
    # 创建service文件
    cat > "$SYSTEMD_SERVICE" <<EOF
[Unit]
Description=OpenClaw Daily Backup
After=network.target

[Service]
Type=oneshot
ExecStart=/root/.openclaw/workspace/scripts/backup-system.sh
User=root

[Install]
WantedBy=multi-user.target
EOF

    # 创建timer文件
    cat > "$SYSTEMD_TIMER" <<EOF
[Unit]
Description=Run OpenClaw backup daily at 2AM
Requires=openclaw-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 启用定时任务
    systemctl enable openclaw-backup.timer
    systemctl start openclaw-backup.timer
    
    echo "✅ Systemd定时任务设置完成"
    echo "📅 每日备份时间: 02:00"
fi

# 显示当前定时任务
echo ""
echo "📋 当前定时任务:"
crontab -l 2>/dev/null || echo "无cron任务"

# 测试立即执行一次
echo ""
echo "🧪 测试备份任务..."
/root/.openclaw/workspace/scripts/backup-system.sh

echo ""
echo "=============================="
echo "🎯 定时备份设置完成!"
echo "下次备份: 今日 02:00"
echo "日志位置: /root/.openclaw/backups/logs/cron.log"
echo "=============================="