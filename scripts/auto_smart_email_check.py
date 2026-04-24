#!/usr/bin/env python3
"""
自动智能邮件检查脚本 - 定时自动运行
"""

import asyncio
import sys
import os

# 添加代码目录到路径
sys.path.append('/root/.openclaw/workspace/ai_agent/code')

from smart_email_command_executor import SmartEmailCommandExecutor

async def main():
    """主函数"""
    print("🤖 自动智能邮件检查启动")
    print("=" * 50)
    
    try:
        executor = SmartEmailCommandExecutor()
        results = await executor.run_smart_email_check()
        
        if results:
            print(f"\n✅ 自动处理完成，处理了 {len(results)} 封邮件")
        else:
            print("\n📭 没有需要处理的邮件")
            
    except Exception as e:
        print(f"❌ 自动检查失败: {e}")
        
    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(main())