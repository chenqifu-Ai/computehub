# 配置版本控制系统

本目录用于跟踪所有重要配置文件的变更历史，支持回退到任意时间点。

## 目录结构
- `snapshots/` - 配置快照存储目录
- `changelog.json` - 变更日志记录
- `current_state.json` - 当前配置状态摘要

## 使用方法
1. **创建快照**: 运行 `create_snapshot.py` 创建当前配置的时间点快照
2. **查看历史**: 查看 `changelog.json` 了解变更历史
3. **回退配置**: 运行 `rollback_to_snapshot.py <timestamp>` 回退到指定时间点

## 支持的配置文件
- email.conf (QQ邮箱配置)
- 163_email.conf (163邮箱配置)
- model.conf (模型配置)
- company_account.json (公司账户配置)
- 其他重要的配置文件