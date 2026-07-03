# Knowledge: Git记忆管理系统规范 v2.0 — 文件查找/写入/提交
> Type: skill
> Source: 小智
> Confidence: 0.9
> TTL: 30 days
> Tags: Git, 记忆系统, 文件查找, 规范, 搜索技巧
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 核心理念
Git不是版本控制工具，是记忆系统本身

## 文件查找流程（最高优先级）
收到任务 → git ls-files | grep 关键词 → 找到 → 读取
否则 → git grep 关键词 → 找到 → 读取
否则 → find 文件系统 → 确认

## 常用命令
git ls-files | grep "关键词"  — 按文件名搜索
git grep -l "关键词"  — 按内容搜索
git log --all --oneline --grep="关键词"  — 按提交历史
git log --oneline -- <文件路径>  — 查看文件修改历史

## 记忆写入流程
学习/发现 → 写入文件 → git add → git commit → 完成

## commit规范
日常记录: git commit -m "记录: <主题> - <具体发现>"
标准发布: git commit -m "📝 STD-xxx: <标题>"
每日归档: 每天结束时提交当日记忆文件

完整文档: memory/topics/技术经验/git管理规范.md
