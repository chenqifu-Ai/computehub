#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同签订SOP生成器
将合同签订流程转换为标准操作程序文档
"""

def generate_contract_sop():
    """
    生成合同签订的标准操作程序(SOP)
    """
    sop = {
        "document_info": {
            "title": "合同签订标准操作程序",
            "document_id": "SOP-CONTRACT-001",
            "version": "1.0",
            "effective_date": "2026-03-25",
            "department": "法务部/业务部",
            "author": "AI助手",
            "review_cycle": "年度"
        },
        "purpose": "规范公司合同签订流程，确保合同签订的合法性、合规性和有效性，降低法律风险，保障公司利益。",
        "scope": "适用于公司所有对外签订的商业合同，包括但不限于采购合同、销售合同、服务合同、技术合同等。",
        "responsibilities": {
            "业务部门": "负责合同需求提出、商务谈判、合同履行跟踪",
            "法务部门": "负责合同法律审核、风险评估、争议解决指导", 
            "财务部门": "负责合同财务条款审核、付款条件确认",
            "管理层": "负责重大合同的最终审批决策",
            "行政部门": "负责合同签署安排、用印管理、档案保管"
        },
        "definitions": {
            "合同": "当事人之间设立、变更、终止民事权利义务关系的协议",
            "重大合同": "单笔金额超过规定限额或对公司经营有重大影响的合同",
            "授权代表": "经公司正式授权，有权代表公司签署合同的人员"
        },
        "procedure": [
            {
                "step": 1,
                "phase": "前期准备阶段",
                "responsible": "业务部门",
                "actions": [
                    {
                        "action": "明确合同需求",
                        "description": "详细说明合同目的、预期成果和商业价值",
                        "deliverables": "《合同需求说明书》"
                    },
                    {
                        "action": "确定合作方",
                        "description": "选择并确认合同相对方，进行初步资质了解",
                        "deliverables": "《合作方基本信息表》"
                    },
                    {
                        "action": "收集资质文件", 
                        "description": "要求对方提供营业执照、授权书等相关资质证明",
                        "deliverables": "对方资质文件复印件（加盖公章）"
                    },
                    {
                        "action": "初步商务谈判",
                        "description": "就价格、交付、服务等核心条款进行初步沟通",
                        "deliverables": "《商务谈判纪要》"
                    }
                ],
                "quality_checkpoints": [
                    "合作方是否具备相应资质和履约能力",
                    "合同需求是否清晰明确",
                    "商务条件是否符合公司利益"
                ]
            },
            {
                "step": 2,
                "phase": "合同起草阶段",
                "responsible": "业务部门/法务部门",
                "actions": [
                    {
                        "action": "选择合同模板",
                        "description": "根据合同类型选择合适的公司标准模板",
                        "deliverables": "选定的合同模板"
                    },
                    {
                        "action": "填写合同主体信息",
                        "description": "准确填写双方名称、地址、法定代表人、联系方式等",
                        "deliverables": "完整的合同主体信息"
                    },
                    {
                        "action": "约定合同标的",
                        "description": "详细描述商品规格、服务内容、技术要求等",
                        "deliverables": "明确的合同标的内容"
                    },
                    {
                        "action": "设定价格条款",
                        "description": "明确价格、支付方式、支付时间、发票要求等",
                        "deliverables": "完整的财务条款"
                    },
                    {
                        "action": "约定履行条款",
                        "description": "明确履行期限、交付方式、验收标准等",
                        "deliverables": "详细的履行条款"
                    },
                    {
                        "action": "设定违约责任",
                        "description": "明确违约情形、违约金计算、损失赔偿等",
                        "deliverables": "完整的违约责任条款"
                    },
                    {
                        "action": "约定争议解决",
                        "description": "明确争议解决方式（仲裁/诉讼）、管辖地等",
                        "deliverables": "争议解决条款"
                    }
                ],
                "quality_checkpoints": [
                    "合同条款是否完整无遗漏",
                    "条款表述是否清晰无歧义",
                    "权利义务是否对等合理"
                ]
            },
            {
                "step": 3,
                "phase": "内部审核阶段",
                "responsible": "多部门协同",
                "actions": [
                    {
                        "action": "业务初审",
                        "description": "业务部门负责人审核合同商务条款",
                        "deliverables": "业务审核意见"
                    },
                    {
                        "action": "法务审核",
                        "description": "法务部门审核合同法律条款和风险点",
                        "deliverables": "法务审核意见书"
                    },
                    {
                        "action": "财务审核",
                        "description": "财务部门审核付款条件和财务风险",
                        "deliverables": "财务审核意见"
                    },
                    {
                        "action": "管理层审批",
                        "description": "根据合同金额和重要性，提交相应管理层审批",
                        "deliverables": "管理层审批意见"
                    },
                    {
                        "action": "修改完善",
                        "description": "根据各部门意见修改合同文本",
                        "deliverables": "修改后的合同终稿"
                    }
                ],
                "quality_checkpoints": [
                    "所有相关部门是否已完成审核",
                    "审核意见是否已全部落实",
                    "审批权限是否符合规定"
                ]
            },
            {
                "step": 4,
                "phase": "对方审核协商阶段",
                "responsible": "业务部门",
                "actions": [
                    {
                        "action": "发送合同草案",
                        "description": "将内部审核通过的合同草案发送给对方",
                        "deliverables": "发送记录"
                    },
                    {
                        "action": "收集反馈意见",
                        "description": "等待并收集对方的修改意见",
                        "deliverables": "对方反馈意见汇总"
                    },
                    {
                        "action": "条款协商",
                        "description": "就争议条款与对方进行协商沟通",
                        "deliverables": "协商会议纪要"
                    },
                    {
                        "action": "形成最终版本",
                        "description": "双方达成一致后形成最终合同版本",
                        "deliverables": "最终版合同文本"
                    }
                ],
                "quality_checkpoints": [
                    "对方意见是否已充分考虑",
                    "争议条款是否已妥善解决",
                    "最终版本是否获得内部确认"
                ]
            },
            {
                "step": 5,
                "phase": "签署准备阶段",
                "responsible": "行政部门/业务部门",
                "actions": [
                    {
                        "action": "确认签署授权",
                        "description": "核实双方签署人的身份和授权文件",
                        "deliverables": "授权委托书/法定代表人证明"
                    },
                    {
                        "action": "准备合同文本",
                        "description": "打印足够份数的最终版合同（通常一式两份或多份）",
                        "deliverables": "打印好的合同文本"
                    },
                    {
                        "action": "准备印章",
                        "description": "准备公司公章或合同专用章",
                        "deliverables": "印章使用申请"
                    },
                    {
                        "action": "安排签署事宜",
                        "description": "确定签署时间、地点、参与人员",
                        "deliverables": "签署安排通知"
                    }
                ],
                "quality_checkpoints": [
                    "签署人授权是否真实有效",
                    "合同文本是否为最终确认版本",
                    "印章使用是否符合规定"
                ]
            },
            {
                "step": 6,
                "phase": "正式签署阶段",
                "responsible": "行政部门",
                "actions": [
                    {
                        "action": "现场签署",
                        "description": "双方签署人在场当面签署合同",
                        "deliverables": "签署过程记录"
                    },
                    {
                        "action": "加盖印章",
                        "description": "在签署处加盖公司公章或合同专用章",
                        "deliverables": "已盖章的合同正本"
                    },
                    {
                        "action": "注明日期",
                        "description": "在合同上注明实际签署日期",
                        "deliverables": "注明日期的合同"
                    },
                    {
                        "action": "交换正本",
                        "description": "双方交换已签署盖章的合同正本",
                        "deliverables": "公司持有的合同正本"
                    }
                ],
                "quality_checkpoints": [
                    "签署是否当面完成",
                    "印章是否清晰完整",
                    "日期是否准确标注"
                ]
            },
            {
                "step": 7,
                "phase": "后续管理阶段",
                "responsible": "业务部门/行政部门",
                "actions": [
                    {
                        "action": "合同归档",
                        "description": "将合同正本及相关文件归档保存",
                        "deliverables": "合同档案"
                    },
                    {
                        "action": "建立跟踪机制",
                        "description": "建立合同履行跟踪表，监控履行进度",
                        "deliverables": "合同履行跟踪表"
                    },
                    {
                        "action": "开始履行",
                        "description": "按合同约定开始履行己方义务",
                        "deliverables": "履行记录"
                    },
                    {
                        "action": "定期检查",
                        "description": "定期检查合同履行情况，及时发现问题",
                        "deliverables": "履行检查报告"
                    },
                    {
                        "action": "处理变更",
                        "description": "如需变更，按程序签订补充协议",
                        "deliverables": "补充协议或变更文件"
                    }
                ],
                "quality_checkpoints": [
                    "合同是否及时归档",
                    "履行跟踪是否有效",
                    "问题是否及时处理"
                ]
            }
        ],
        "related_documents": [
            "《合同管理办法》",
            "《印章使用管理规定》", 
            "《授权委托书模板》",
            "《各类合同标准模板库》"
        ],
        "revision_history": [
            {
                "version": "1.0",
                "date": "2026-03-25",
                "changes": "初始版本",
                "approved_by": "AI助手"
            }
        ],
        "approval_requirements": {
            "minor_contracts": "部门负责人审批",
            "major_contracts": "分管副总审批", 
            "strategic_contracts": "总经理审批"
        }
    }
    
    return sop

def format_sop_document(sop):
    """
    将SOP数据格式化为标准文档格式
    """
    lines = []
    
    # 文档标题和基本信息
    lines.append("# 标准操作程序 (SOP)")
    lines.append("")
    lines.append(f"**文件编号：** {sop['document_info']['document_id']}")
    lines.append(f"**文件名称：** {sop['document_info']['title']}")
    lines.append(f"**版本号：** {sop['document_info']['version']}")
    lines.append(f"**生效日期：** {sop['document_info']['effective_date']}")
    lines.append(f"**适用部门：** {sop['document_info']['department']}")
    lines.append(f"**编制人：** {sop['document_info']['author']}")
    lines.append(f"**复审周期：** {sop['document_info']['review_cycle']}")
    lines.append("")
    
    # 目的
    lines.append("## 1. 目的")
    lines.append(sop['purpose'])
    lines.append("")
    
    # 适用范围
    lines.append("## 2. 适用范围")
    lines.append(sop['scope'])
    lines.append("")
    
    # 职责分工
    lines.append("## 3. 职责分工")
    for role, responsibility in sop['responsibilities'].items():
        lines.append(f"- **{role}：** {responsibility}")
    lines.append("")
    
    # 定义
    lines.append("## 4. 定义")
    for term, definition in sop['definitions'].items():
        lines.append(f"- **{term}：** {definition}")
    lines.append("")
    
    # 操作程序
    lines.append("## 5. 操作程序")
    for phase in sop['procedure']:
        lines.append(f"\n### 第{phase['step']}阶段：{phase['phase']}")
        lines.append(f"**责任部门：** {phase['responsible']}")
        lines.append("")
        lines.append("**具体操作步骤：**")
        
        for i, action in enumerate(phase['actions'], 1):
            lines.append(f"{i}. **{action['action']}**")
            lines.append(f"   - 描述：{action['description']}")
            lines.append(f"   - 交付物：{action['deliverables']}")
            lines.append("")
        
        lines.append("**质量控制点：**")
        for checkpoint in phase['quality_checkpoints']:
            lines.append(f"- {checkpoint}")
        lines.append("")
    
    # 相关文件
    lines.append("## 6. 相关文件")
    for doc in sop['related_documents']:
        lines.append(f"- {doc}")
    lines.append("")
    
    # 审批要求
    lines.append("## 7. 审批要求")
    for contract_type, requirement in sop['approval_requirements'].items():
        lines.append(f"- **{contract_type}：** {requirement}")
    lines.append("")
    
    # 版本历史
    lines.append("## 8. 版本修订历史")
    lines.append("| 版本 | 日期 | 变更内容 | 批准人 |")
    lines.append("|------|------|----------|--------|")
    for revision in sop['revision_history']:
        lines.append(f"| {revision['version']} | {revision['date']} | {revision['changes']} | {revision['approved_by']} |")
    
    return "\n".join(lines)

if __name__ == "__main__":
    # 生成SOP
    contract_sop = generate_contract_sop()
    sop_document = format_sop_document(contract_sop)
    
    # 保存结果
    output_path = '/root/.openclaw/workspace/ai_agent/results/contract_signing_sop.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(sop_document)
    
    print(sop_document)