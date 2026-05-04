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

### AI API 配置

- **Qwen 3.6 35B (推理模型)**: http://58.23.129.98:8000/v1 (Key: sk-78sadn09bjawde123e) ⭐ 默认
- **Ollama 云端**: https://ollama.com (Key: 8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii)
- **OpenClaw 本地**: ollama/qwen3.6-35b (备选)
- **NewAPI (ai.zhangtuokeji.top)**: https://ai.zhangtuokeji.top:9090 (Key: sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl) ⭐ 当前主力
  - ⚠️ **max_tokens ≥ 1024**，推荐 2048
  - ⚠️ **content 字段永远为 null**（所有输出在 reasoning 字段）
  - ✅ 适配层已处理 fallback（读取 reasoning）
  - ✅ 响应速度 ~0.7s

### AI 使用规则

#### NewAPI qwen3.6-35b-common 规则
1. **max_tokens 必须 ≥ 1024**（推荐 2048）
2. **content 永远为 null**，适配层从 reasoning 字段读取
3. **temperature 0-1 都可用**，代码生成建议 0.7+
4. **模型 ID**: `qwen3.6-35b-common`（不是 `qwen3.6-35b`）
5. **API Key**: `sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl`
6. **Provider**: `zhangtuo-ai-common`

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
