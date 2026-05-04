# 🔐 OpenClaw 备份系统规范

## 🎯 备份策略

### 1. 每日增量备份
- **时间**: 每天凌晨 2:00
- **保留**: 7天
- **内容**: 核心配置、工作区、扩展
- **位置**: `/root/.openclaw/backups/snapshots/`

### 2. 每周完整备份  
- **时间**: 每周日凌晨 3:00
- **保留**: 30天
- **内容**: 完整系统状态
- **验证**: MD5校验和验证

### 3. 变更触发备份
- **触发条件**: 配置变更、扩展安装、重大更新
- **保留**: 14天
- **即时执行**: 变更后立即备份

## 📁 备份内容

### 核心资产
```
/root/.openclaw/workspace/    # 工作区文件
/root/.openclaw/extensions/   # 扩展插件  
/root/.openclaw/config/       # 配置文件
/root/.openclaw/agents/       # 智能体配置
```

### 排除内容
```
node_modules/    # 依赖包
.git/            # 版本控制
tmp/             # 临时文件  
logs/            # 日志文件
```

## 🛡️ 备份完整性保障

### 验证机制
1. **MD5校验**: 每个备份文件生成MD5校验和
2. **大小验证**: 检查备份文件大小合理性
3. **日志记录**: 详细记录备份过程
4. **元数据存储**: 备份信息JSON记录

### 监控告警
- ✅ 备份成功通知
- ❌ 备份失败告警
- 📊 备份状态监控

## 🔄 恢复流程

### 紧急恢复
```bash
# 解压最新备份
tar -xzf /root/.openclaw/backups/snapshots/openclaw_backup_最新时间戳.tar.gz -C /

# 验证恢复
md5sum -c backup_metadata.json
```

### 选择性恢复
```bash
# 恢复特定目录
tar -xzf backup_file.tar.gz -C /root/.openclaw/ workspace/
```

## 📊 备份状态管理

### 状态文件
- `last_backup_success`: 最后成功备份时间戳
- `backup_metadata.json`: 备份元数据记录
- `backup.log`: 备份操作日志

### 健康检查
```bash
# 检查备份状态
if [ -f /root/.openclaw/backups/last_backup_success ]; then
    echo "✅ 备份系统正常"
else
    echo "❌ 备份可能存在问题"
fi
```

## 🚨 应急预案

### 备份失败处理
1. 检查磁盘空间
2. 验证目录权限  
3. 查看备份日志
4. 手动执行备份

### 恢复测试
- 定期测试恢复流程
- 验证备份文件完整性
- 更新恢复文档

## 🔧 维护指南

### 日常维护
- 监控备份任务执行
- 清理过期备份
- 检查备份日志
- 更新备份策略

### 故障处理
- 备份失败: 检查日志并重试
- 恢复失败: 使用更早备份
- 磁盘满: 清理旧备份释放空间

---
**最后更新**: 2026-04-11  
**生效版本**: v1.0.0
**备份系统**: 已部署并运行