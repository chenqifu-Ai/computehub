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
- **NewAPI (ai.zhangtuokeji.top)**: https://ai.zhangtuokeji.top:9090 (Key: sk-lthqkgFRv5bJIW2d9bAqwB2xWo8acV2U0fo5tFikDlBxn0nC) ⭐ 当前主力
  - ⚠️ **IP 白名单**: 只认 ECS (36.250.122.43)，Windows 等节点必须通过 **Gateway LLM Proxy** 中转
  - ⚠️ **max_tokens ≥ 1024**，推荐 2048
  - ⚠️ **content 字段永远为 null**（所有输出在 reasoning 字段）
  - ✅ 适配层已处理 fallback（读取 reasoning）
  - ✅ 响应速度 ~0.7s
- **qwen36-backup**: http://58.23.129.98:8999/v1 (Key: sk-E_Ta97lGlSDu3HZCSqiZbg)
  - 模型: qwen3.6-35b (reasoning=True)
  - 状态: 2026-05-04 记录，待确认是否接入

### AI 使用规则

#### zhangtuo-ai/qwen3.6-35b 规则（2026-06-04 更新）
1. **模型 ID**: `qwen3.6-35b`（非 `qwen3.6-35b-common`）— 支持图片输入 ⭐
2. **Provider**: `zhangtuo-ai`（非 `zhangtuo-ai-common`）
3. **API Key**: `sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB`
4. **⚠️ IP 白名单**: 仅 ECS 36.250.122.43 可直连；Windows 等走 Gateway LLM Proxy
5. **⚠️ max_tokens 必须 ≥ 1024**（推荐 2048~4096）
6. **⚠️ content 永远为 null** — 从 `reasoning` 字段读取
7. **⚠️ 图片输入** — base64 → `image_url`，参考 IMG-REC-001 v3.0
8. **temperature**: 0-1 都可用，图片识别建议 0.3，代码生成建议 0.7+

#### 废弃配置（2026-06-04 起停用）
| 旧配置 | 原因 | 替代 |
|--------|------|------|
| `qwen3.6-35b-common` | 不支持图片 | → `qwen3.6-35b` |
| `zhangtuo-ai-common` provider | 统一 | → `zhangtuo-ai` |
| `sk-3RgMq1COL9...` key | 旧 key 废弃 | → `sk-28PRiilece...` |

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
