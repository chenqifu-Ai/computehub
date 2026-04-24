# 配置版本控制指南

## 🎯 目标
建立完整的配置文件版本控制系统，支持：
- ✅ 自动记录配置变更
- ✅ 创建时间点快照  
- ✅ 回退到任意历史状态
- ✅ 变更日志追踪

## 📁 系统结构
```
config/
├── version_control/
│   ├── README.md                 # 系统说明
│   ├── create_snapshot.py        # 创建快照
│   ├── rollback_to_snapshot.py   # 回退配置
│   ├── manage_config.py          # 统一管理入口
│   ├── changelog.json            # 变更日志
│   ├── current_state.json        # 当前状态摘要
│   └── snapshots/                # 快照存储目录
│       └── snapshot_2026-03-26T18-27-11-320545/
│           ├── email.conf
│           ├── 163_email.conf
│           └── ...
├── email.conf                    # QQ邮箱配置
├── 163_email.conf                # 163邮箱配置
└── ...                           # 其他配置文件
```

## 🚀 使用方法

### 1. 创建快照（推荐在重要变更前执行）
```bash
cd /root/.openclaw/workspace/config/version_control
python3 manage_config.py snapshot "描述变更内容"
```

### 2. 查看可用快照
```bash
python3 manage_config.py list
```

### 3. 回退到指定快照
```bash
# 预览回退操作（不实际执行）
python3 manage_config.py rollback <快照ID> --dry-run

# 实际执行回退
python3 manage_config.py rollback <快照ID>
```

### 4. 查看当前状态
```bash
python3 manage_config.py status
```

## 🔒 安全特性
- **自动备份**: 每次回退前自动创建当前状态备份
- **预览模式**: 支持 `--dry-run` 参数预览回退操作
- **完整日志**: 所有变更都有详细记录和时间戳
- **文件完整性**: 使用MD5哈希验证文件一致性

## 📝 最佳实践
1. **重要变更前**：总是先创建快照
2. **定期快照**：建议每天或每周创建一次基准快照
3. **描述清晰**：快照描述要说明变更内容
4. **测试回退**：使用 `--dry-run` 先预览再执行

## 💡 示例场景

### 场景1：邮箱配置更新后出现问题
```bash
# 1. 创建更新前的快照
python3 manage_config.py snapshot "邮箱配置更新前"

# 2. 更新配置...
# 3. 发现问题，回退到安全状态
python3 manage_config.py rollback snapshot_2026-03-26T18-27-11-320545
```

### 场景2：批量配置变更
```bash
# 变更前创建快照
python3 manage_config.py snapshot "批量更新模型配置"

# 如果一切正常，可以保留
# 如果有问题，立即回退
```

## 📊 当前状态
- **最新快照**: `snapshot_2026-03-26T18-27-11-320545`
- **创建时间**: 2026-03-26 18:27:11
- **描述**: Initial snapshot after email test
- **跟踪文件**: 5个配置文件

---
*系统已就绪，可以随时使用版本控制功能*