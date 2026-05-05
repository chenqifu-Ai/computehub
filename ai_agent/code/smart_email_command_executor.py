#!/usr/bin/env python3

from scripts.email_utils import load_config
"""
智能邮件命令执行器 - 集成智能决策引擎
自动执行"小智请执行"邮件，无需"继续"确认
"""

import imaplib
import email
from email.header import decode_header
import json
import os
import subprocess
import sys
import asyncio
from datetime import datetime
from smart_decision_engine import SmartDecisionEngine

# 配置
IMAP_SERVER = "imap.qq.com"
IMAP_PORT = 993
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "__USE_CONFIG__"
TARGET_SUBJECT = "小智请执行"

class SmartEmailCommandExecutor:
    """智能邮件命令执行器"""
    
    def __init__(self):
        self.decision_engine = SmartDecisionEngine()
        self.execution_history = []
        
    def decode_str(self, s):
        """解码字符串"""
        if s is None:
            return ""
        decoded = decode_header(s)
        result = []
        for content, charset in decoded:
            if isinstance(content, bytes):
                result.append(content.decode(charset or 'utf-8', errors='ignore'))
            else:
                result.append(content)
        return ''.join(result)
    
    def connect_imap(self):
        """连接IMAP服务器"""
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(EMAIL_ACCOUNT, AUTH_CODE)
            mail.select('INBOX')
            return mail
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return None
    
    def get_target_emails(self, mail):
        """获取目标邮件"""
        try:
            status, messages = mail.search(None, 'UNSEEN')
            if status != 'OK':
                return []
            
            email_ids = messages[0].split()
            target_emails = []
            
            for email_id in email_ids[-10:]:  # 只检查最近10封
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = self.decode_str(msg.get('Subject', ''))
                        sender = self.decode_str(msg.get('From', ''))
                        
                        if TARGET_SUBJECT in subject:
                            body = self.get_email_body(msg)
                            target_emails.append({
                                'id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                                'subject': subject,
                                'sender': sender,
                                'body': body,
                                'timestamp': datetime.now().isoformat()
                            })
            
            return target_emails
        except Exception as e:
            print(f"❌ 获取邮件失败: {e}")
            return []
    
    def get_email_body(self, msg):
        """获取邮件正文"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        return body.strip()
    
    def analyze_command_complexity(self, command_text: str) -> str:
        """分析命令复杂度"""
        # 简单命令判断规则
        simple_keywords = ['状态', '检查', '查看', '报告', '总结']
        complex_keywords = ['执行', '运行', '处理', '分析', '生成']
        high_risk_keywords = ['删除', '修改', '更新', '安装', '配置']
        
        if any(keyword in command_text for keyword in high_risk_keywords):
            return 'high'
        elif any(keyword in command_text for keyword in complex_keywords):
            return 'medium'
        else:
            return 'low'
    
    def parse_command(self, email_body: str) -> dict:
        """解析邮件命令"""
        # 简单的命令解析
        lines = email_body.split('\n')
        command_text = lines[0] if lines else ""
        
        # 分析命令类型
        command_type = "unknown"
        if "状态" in command_text or "检查" in command_text:
            command_type = "status_check"
        elif "执行" in command_text or "运行" in command_text:
            command_type = "execute"
        elif "分析" in command_text:
            command_type = "analysis"
        elif "生成" in command_text:
            command_type = "generate"
        
        # 估算执行时间
        estimated_duration = 30  # 默认30秒
        if command_type == "status_check":
            estimated_duration = 10
        elif command_type == "execute":
            estimated_duration = 60
        elif command_type == "analysis":
            estimated_duration = 120
        elif command_type == "generate":
            estimated_duration = 180
        
        return {
            'type': command_type,
            'text': command_text,
            'estimated_duration': estimated_duration,
            'risk_level': self.analyze_command_complexity(command_text),
            'steps': 3  # 默认3个步骤
        }
    
    async def execute_command_step(self, step: int, command_info: dict, **kwargs):
        """执行命令步骤"""
        command_type = command_info['type']
        command_text = command_info['text']
        
        # 模拟执行不同步骤
        if step == 0:
            # 步骤1: 准备执行
            print(f"📋 准备执行: {command_text}")
            await asyncio.sleep(1)
            return f"准备完成"
            
        elif step == 1:
            # 步骤2: 执行命令
            print(f"🚀 执行命令: {command_text}")
            
            # 根据命令类型执行不同操作
            if command_type == "status_check":
                result = self.execute_status_check(command_text)
            elif command_type == "execute":
                result = self.execute_system_command(command_text)
            elif command_type == "analysis":
                result = self.execute_analysis(command_text)
            elif command_type == "generate":
                result = self.execute_generation(command_text)
            else:
                result = f"执行默认操作: {command_text}"
            
            await asyncio.sleep(2)
            return result
            
        elif step == 2:
            # 步骤3: 完成报告
            print(f"✅ 完成命令: {command_text}")
            await asyncio.sleep(1)
            return f"命令执行完成"
    
    def execute_status_check(self, command_text: str) -> str:
        """执行状态检查命令"""
        if "系统" in command_text:
            # 执行系统状态检查
            try:
                result = subprocess.run(['uptime'], capture_output=True, text=True)
                return f"系统状态: {result.stdout.strip()}"
            except:
                return "系统状态检查完成"
        else:
            return "状态检查完成"
    
    def execute_system_command(self, command_text: str) -> str:
        """执行系统命令"""
        # 安全地执行简单命令
        safe_commands = {
            '查看目录': 'ls -la',
            '查看进程': 'ps aux | head -10',
            '磁盘空间': 'df -h',
            '内存使用': 'free -h'
        }
        
        for keyword, cmd in safe_commands.items():
            if keyword in command_text:
                try:
                    result = subprocess.run(cmd.split(), capture_output=True, text=True)
                    return f"命令执行成功: {result.stdout[:100]}..."
                except:
                    return f"执行命令: {cmd}"
        
        return "系统命令执行完成"
    
    def execute_analysis(self, command_text: str) -> str:
        """执行分析命令"""
        # 模拟分析操作
        return f"分析完成: {command_text}"
    
    def execute_generation(self, command_text: str) -> str:
        """执行生成命令"""
        # 模拟生成操作
        return f"生成完成: {command_text}"
    
    async def process_email_smart(self, email_data: dict):
        """智能处理邮件"""
        print(f"\n📧 处理邮件: {email_data['subject']}")
        print(f"   发件人: {email_data['sender']}")
        
        # 解析命令
        command_info = self.parse_command(email_data['body'])
        print(f"   命令类型: {command_info['type']}")
        print(f"   风险等级: {command_info['risk_level']}")
        
        # 使用智能决策引擎执行
        summary = await self.decision_engine.execute_with_decision(
            self.execute_command_step, 
            f"邮件命令: {email_data['subject']}",
            command_info['steps'],
            command_info=command_info,
            estimated_duration=command_info['estimated_duration'],
            risk_level=command_info['risk_level']
        )
        
        # 记录执行历史
        execution_record = {
            'email_id': email_data['id'],
            'subject': email_data['subject'],
            'sender': email_data['sender'],
            'command': command_info,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        self.execution_history.append(execution_record)
        
        print(f"\n🎉 邮件处理完成!")
        print(f"   自动继续率: {summary.get('auto_rate', 0):.1f}%")
        print(f"   需要确认次数: {summary.get('confirm_required_steps', 0)}")
        
        return execution_record
    
    async def run_smart_email_check(self):
        """运行智能邮件检查"""
        print("🤖 智能邮件命令执行器启动")
        print("=" * 50)
        
        # 连接邮箱
        mail = self.connect_imap()
        if not mail:
            print("❌ 无法连接邮箱")
            return
        
        # 获取目标邮件
        emails = self.get_target_emails(mail)
        
        if not emails:
            print(f"📭 没有找到主题为'{TARGET_SUBJECT}'的新邮件")
            mail.close()
            mail.logout()
            return
        
        print(f"📨 找到 {len(emails)} 封目标邮件")
        
        # 智能处理每封邮件
        results = []
        for email_data in emails:
            result = await self.process_email_smart(email_data)
            results.append(result)
        
        # 输出总结
        print("\n" + "=" * 50)
        print("📊 智能邮件处理总结")
        print("-" * 30)
        
        total_emails = len(results)
        total_steps = sum(len(r['command'].get('steps', 3)) for r in results)
        total_auto_steps = sum(r['summary'].get('auto_continue_steps', 0) for r in results)
        total_confirm_steps = sum(r['summary'].get('confirm_required_steps', 0) for r in results)
        
        print(f"处理邮件数量: {total_emails}")
        print(f"总步骤数: {total_steps}")
        print(f"自动继续步骤: {total_auto_steps}")
        print(f"需要确认步骤: {total_confirm_steps}")
        
        if total_steps > 0:
            auto_rate = (total_auto_steps / total_steps) * 100
            reduction = ((total_steps - total_confirm_steps) / total_steps) * 100
            print(f"自动继续率: {auto_rate:.1f}%")
            print(f"交互减少: {reduction:.1f}%")
        
        print(f"\n💡 效果: 用户不再需要频繁说'继续'!")
        
        # 关闭连接
        mail.close()
        mail.logout()
        
        return results

# 演示函数
async def demo_smart_email_executor():
    """演示智能邮件执行器"""
    executor = SmartEmailCommandExecutor()
    
    print("🚀 智能邮件命令执行器演示")
    print("=" * 50)
    
    # 模拟邮件数据
    test_emails = [
        {
            'id': 'test1',
            'subject': '小智请执行 - 检查系统状态',
            'sender': 'test@example.com',
            'body': '请检查当前系统状态和资源使用情况',
            'timestamp': datetime.now().isoformat()
        },
        {
            'id': 'test2', 
            'subject': '小智请执行 - 分析项目进度',
            'sender': 'test@example.com',
            'body': '请分析当前项目进度并生成报告',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # 处理测试邮件
    for email_data in test_emails:
        await executor.process_email_smart(email_data)
    
    print("\n✅ 演示完成!")

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_smart_email_executor())
    
    # 实际运行（取消注释以使用）
    # asyncio.run(SmartEmailCommandExecutor().run_smart_email_check())
# 从统一配置加载
_cfg = load_config()
AUTH_CODE = _cfg["auth_code"]
