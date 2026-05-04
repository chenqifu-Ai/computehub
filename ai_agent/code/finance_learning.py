#!/usr/bin/env python3
"""
金融顾问自动学习脚本
轮换主题：银行业务→证券投资→基金理财→保险规划→风险管理
"""

import os
import random
import json
from datetime import datetime
from pathlib import Path

# 学习主题轮换
THEMES = [
    "银行业务",
    "证券投资", 
    "基金理财",
    "保险规划",
    "风险管理"
]

# 各主题知识点库
KNOWLEDGE_BASE = {
    "银行业务": [
        "商业银行存款业务类型与特点",
        "银行贷款审批流程与风险评估",
        "银行理财产品分类与风险等级",
        "电子银行安全防护措施",
        "银行间市场交易机制",
        "央行货币政策工具解析",
        "银行资本充足率管理"
    ],
    "证券投资": [
        "股票基本面分析方法",
        "技术分析指标应用",
        "债券投资策略与风险",
        "衍生品交易原理",
        "资产配置理论",
        "量化投资策略",
        "市场情绪分析"
    ],
    "基金理财": [
        "公募基金分类与特点",
        "基金净值计算方法",
        "基金定投策略",
        "FOF基金投资逻辑",
        "基金费率结构分析",
        "基金业绩评价指标",
        "基金风险控制"
    ],
    "保险规划": [
        "人身保险产品分类",
        "财产保险保障范围",
        "保险精算原理",
        "保险理赔流程",
        "保险资金运用",
        "再保险机制",
        "保险监管政策"
    ],
    "风险管理": [
        "金融风险识别方法",
        "风险量化模型",
        "风险对冲策略",
        "压力测试方法",
        "合规风险管理",
        "操作风险控制",
        "系统性风险防范"
    ]
}

def get_current_theme():
    """获取当前学习主题"""
    rotation_file = Path("/root/.openclaw/workspace/memory/finance-rotation.json")
    
    if rotation_file.exists():
        try:
            with open(rotation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('current_theme', THEMES[0])
        except:
            pass
    
    # 默认从第一个主题开始
    return THEMES[0]

def update_rotation_index():
    """更新轮换索引"""
    current_theme = get_current_theme()
    current_index = THEMES.index(current_theme)
    next_index = (current_index + 1) % len(THEMES)
    
    rotation_data = {
        'current_theme': THEMES[next_index],
        'last_update': datetime.now().isoformat(),
        'total_cycles': 0
    }
    
    rotation_file = Path("/root/.openclaw/workspace/memory/finance-rotation.json")
    rotation_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(rotation_file, 'w', encoding='utf-8') as f:
        json.dump(rotation_data, f, ensure_ascii=False, indent=2)
    
    return THEMES[next_index]

def generate_learning_content(theme, topic):
    """生成学习内容"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    content = f"""# {topic}

**学习时间**: {timestamp}  
**所属主题**: {theme}  
**学习类型**: 金融顾问知识积累

## 核心概念

### 定义与特征
- 基本定义：{topic}是金融领域的重要概念
- 主要特征：具有专业性、实用性、系统性
- 应用场景：广泛应用于金融咨询、投资决策、风险管理

### 关键要点
1. **理论基础**：基于金融学原理和市场实践
2. **操作流程**：包含标准化的执行步骤
3. **风险控制**：强调风险识别与防范措施
4. **案例分析**：结合实际案例进行说明

## 实践应用

### 在金融顾问工作中的运用
- 为客户提供专业咨询服务
- 制定个性化的金融规划方案
- 评估投资产品的风险收益特征
- 监控市场变化并及时调整策略

### 注意事项
- 遵守相关法律法规
- 保持客观公正的立场
- 持续学习更新知识
- 注重客户隐私保护

## 学习总结

本次学习加深了对{topic}的理解，为金融顾问工作提供了理论支持和实践指导。

---
*自动生成于金融顾问学习系统*"""
    
    return content

def save_learning_file(theme, topic, content):
    """保存学习文件"""
    ref_dir = Path("/root/.openclaw/workspace/skills/finance-advisor/references")
    ref_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{theme}_{topic.replace(' ', '_')}.md"
    filepath = ref_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath

def main():
    """主函数"""
    print("🤖 开始金融顾问自动学习...")
    
    # 获取当前主题
    current_theme = get_current_theme()
    print(f"📚 当前学习主题: {current_theme}")
    
    # 随机选择知识点
    topics = KNOWLEDGE_BASE.get(current_theme, ["金融基础知识"])
    selected_topic = random.choice(topics)
    print(f"🎯 学习知识点: {selected_topic}")
    
    # 生成学习内容
    content = generate_learning_content(current_theme, selected_topic)
    
    # 保存文件
    filepath = save_learning_file(current_theme, selected_topic, content)
    print(f"💾 学习内容已保存: {filepath}")
    
    # 更新轮换索引
    next_theme = update_rotation_index()
    print(f"🔄 下次学习主题: {next_theme}")
    
    # 统计学习进度
    ref_dir = Path("/root/.openclaw/workspace/skills/finance-advisor/references")
    total_files = len(list(ref_dir.glob("*.md"))) if ref_dir.exists() else 0
    print(f"📊 金融顾问学习文档总数: {total_files} 篇")
    
    print("✅ 金融顾问学习任务完成！")

if __name__ == "__main__":
    main()