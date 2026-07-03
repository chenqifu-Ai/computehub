# Knowledge: Git记忆管理规划 — 核心文件跟踪/垃圾文件排除
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Git, 记忆管理, .gitignore, 文件跟踪, 规划
> Timestamp: 2026-07-02T12:23:16+08:00

## Content

## 核心问题
1. 核心记忆文件未纳入git管理
2. 大量临时/测试文件污染git status
3. 无.gitignore或不足

## 应对
- .gitignore 排除 deploy/*, node_modules/, __pycache__/, *.pyc, .env
- git add 精确加核心文件，不用 git add .
- 核心文件必须跟踪：AGENTS.md, SOUL.md, SOP.md, MEMORY.md, TOOLS.md, config/

完整文档: memory/topics/技术经验/git管理规划.md
