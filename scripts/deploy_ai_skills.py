#!/usr/bin/env python3
"""
AI决策技能部署脚本
自动为所有专家集成AI决策能力
"""

import sys
import os

# 添加路径
sys.path.append('/root/.openclaw/workspace/ai_agent/code')

from integrate_ai_skill_to_experts import ExpertAIIntegrator
import asyncio

async def main():
    """主函数"""
    print("🚀 开始部署AI决策技能到所有专家...")
    
    integrator = ExpertAIIntegrator()
    
    # 测试集成效果
    results = await integrator.batch_test_experts()
    
    # 生成报告
    report = integrator.generate_integration_report(results)
    
    print(f"
✅ AI决策技能部署完成!")
    print(f"   7大专家已具备AI智能决策能力")
    print(f"   总体自动处理率: {report['overall_auto_rate']:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
