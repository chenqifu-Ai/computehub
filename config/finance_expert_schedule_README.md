# 📅 财务专家执行频率配置

## 当前配置
- **执行频率**: 每天一次
- **执行时间**: 上午9:00
- **任务内容**: 财神爷（财务专家）财务分析报告

## 修改历史
- **2026-04-08 05:44**: 从每2小时改为每天执行一次
- **修改原因**: 用户要求减少执行频率

## 调度命令
```bash
# 每天上午9点执行
0 9 * * * python3 /root/.openclaw/workspace/ai_agent/code/expert_scripts/finance_expert_analysis.py
```

## 配置文件位置
- 主配置: `/root/.openclaw/workspace/config/finance_expert_schedule.json`
- 任务脚本: `/root/.openclaw/workspace/ai_agent/code/expert_scripts/finance_expert_analysis.py`

## 恢复说明
如需恢复每2小时执行，请修改cron表达式为: `0 */2 * * *`
