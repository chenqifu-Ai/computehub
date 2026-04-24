#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置每日深度思考定时任务
每天23:00自动执行深度思考分析
"""

import json
import os
from datetime import datetime

class DailyThinkingCron:
    def __init__(self):
        self.workspace = "/root/.openclaw/workspace"
        self.script_dir = os.path.join(self.workspace, "ai_agent", "code")
        self.results_dir = os.path.join(self.workspace, "ai_agent", "results")
        
    def create_thinking_script(self):
        """创建深度思考分析脚本"""
        script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日深度思考分析脚本
自动分析当天的工作表现和成长
"""

import os
import json
from datetime import datetime, timedelta
import re

class DailyThinkingAnalyzer:
    def __init__(self):
        self.workspace = "/root/.openclaw/workspace"
        self.memory_dir = os.path.join(self.workspace, "memory")
        self.memory_file = os.path.join(self.workspace, "MEMORY.md")
        
    def get_today_date(self):
        """获取今天的日期"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def get_recent_days(self, days=1):
        """获取最近几天的日期"""
        today = datetime.now()
        dates = []
        for i in range(days):
            date = today - timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        return dates
    
    def read_memory_files(self, dates):
        """读取指定日期的记忆文件"""
        memories = {}
        for date in dates:
            file_path = os.path.join(self.memory_dir, f"{date}.md")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        memories[date] = f.read()
                except:
                    memories[date] = f"无法读取文件: {file_path}"
            else:
                memories[date] = f"文件不存在: {file_path}"
        return memories
    
    def read_long_term_memory(self):
        """读取长期记忆"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return "无法读取长期记忆文件"
        return "长期记忆文件不存在"
    
    def analyze_daily_work(self, memories):
        """分析每日工作"""
        analysis = {
            "tasks_completed": [],
            "challenges_faced": [],
            "solutions_found": [],
            "learning_points": [],
            "sop_violations": [],
            "efficiency_issues": []
        }
        
        for date, content in memories.items():
            # 分析已完成的任务
            if "已完成" in content or "完成" in content:
                task_pattern = r'[-*•]\\s*(.*?已完成|.*?完成)'
                tasks = re.findall(task_pattern, content)
                analysis["tasks_completed"].extend([f"{date}: {task}" for task in tasks])
            
            # 分析遇到的挑战
            if "问题" in content or "错误" in content or "挑战" in content:
                challenge_pattern = r'[-*•]\\s*(.*?[问题错误挑战].*?[。\\n])'
                challenges = re.findall(challenge_pattern, content)
                analysis["challenges_faced"].extend([f"{date}: {challenge}" for challenge in challenges])
            
            # 分析解决方案
            if "解决" in content or "修复" in content:
                solution_pattern = r'[-*•]\\s*(.*?[解决修复].*?[。\\n])'
                solutions = re.findall(solution_pattern, content)
                analysis["solutions_found"].extend([f"{date}: {solution}" for solution in solutions])
            
            # 分析学习点
            if "学习" in content or "教训" in content or "经验" in content:
                learning_pattern = r'[-*•]\\s*(.*?[学习教训经验].*?[。\\n])'
                learnings = re.findall(learning_pattern, content)
                analysis["learning_points"].extend([f"{date}: {learning}" for learning in learnings])
            
            # 分析SOP违规
            if "SOP" in content or "违规" in content or "流程" in content:
                sop_pattern = r'[-*•]\\s*(.*?[SOP违规流程].*?[。\\n])'
                sop_issues = re.findall(sop_pattern, content)
                analysis["sop_violations"].extend([f"{date}: {issue}" for issue in sop_issues])
            
            # 分析效率问题
            if "效率" in content or "批量" in content or "逐个" in content:
                efficiency_pattern = r'[-*•]\\s*(.*?[效率批量逐个].*?[。\\n])'
                efficiency_issues = re.findall(efficiency_pattern, content)
                analysis["efficiency_issues"].extend([f"{date}: {issue}" for issue in efficiency_issues])
        
        return analysis
    
    def generate_daily_report(self, analysis):
        """生成每日报告"""
        today = self.get_today_date()
        
        report = f"""# 📊 每日深度思考报告 ({today})

## 🎯 今日工作概览
- 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 任务完成数: {len(analysis['tasks_completed'])}
- 遇到挑战数: {len(analysis['challenges_faced'])}
- 解决方案数: {len(analysis['solutions_found'])}
- 学习收获数: {len(analysis['learning_points'])}

## ✅ 今日完成的任务
"""
        
        for task in analysis["tasks_completed"][:5]:  # 最多显示5个
            report += f"- {task}\\n"
        
        report += f"""
## ⚠️ 今日遇到的挑战
"""
        for challenge in analysis["challenges_faced"][:5]:
            report += f"- {challenge}\\n"
        
        report += f"""
## 🔧 今日解决方案
"""
        for solution in analysis["solutions_found"][:5]:
            report += f"- {solution}\\n"
        
        report += f"""
## 📚 今日学习收获
"""
        for learning in analysis["learning_points"][:5]:
            report += f"- {learning}\\n"
        
        report += f"""
## ⛔ SOP合规检查
"""
        if analysis["sop_violations"]:
            for violation in analysis["sop_violations"]:
                report += f"- ❌ {violation}\\n"
        else:
            report += "- ✅ 今日无SOP违规记录\\n"
        
        report += f"""
## ⏱️ 效率优化建议
"""
        if analysis["efficiency_issues"]:
            for issue in analysis["efficiency_issues"]:
                report += f"- 💡 {issue}\\n"
        else:
            report += "- ✅ 今日无效率问题记录\\n"
        
        report += f"""
## 💡 明日改进建议
"""
        
        # 根据分析生成建议
        if analysis["sop_violations"]:
            report += "- 加强SOP流程执行纪律\\n"
        if analysis["efficiency_issues"]:
            report += "- 优化批量操作流程\\n"
        if analysis["challenges_faced"] and not analysis["solutions_found"]:
            report += "- 加强问题解决能力\\n"
        
        report += """
## 📈 成长指标
- 任务完成率: 保持或提升
- 问题解决率: 争取100%解决
- 学习转化率: 持续积累经验
- SOP合规率: 目标100%

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*分析者: 小智*
*执行方式: 定时任务自动化*
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return report
    
    def save_report(self, report):
        """保存报告到文件"""
        today = self.get_today_date()
        report_file = os.path.join(self.memory_dir, f"daily-thinking-{today}.md")
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            return report_file
        except Exception as e:
            return f"保存报告失败: {str(e)}"
    
    def send_notification(self, report_file):
        """发送通知（预留接口）"""
        # 这里可以集成邮件、消息推送等功能
        print(f"深度思考报告已生成: {report_file}")
        return True
    
    def run(self):
        """执行每日深度思考分析"""
        print("开始执行每日深度思考分析...")
        
        # 1. 获取今天日期
        today = self.get_today_date()
        print(f"分析日期: {today}")
        
        # 2. 读取记忆文件
        dates = self.get_recent_days(1)  # 只分析今天
        memories = self.read_memory_files(dates)
        print(f"读取到{len(memories)}天的记忆文件")
        
        # 3. 分析工作
        analysis = self.analyze_daily_work(memories)
        print(f"分析完成: {len(analysis['tasks_completed'])}个任务, {len(analysis['challenges_faced'])}个挑战")
        
        # 4. 生成报告
        report = self.generate_daily_report(analysis)
        
        # 5. 保存报告
        report_file = self.save_report(report)
        
        # 6. 发送通知
        self.send_notification(report_file)
        
        return {
            "success": True,
            "date": today,
            "tasks_found": len(analysis["tasks_completed"]),
            "challenges_found": len(analysis["challenges_faced"]),
            "report_file": report_file,
            "report_preview": report[:500] + "..." if len(report) > 500 else report
        }

if __name__ == "__main__":
    analyzer = DailyThinkingAnalyzer()
    result = analyzer.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
'''
        
        script_path = os.path.join(self.script_dir, "daily_thinking_analysis.py")
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 设置执行权限
            os.chmod(script_path, 0o755)
            
            print(f"✅ 深度思考脚本已创建: {script_path}")
            return script_path
        except Exception as e:
            print(f"❌ 创建脚本失败: {e}")
            return None
    
    def setup_cron_job(self):
        """设置定时任务"""
        cron_config = {
            "name": "每日深度思考分析",
            "schedule": {
                "kind": "cron",
                "expr": "0 23 * * *",  # 每天23:00执行
                "tz": "Asia/Shanghai"
            },
            "payload": {
                "kind": "agentTurn",
                "message": "执行每日深度思考分析"
            },
            "sessionTarget": "isolated",
            "enabled": True
        }
        
        return cron_config
    
    def create_cron_setup_script(self):
        """创建定时任务设置脚本"""
        script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置每日深度思考定时任务
"""

import json
import subprocess
import os

def setup_daily_thinking_cron():
    """设置每日深度思考定时任务"""
    
    # 创建定时任务配置
    cron_config = {
        "name": "每日深度思考分析",
        "schedule": {
            "kind": "cron",
            "expr": "0 23 * * *",  # 每天23:00执行
            "tz": "Asia/Shanghai"
        },
        "payload": {
            "kind": "agentTurn",
            "message": "执行每日深度思考分析"
        },
        "sessionTarget": "isolated",
        "enabled": True
    }
    
    # 保存配置到文件
    config_file = "/root/.openclaw/workspace/ai_agent/code/daily_thinking_cron.json"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(cron_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 定时任务配置已保存: {config_file}")
        
        # 这里需要调用OpenClaw的cron API来设置定时任务
        # 由于权限限制，这里只生成配置，实际设置需要用户确认
        
        print("\\n📋 定时任务配置:")
        print(f"名称: {cron_config['name']}")
        print(f"时间: 每天 23:00 (北京时间)")
        print(f"任务: {cron_config['payload']['message']}")
        print(f"状态: {'启用' if cron_config['enabled'] else '禁用'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 设置定时任务失败: {e}")
        return False

if __name__ == "__main__":
    success = setup_daily_thinking_cron()
    if success:
        print("\\n🎯 定时任务设置完成!")
        print("请使用OpenClaw的cron工具激活此定时任务。")
    else:
        print("\\n❌ 定时任务设置失败!")
'''
        
        script_path = os.path.join(self.script_dir, "setup_daily_thinking_cron.py")
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            os.chmod(script_path, 0o755)
            
            print(f"✅ 定时任务设置脚本已创建: {script_path}")
            return script_path
        except Exception as e:
            print(f"❌ 创建设置脚本失败: {e}")
            return None
    
    def run(self):
        """执行设置流程"""
        print("开始设置每日深度思考定时任务...")
        
        # 1. 创建深度思考脚本
        thinking_script = self.create_thinking_script()
        if not thinking_script:
            return {"success": False, "error": "创建深度思考脚本失败"}
        
        # 2. 创建定时任务设置脚本
        setup_script = self.create_cron_setup_script()
        if not setup_script:
            return {"success": False, "error": "创建设置脚本失败"}
        
        # 3. 生成定时任务配置
        cron_config = self.setup_cron_job()
        
        # 4. 保存配置
        config_file = os.path.join(self.script_dir, "daily_thinking_cron.json")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(cron_config, f, ensure_ascii=False, indent=2)
            print(f"✅ 定时任务配置已保存: {config_file}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
        
        return {
            "success": True,
            "thinking_script": thinking_script,
            "setup_script": setup_script,
            "config_file": config_file,
            "cron_config": cron_config
        }

if __name__ == "__main__":
    setup = DailyThinkingCron()
    result = setup.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
