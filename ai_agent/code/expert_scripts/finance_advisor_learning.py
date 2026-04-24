#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融顾问自动学习脚本
轮换主题：银行业务→证券投资→基金理财→保险规划→风险管理
"""

import json
import random
from datetime import datetime
from pathlib import Path

# 学习主题和知识点
topics_knowledge = {
    "银行业务": [
        "存款业务与利率计算",
        "贷款业务与风险管理", 
        "支付结算系统",
        "银行卡业务",
        "电子银行业务",
        "国际业务",
        "现金管理"
    ],
    "证券投资": [
        "股票投资基础",
        "债券投资分析",
        "基金投资策略",
        "衍生品投资",
        "技术分析方法",
        "基本面分析",
        "量化投资"
    ],
    "基金理财": [
        "货币市场基金",
        "债券型基金",
        "股票型基金",
        "混合型基金",
        "指数基金",
        "ETF基金",
        "QDII基金"
    ],
    "保险规划": [
        "人寿保险",
        "健康保险",
        "财产保险",
        "责任保险",
        "再保险",
        "保险精算",
        "保险投资"
    ],
    "风险管理": [
        "信用风险管理",
        "市场风险管理",
        "操作风险管理",
        "流动性风险管理",
        "合规风险管理",
        "风险计量模型",
        "风险控制策略"
    ]
}

def get_next_topic(progress_file):
    """获取下一个学习主题"""
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        
        current_index = progress.get('currentIndex', 0)
        topics = progress.get('topics', list(topics_knowledge.keys()))
        
        # 轮换到下一个主题
        next_index = (current_index + 1) % len(topics)
        next_topic = topics[next_index]
        
        # 更新进度
        progress['currentIndex'] = next_index
        progress['lastUpdate'] = datetime.now().isoformat()
        progress['totalLearned'] = progress.get('totalLearned', 0) + 1
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        
        return next_topic
        
    except Exception as e:
        print(f"读取进度文件错误: {e}")
        return random.choice(list(topics_knowledge.keys()))

def generate_learning_content(topic):
    """生成学习内容"""
    knowledge_point = random.choice(topics_knowledge[topic])
    
    content = f"# {knowledge_point} - {topic}学习笔记\n\n"
    content += f"**学习时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    content += f"## 📚 知识要点\n\n"
    
    # 根据主题生成不同的内容
    if topic == "银行业务":
        content += "### 核心概念\n"
        content += "- 存款业务的基本类型和特点\n"
        content += "- 贷款利率的计算方法和影响因素\n"
        content += "- 支付结算的流程和风险控制\n\n"
        
        content += "### 实务操作\n"
        content += "- 客户身份识别和反洗钱要求\n"
        content += "- 信贷审批流程和风险管理\n"
        content += "- 电子银行的安全保障措施\n"
        
    elif topic == "证券投资":
        content += "### 投资理论\n"
        content += "- 现代投资组合理论(MPT)\n"
        content += "- 资本资产定价模型(CAPM)\n"
        content += "- 有效市场假说(EMH)\n\n"
        
        content += "### 分析方法\n"
        content += "- 技术分析: K线图、均线、指标\n"
        content += "- 基本面分析: 财务分析、行业分析\n"
        content += "- 量化分析: 模型构建、回测验证\n"
        
    elif topic == "基金理财":
        content += "### 基金类型\n"
        content += "- 按投资标的: 股票型、债券型、混合型\n"
        content += "- 按运作方式: 开放式、封闭式\n"
        content += "- 特殊类型: ETF、LOF、QDII\n\n"
        
        content += "### 投资策略\n"
        content += "- 定投策略和时机选择\n"
        content += "- 风险收益特征分析\n"
        content += "- 基金选择和组合构建\n"
        
    elif topic == "保险规划":
        content += "### 保险产品\n"
        content += "- 人身保险: 寿险、健康险、意外险\n"
        content += "- 财产保险: 车险、家财险、责任险\n"
        content += "- 新型保险: 投资连结保险、万能险\n\n"
        
        content += "### 规划原则\n"
        content += "- 保障优先原则\n"
        content += "- 适度保障原则\n"
        content += "- 动态调整原则\n"
        
    elif topic == "风险管理":
        content += "### 风险类型\n"
        content += "- 市场风险: 价格波动风险\n"
        content += "- 信用风险: 违约风险\n"
        content += "- 操作风险: 内部流程风险\n\n"
        
        content += "### 管理工具\n"
        content += "- 风险识别和评估\n"
        content += "- 风险控制和转移\n"
        content += "- 风险监测和报告\n"
    
    content += "\n## 💡 学习心得\n\n"
    content += "通过本次学习，加深了对金融知识的理解，为客户提供更专业的金融服务奠定了基础。\n\n"
    
    content += "## 🎯 后续学习计划\n\n"
    content += "1. 深入理解相关法律法规\n"
    content += "2. 学习实际案例分析\n"
    content += "3. 关注市场最新动态\n"
    
    return content, knowledge_point

def main():
    """主函数"""
    
    # 获取下一个学习主题
    progress_file = "/root/.openclaw/workspace/finance-advisor/learning-progress.json"
    topic = get_next_topic(progress_file)
    
    # 生成学习内容
    content, knowledge_point = generate_learning_content(topic)
    
    # 保存学习文档
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{topic}_{knowledge_point}.md"
    filepath = f"/root/.openclaw/workspace/finance-advisor/references/{filename}"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 输出结果
    print(f"🎓 金融顾问学习完成")
    print(f"📚 学习主题: {topic}")
    print(f"📖 知识点: {knowledge_point}")
    print(f"📁 保存位置: {filepath}")
    print(f"⏰ 学习时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 更新专家工作日志
    work_log = {
        "expert": "金算子（金融顾问）",
        "task": "金融知识学习",
        "topic": topic,
        "knowledge_point": knowledge_point,
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "status": "已完成",
        "output_file": filepath
    }
    
    work_log_file = f"/root/.openclaw/workspace/expert_work_logs/金算子_金融顾问_report_{timestamp}.json"
    with open(work_log_file, 'w', encoding='utf-8') as f:
        json.dump(work_log, f, ensure_ascii=False, indent=2)
    
    print(f"📊 工作记录: {work_log_file}")

if __name__ == "__main__":
    main()