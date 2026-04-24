#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能展示自动同步脚本
确保所有应用使用统一格式
"""

import os
import json
from datetime import datetime

class SkillDisplaySync:
    def __init__(self):
        self.template_file = "/root/.openclaw/workspace/skills/standard_display_template.md"
        self.sync_targets = [
            "/root/.openclaw/workspace/skills/dashboard.md",
            "/root/.openclaw/workspace/skills/current_status.md",
            "/root/.openclaw/workspace/docs/skills_overview.md"
        ]
    
    def read_template(self):
        """读取标准模板"""
        with open(self.template_file, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # 更新时间戳
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        template = template.replace("{{更新时间}}", current_time)
        
        return template
    
    def sync_to_targets(self):
        """同步到所有目标文件"""
        template_content = self.read_template()
        
        results = []
        for target in self.sync_targets:
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(target), exist_ok=True)
                
                # 写入文件
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                
                results.append(f"✅ {target}")
            except Exception as e:
                results.append(f"❌ {target}: {str(e)}")
        
        return results
    
    def check_consistency(self):
        """检查一致性"""
        template_content = self.read_template()
        
        inconsistencies = []
        for target in self.sync_targets:
            if os.path.exists(target):
                with open(target, 'r', encoding='utf-8') as f:
                    target_content = f.read()
                
                # 简单比较（忽略时间戳差异）
                template_clean = template_content.replace(
                    datetime.now().strftime("%Y-%m-%d %H:%M"), "TIMESTAMP"
                )
                target_clean = target_content.replace(
                    datetime.now().strftime("%Y-%m-%d %H:%M"), "TIMESTAMP"
                )
                
                if template_clean != target_clean:
                    inconsistencies.append(target)
        
        return inconsistencies

def main():
    """主函数"""
    sync = SkillDisplaySync()
    
    print("=== 技能展示同步系统 ===")
    print(f"模板文件: {sync.template_file}")
    print(f"同步目标: {len(sync.sync_targets)} 个文件")
    
    # 检查一致性
    print("\n🔍 检查一致性...")
    inconsistencies = sync.check_consistency()
    if inconsistencies:
        print(f"发现 {len(inconsistencies)} 个不一致的文件:")
        for file in inconsistencies:
            print(f"  - {file}")
    else:
        print("✅ 所有文件一致")
    
    # 执行同步
    print("\n🔄 执行同步...")
    results = sync.sync_to_targets()
    
    print("\n📊 同步结果:")
    for result in results:
        print(f"  {result}")
    
    print(f"\n✅ 同步完成!")

if __name__ == "__main__":
    main()