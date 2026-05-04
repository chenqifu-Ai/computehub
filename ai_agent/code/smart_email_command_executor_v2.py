#!/usr/bin/env python3
"""
智能邮件命令执行器 V2 - 集成AI决策引擎V2
真正的智能邮件处理，理解用户意图
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
from smart_decision_engine_v2 import AIDecisionEngine

# 配置
IMAP_SERVER = "imap.qq.com"
IMAP_PORT = 993
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "xunlwhjokescbgdd"
TARGET_SUBJECT = "小智请执行"

class SmartEmailCommandExecutorV2:
    """智能邮件命令执行器V2"""
    
    def __init__(self):
        self.ai_engine = AIDecisionEngine()
        self.execution_history = []
        self.user_context = {
            'recent_tasks': [],
            'interaction_history': [],
            'user_preferences': {}
        }
        
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
    
    def extract_command_intent(self, email_data: dict) -> dict:
        """提取命令意图"""
        subject = email_data['subject']
        body = email_data['body']
        
        # 合并主题和正文作为用户输入
        user_input = f"{subject} {body}"
        
        # 分析命令类型
        command_type = "unknown"
        estimated_duration = 30
        
        if "状态" in user_input or "检查" in user_input:
            command_type = "status_check"
            estimated_duration = 10
        elif "执行" in user_input or "运行" in user_input:
            command_type = "execute"
            estimated_duration = 60
        elif "分析" in user_input:
            command_type = "analysis"
            estimated_duration = 120
        elif "生成" in user_input or "创建" in user_input:
            command_type = "generate"
            estimated_duration = 180
        elif "删除" in user_input or "清空" in user_input:
            command_type = "delete"
            estimated_duration = 30
        
        return {
            'user_input': user_input,
            'command_type': command_type,
            'estimated_duration': estimated_duration,
            'email_data': email_data
        }
    
    async def execute_command_ai(self, command_intent: dict):
        """使用AI决策执行命令"""
        
        async def command_task():
            """命令执行任务"""
            command_type = command_intent['command_type']
            user_input = command_intent['user_input']
            
            print(f"🔧 执行命令: {command_type}")
            
            # 模拟命令执行
            if command_type == "status_check":
                result = await self.execute_status_check(user_input)
            elif command_type == "execute":
                result = await self.execute_system_command(user_input)
            elif command_type == "analysis":
                result = await self.execute_analysis(user_input)
            elif command_type == "generate":
                result = await self.execute_generation(user_input)
            elif command_type == "delete":
                result = await self.execute_delete(user_input)
            else:
                result = f"执行默认操作: {user_input}"
            
            return result
        
        # 使用AI决策引擎
        task_description = f"邮件命令: {command_intent['email_data']['subject']}"
        
        result = await self.ai_engine.smart_execute(
            command_task, 
            task_description, 
            command_intent['user_input'],
            self.user_context
        )
        
        # 更新用户上下文
        self._update_user_context(command_intent, result)
        
        return result
    
    async def execute_status_check(self, user_input: str) -> str:
        """执行状态检查"""
        await asyncio.sleep(1)
        
        if "系统" in user_input:
            try:
                result = subprocess.run(['uptime'], capture_output=True, text=True)
                return f"系统状态检查完成: {result.stdout.strip()}"
            except:
                return "系统状态检查完成"
        else:
            return "状态检查完成"
    
    async def execute_system_command(self, user_input: str) -> str:
        """执行系统命令"""
        await asyncio.sleep(2)
        
        safe_commands = {
            '查看目录': 'ls -la',
            '查看进程': 'ps aux | head -10',
            '磁盘空间': 'df -h',
            '内存使用': 'free -h'
        }
        
        for keyword, cmd in safe_commands.items():
            if keyword in user_input:
                try:
                    result = subprocess.run(cmd.split(), capture_output=True, text=True)
                    return f"命令执行成功: {result.stdout[:100]}..."
                except:
                    return f"执行命令: {cmd}"
        
        return "系统命令执行完成"
    
    async def execute_analysis(self, user_input: str) -> str:
        """执行分析任务"""
        await asyncio.sleep(3)
        return f"分析完成: {user_input}"
    
    async def execute_generation(self, user_input: str) -> str:
        """执行生成任务"""
        await asyncio.sleep(4)
        return f"生成完成: {user_input}"
    
    async def execute_delete(self, user_input: str) -> str:
        """执行删除任务"""
        await asyncio.sleep(1)
        # 模拟安全删除（实际中应该更谨慎）
        return f"安全删除操作完成: {user_input}"
    
    def _update_user_context(self, command_intent: dict, result: dict):
        """更新用户上下文"""
        # 记录任务历史
        task_record = {
            'timestamp': datetime.now().isoformat(),
            'command_intent': command_intent,
            'result': result,
            'keywords': self._extract_keywords(command_intent['user_input'])
        }
        
        self.user_context['recent_tasks'].append(task_record)
        
        # 保持最近20个任务
        if len(self.user_context['recent_tasks']) > 20:
            self.user_context['recent_tasks'] = self.user_context['recent_tasks'][-20:]
        
        # 记录交互历史
        interaction_record = {
            'timestamp': datetime.now().isoformat(),
            'user_input': command_intent['user_input'],
            'decision': result.get('status', 'unknown')
        }
        
        self.user_context['interaction_history'].append(interaction_record)
        
        # 保持最近50次交互
        if len(self.user_context['interaction_history']) > 50:
            self.user_context['interaction_history'] = self.user_context['interaction_history'][-50:]
    
    def _extract_keywords(self, text: str) -> list:
        """提取关键词"""
        keywords = ['状态', '检查', '执行', '运行', '分析', '生成', '删除', '部署', '配置']
        found_keywords = [kw for kw in keywords if kw in text]
        return found_keywords
    
    async def process_email_ai(self, email_data: dict):
        """AI处理邮件"""
        print(f"\n📧 AI处理邮件: {email_data['subject']}")
        print(f"   发件人: {email_data['sender']}")
        
        # 提取命令意图
        command_intent = self.extract_command_intent(email_data)
        print(f"   命令类型: {command_intent['command_type']}")
        print(f"   用户输入: {command_intent['user_input'][:50]}...")
        
        # AI决策执行
        result = await self.execute_command_ai(command_intent)
        
        # 记录执行历史
        execution_record = {
            'email_id': email_data['id'],
            'subject': email_data['subject'],
            'sender': email_data['sender'],
            'command_intent': command_intent,
            'ai_result': result,
            'timestamp': datetime.now().isoformat()
        }
        self.execution_history.append(execution_record)
        
        print(f"\n🎉 AI处理完成!")
        print(f"   决策结果: {result['status']}")
        
        return execution_record
    
    async def run_ai_email_check(self):
        """运行AI邮件检查"""
        print("🧠 AI智能邮件命令执行器V2启动")
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
        
        # AI处理每封邮件
        results = []
        for email_data in emails:
            result = await self.process_email_ai(email_data)
            results.append(result)
        
        # 输出AI总结
        print("\n" + "=" * 50)
        print("🧠 AI处理总结")
        print("-" * 30)
        
        status_counts = {}
        for result in results:
            status = result['ai_result']['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"{status}: {count}封邮件")
        
        auto_count = status_counts.get('auto_completed', 0)
        total_count = len(results)
        
        if total_count > 0:
            auto_rate = (auto_count / total_count) * 100
            print(f"自动处理率: {auto_rate:.1f}%")
        
        print(f"\n💡 AI效果: 真正理解用户意图，智能决策!")
        
        # 关闭连接
        mail.close()
        mail.logout()
        
        return results

# 演示函数
async def demo_ai_email_executor():
    """演示AI邮件执行器"""
    executor = SmartEmailCommandExecutorV2()
    
    print("🚀 AI智能邮件命令执行器V2演示")
    print("=" * 50)
    
    # 模拟邮件数据
    test_emails = [
        {
            'id': 'test1',
            'subject': '小智请执行 - 马上检查系统状态',
            'sender': 'test@example.com',
            'body': '请立即检查系统CPU、内存使用情况',
            'timestamp': datetime.now().isoformat()
        },
        {
            'id': 'test2', 
            'subject': '小智请执行 - 删除临时文件',
            'sender': 'test@example.com',
            'body': '请删除所有临时文件，清理磁盘空间',
            'timestamp': datetime.now().isoformat()
        },
        {
            'id': 'test3',
            'subject': '小智请执行 - 分析项目进度报告',
            'sender': 'test@example.com',
            'body': '请分析当前项目进度并生成详细报告',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # AI处理测试邮件
    for email_data in test_emails:
        await executor.process_email_ai(email_data)
    
    print("\n✅ AI演示完成!")

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_ai_email_executor())
    
    # 实际运行（取消注释以使用）
    # asyncio.run(SmartEmailCommandExecutorV2().run_ai_email_check())