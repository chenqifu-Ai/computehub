# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Git记忆管理系统

### 🎯 Git记忆功能
- **搜索能力**: 基于Git的强大全文搜索
- **版本控制**: 完整的历史记录和追溯
- **自动提交**: 智能记忆快照和备份
- **主题分类**: 按时间和主题组织记忆

### 🔧 使用命令
```bash
# 关键词搜索
python scripts/git-memory-search.py keyword "搜索关键词"

# 提交信息搜索  
python scripts/git-memory-search.py commit "提交关键词"

# 时间范围搜索
python scripts/git-memory-search.py time --since="2026-04-20"

# 自动提交记忆
python scripts/git-memory-manager.py commit -m "记忆描述"

# 每日维护
python scripts/git-memory-manager.py maintenance

# 查看状态
python scripts/git-memory-manager.py status
```

### 📁 记忆目录结构
```
memory/
  /daily/           # 每日记忆文件
    2026-04-23.md   # 当日记录
  /topics/          # 主题记忆
    technical/      # 技术主题
    personal/       # 个人主题
  /search-index/    # 搜索索引
```

### 💡 搜索示例
```bash
# 搜索所有关于"股票"的内容
python scripts/git-memory-search.py keyword "股票"

# 搜索最近7天的记忆  
python scripts/git-memory-search.py time --since="7 days ago"

# 搜索特定文件的修改历史
python scripts/git-memory-search.py history "MEMORY.md"
```

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod

### 设备标识

- 小米小龙虾 → openclaw.local - OpenClaw网关设备
- 小米平板 → Android Termux环境 (u0_a207/123)
- Windows笔记本 → xiaomi/1234567890 - Windows开发机
- 华为手机 → u0_a46/123 - HWI-AL00型号 (IP动态变化)
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
