#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC - 智能体加载测试脚本
测试所有 6 个智能体能否正常加载

创建时间：2026-04-19
作者：小智 (数据智能体)
"""

import os
import sys
import json
from datetime import datetime

# 添加框架路径
sys.path.insert(0, '/root/.openclaw/workspace/projects/chargecloud-opc/framework')

from ai_agent import AIAgent

# 智能体列表
AGENTS = [
    {
        'id': 'ceo_agent',
        'name': 'CEO 智能体',
        'role': '战略决策',
        'model': 'qwen3.5:397b'
    },
    {
        'id': 'marketing_agent',
        'name': '营销智能体',
        'role': '市场增长',
        'model': 'qwen3.5:35b'
    },
    {
        'id': 'operations_agent',
        'name': '运营智能体',
        'role': '业务执行',
        'model': 'qwen3.5:35b'
    },
    {
        'id': 'finance_agent',
        'name': '财务智能体',
        'role': '资金管控',
        'model': 'qwen3.5:35b'
    },
    {
        'id': 'data_agent',
        'name': '数据智能体',
        'role': '数据分析',
        'model': 'qwen3.5:35b'
    },
    {
        'id': 'risk_agent',
        'name': '风控智能体',
        'role': '安全合规',
        'model': 'qwen3.5:35b'
    }
]

def test_agent_load(agent_info):
    """测试单个智能体加载"""
    agent_id = agent_info['id']
    config_path = f"/root/.openclaw/workspace/projects/chargecloud-opc/agents/{agent_id}/config.yaml"
    
    print(f"\n{'='*60}")
    print(f"测试：{agent_info['name']} ({agent_id})")
    print(f"{'='*60}")
    print(f"配置文件：{config_path}")
    print(f"角色：{agent_info['role']}")
    print(f"模型：{agent_info['model']}")
    print()
    
    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在：{config_path}")
        return False
    
    print(f"✅ 配置文件存在")
    
    try:
        # 加载智能体
        print(f"正在加载智能体...")
        agent = AIAgent(config_path)
        
        # 获取状态
        status = agent.get_status()
        
        print(f"\n✅ 智能体加载成功!")
        print(f"\n智能体详情:")
        print(f"  ID:        {status['agent_id']}")
        print(f"  名称：     {status['name']}")
        print(f"  角色：     {status['role']}")
        print(f"  状态：     {status['status']}")
        print(f"  创建时间： {status['created_at']}")
        print(f"  任务队列： {status['task_queue_size']} 个任务")
        print(f"  记忆系统:")
        print(f"    - 短期记忆：{status['memory']['short_term_count']} 条")
        print(f"    - 长期记忆：{status['memory']['long_term_count']} 条")
        print(f"    - 经验库：  {status['memory']['experience_count']} 条")
        
        # 测试工具注册
        print(f"\n已注册工具:")
        for tool_name in agent.tools.tools.keys():
            print(f"  ✅ {tool_name}")
        
        # 测试执行一个简单任务
        print(f"\n🧪 测试执行简单任务...")
        task = agent.run("生成一份测试报告")
        
        print(f"任务状态：{task.status}")
        print(f"任务 ID:   {task.id}")
        print(f"错误信息：{task.error if task.error else '无'}")
        
        if task.status == 'completed':
            print(f"\n✅ 任务执行成功!")
        else:
            print(f"\n⚠️  任务执行失败：{task.error}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 加载失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 ChargeCloud OPC - 智能体加载测试")
    print("=" * 60)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试目标：{len(AGENTS)} 个智能体")
    print("=" * 60)
    
    # 测试结果统计
    results = []
    success_count = 0
    fail_count = 0
    
    # 逐个测试
    for agent_info in AGENTS:
        success = test_agent_load(agent_info)
        results.append({
            'agent': agent_info,
            'success': success
        })
        
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    print(f"\n总计：{len(AGENTS)} 个智能体")
    print(f"✅ 成功：{success_count} 个")
    print(f"❌ 失败：{fail_count} 个")
    print(f"成功率：{success_count/len(AGENTS)*100:.1f}%")
    
    print("\n详细结果:")
    for result in results:
        agent = result['agent']
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {agent['name']:12} ({agent['id']:20}) - {agent['role']}")
    
    # 生成测试报告
    report = {
        'test_time': datetime.now().isoformat(),
        'total_agents': len(AGENTS),
        'success_count': success_count,
        'fail_count': fail_count,
        'success_rate': f"{success_count/len(AGENTS)*100:.1f}%",
        'results': [
            {
                'agent_id': r['agent']['id'],
                'agent_name': r['agent']['name'],
                'role': r['agent']['role'],
                'success': r['success']
            }
            for r in results
        ]
    }
    
    # 保存测试报告
    report_path = '/root/.openclaw/workspace/projects/chargecloud-opc/logs/agent_load_test.json'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试报告已保存：{report_path}")
    
    # 最终结论
    print("\n" + "=" * 60)
    if success_count == len(AGENTS):
        print("🎉 所有智能体加载成功！框架运行正常！")
    else:
        print(f"⚠️  有 {fail_count} 个智能体加载失败，请检查错误信息")
    print("=" * 60)
    
    return success_count == len(AGENTS)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
