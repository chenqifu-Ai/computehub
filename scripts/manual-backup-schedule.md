# ⏰ OpenClaw 手动备份调度方案

## 📱 Termux环境限制说明

由于Termux环境限制，无法使用标准的`cron`服务。采用以下替代方案：

## 🔄 备份执行方式

### 1. 手动触发备份（推荐）
```bash
# 立即执行备份
/root/.openclaw/workspace/scripts/backup-system.sh

# 每日手动执行（建议早上）
echo "每日备份已执行" >> /root/.openclaw/backups/last_run.log
```

### 2. Termux定时任务替代
```bash
# 使用Termux的定时任务功能（如果可用）
termux-job-scheduler --periodic --period 86400000 --persisted true \
    --script /root/.openclaw/workspace/scripts/backup-system.sh
```

### 3. Systemd定时任务（标准Linux）
```bash
# 启用systemd定时器
systemctl enable openclaw-backup.timer
systemctl start openclaw-backup.timer

# 查看状态
systemctl status openclaw-backup.timer
```

## 📅 备份时间安排

### 建议执行时间
- **每日**: 早上 02:00 (自动化)
- **每周**: 周日 03:00 (完整备份)  
- **变更后**: 立即执行 (重要变更)

### 手动执行提醒
```bash
# 每日提醒脚本
#!/bin/bash
echo "⏰ 提醒: 请执行每日备份"
echo "命令: /root/.openclaw/workspace/scripts/backup-system.sh"
```

## 📊 备份状态监控

### 检查最后一次备份
```bash
# 查看最新备份文件
ls -la /root/.openclaw/backups/snapshots/ | tail -1

# 检查备份时间
stat /root/.openclaw/backups/last_backup_success 2>/dev/null || echo "需要执行备份"
```

### 备份健康检查
```bash
# 每日检查脚本
if [ -f /root/.openclaw/backups/last_backup_success ]; then
    echo "✅ 备份系统正常"
else
    echo "❌ 需要执行备份"
    /root/.openclaw/workspace/scripts/backup-system.sh
fi
```

## 🚨 应急方案

### 定时任务失败处理
1. **手动执行备份**
2. **检查磁盘空间**
3. **验证脚本权限**
4. **查看错误日志**

### 恢复测试
```bash
# 每月测试恢复流程
tar -tzf /root/.openclaw/backups/snapshots/latest_backup.tar.gz | head -5
```

## 🔧 维护指南

### 日常维护
- 每日手动执行备份
- 检查备份文件完整性  
- 清理过期备份文件
- 更新备份策略文档

### 故障处理
- 备份失败: 查看日志并重试
- 磁盘满: 清理旧备份
- 权限问题: 检查文件权限

---
**适用环境**: Termux Android
**备份策略**: 每日手动执行 + 变更触发
**监控方式**: 人工检查 + 日志监控