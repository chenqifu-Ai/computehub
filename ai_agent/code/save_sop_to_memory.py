#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将主智能体SOP规则写入永久记忆
"""

import os
import datetime
from pathlib import Path

def update_memory_with_sop():
    """更新MEMORY.md文件，添加SOP规则"""
    memory_file = Path("/root/.openclaw/workspace/MEMORY.md")
    
    if not memory_file.exists():
        return {"success": False, "error": "MEMORY.md文件不存在"}
    
    # 读取现有内容
    with open(memory_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # SOP规则内容
    sop_section = """
## 主智能体SOP规则（强制执行）

### 核心流程
```
1. 思考 → 2. 写计划写Python代码 → 3. 执行代码 → 4. 分析结果 → 5. 循环直到完成
```

### 详细规则

#### 1. 思考（大脑）
- 分析任务本质
- 制定执行计划  
- 明确成功标准
- **禁止直接行动**

#### 2. 写计划写Python代码（手脚准备）
- 将计划转化为可执行代码
- 代码必须完整、可执行
- 包含验证逻辑
- **Python就是AI的手脚**

#### 3. 执行代码（手脚行动）
- 运行Python脚本
- 获取执行结果
- **必须验证执行正确性**
- 禁止虚假报告

#### 4. 分析结果（大脑反馈）
- 检查结果是否符合预期
- 验证成功标准是否达成
- 识别问题并调整

#### 5. 循环直到完成（持续优化）
- 未完成则返回第1步
- 调整计划重新执行
- **不完成不罢休**

### 执行正确性规范

#### 结果验证机制
- 文件操作：验证存在、大小、内容
- 网络请求：验证响应码、数据
- 邮件发送：验证SMTP响应、发送ID

#### 反馈真实性
- ❌ 禁止："已执行"（未验证）
- ✅ 必须："执行成功，验证结果：xxx"

#### 可量化成功标准
- 每个操作必须有明确成功标准
- 结果必须可验证、可信任

### 核心思想
- **Python是AI的手脚**：大脑思考，手脚执行
- **信任是基础**：一次虚假报告破坏所有信任
- **质量优先**：不追求速度，追求正确性

---
*制定时间：2026-03-26*  
*制定者：小智*  
*审核者：老大*
"""
    
    # 检查是否已有SOP规则
    if "主智能体SOP规则" in content:
        # 更新现有SOP规则
        sections = content.split("## ")
        new_content = ""
        
        for i, section in enumerate(sections):
            if i == 0:
                new_content += section
            else:
                if "主智能体SOP规则" in section:
                    # 替换为新的SOP规则
                    new_content += "## " + sop_section.lstrip()
                else:
                    new_content += "## " + section
    else:
        # 在文件末尾添加SOP规则
        new_content = content.rstrip() + "\n\n" + sop_section
    
    # 写入文件
    with open(memory_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # 验证写入成功
    with open(memory_file, 'r', encoding='utf-8') as f:
        updated_content = f.read()
    
    if "主智能体SOP规则" in updated_content:
        return {
            "success": True,
            "file_path": str(memory_file),
            "file_size": len(updated_content),
            "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        return {"success": False, "error": "SOP规则写入失败"}

def main():
    """主函数"""
    print("=== 将SOP规则写入永久记忆 ===")
    print(f"执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 执行更新
    result = update_memory_with_sop()
    
    # 输出结果
    if result["success"]:
        print("✅ SOP规则写入成功")
        print(f"文件: {result['file_path']}")
        print(f"大小: {result['file_size']} 字节")
        print(f"时间: {result['update_time']}")
    else:
        print("❌ SOP规则写入失败")
        print(f"错误: {result['error']}")
    
    # 保存执行结果
    import json
    result_file = "/root/.openclaw/workspace/ai_agent/results/sop_save_result.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n执行结果已保存到: {result_file}")

if __name__ == "__main__":
    main()