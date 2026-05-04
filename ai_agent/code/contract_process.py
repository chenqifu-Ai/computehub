#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同签订流程生成器
根据标准商业实践生成完整的合同签订流程
"""

def generate_contract_signing_process():
    """
    生成合同签订的完整流程
    """
    process = {
        "title": "合同签订标准流程",
        "steps": [
            {
                "step": 1,
                "name": "前期准备阶段",
                "tasks": [
                    "明确合同目的和商业需求",
                    "确定合同相对方（对方当事人）",
                    "收集对方资质文件（营业执照、授权文件等）",
                    "进行初步商业谈判",
                    "确定合同主要条款框架"
                ]
            },
            {
                "step": 2,
                "name": "合同起草阶段", 
                "tasks": [
                    "选择合适的合同模板或从零起草",
                    "明确合同主体信息（双方名称、地址、法定代表人等）",
                    "详细约定合同标的（商品/服务的具体描述）",
                    "确定价格条款和支付方式",
                    "约定履行期限和交付方式",
                    "设定违约责任条款",
                    "约定争议解决方式（仲裁/诉讼）",
                    "确定合同生效条件和份数"
                ]
            },
            {
                "step": 3,
                "name": "内部审核阶段",
                "tasks": [
                    "业务部门初审",
                    "法务部门法律审核",
                    "财务部门财务条款审核", 
                    "管理层审批（根据金额和重要性）",
                    "修改完善合同条款"
                ]
            },
            {
                "step": 4,
                "name": "对方审核协商阶段",
                "tasks": [
                    "将合同草案发送给对方",
                    "等待对方反馈意见",
                    "就争议条款进行协商",
                    "达成一致后形成最终版本",
                    "确认双方对合同内容无异议"
                ]
            },
            {
                "step": 5,
                "name": "签署准备阶段",
                "tasks": [
                    "确认签署人身份和授权",
                    "准备足够份数的合同文本",
                    "准备签署所需的印章",
                    "安排签署时间和地点",
                    "准备见证人（如需要）"
                ]
            },
            {
                "step": 6,
                "name": "正式签署阶段",
                "tasks": [
                    "双方签署人当面签署",
                    "加盖公司公章或合同专用章",
                    "注明签署日期",
                    "交换合同正本",
                    "拍照留存签署过程（可选）"
                ]
            },
            {
                "step": 7,
                "name": "后续管理阶段",
                "tasks": [
                    "合同归档保存",
                    "建立合同履行跟踪机制",
                    "按约定开始履行合同义务",
                    "定期检查合同履行情况",
                    "处理合同变更或补充协议（如需要）"
                ]
            }
        ],
        "key_points": [
            "确保签署人具有合法授权",
            "合同条款要具体明确，避免歧义",
            "重要合同建议请专业律师审核",
            "保留完整的沟通记录和签署证据",
            "注意合同的生效条件和时间节点"
        ],
        "common_pitfalls": [
            "未核实对方签约资格和授权",
            "合同条款过于笼统或存在漏洞",
            "签署程序不规范导致效力问题",
            "未妥善保管合同原件",
            "忽视合同履行的跟踪管理"
        ]
    }
    
    return process

def format_output(process):
    """
    格式化输出结果
    """
    output = []
    output.append(f"# {process['title']}\n")
    
    for step in process['steps']:
        output.append(f"## 第{step['step']}步：{step['name']}")
        for i, task in enumerate(step['tasks'], 1):
            output.append(f"{i}. {task}")
        output.append("")
    
    output.append("## 关键注意事项")
    for point in process['key_points']:
        output.append(f"- {point}")
    
    output.append("\n## 常见风险点")
    for pitfall in process['common_pitfalls']:
        output.append(f"- {pitfall}")
    
    return "\n".join(output)

if __name__ == "__main__":
    # 执行主流程
    contract_process = generate_contract_signing_process()
    result = format_output(contract_process)
    
    # 保存结果
    with open('/root/.openclaw/workspace/ai_agent/results/contract_signing_process.md', 'w', encoding='utf-8') as f:
        f.write(result)
    
    print(result)