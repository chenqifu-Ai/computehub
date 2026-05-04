# Web Automation 技能

## 创建时间
2026-03-17

## 功能
- 自动点击、填写表单
- 网页数据抓取
- 登录流程自动化
- 搜索、截图

## 安装位置
`/root/.openclaw/workspace/skills/web-automation/`

## 每日更新
Cron 任务: `0 4 * * *` (每天凌晨 4 点)
脚本: `scripts/update_daily.sh`

## 来源
- page-agent: https://github.com/nicepkg/page-agent
- browser-automation: https://github.com/nardwang2026/openclaw-browser-automation-skill
- manus: https://github.com/mvanhorn/clawdbot-skill-manus

## 使用方法
1. 启动 Chrome 调试模式: `chrome --remote-debugging-port=9222`
2. 使用脚本: `python3 scripts/browser_tool.py <command>`
3. 或直接说: "搜索xxx", "打开xxx", "抓取xxx数据"