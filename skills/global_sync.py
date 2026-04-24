#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局技能同步系统
确保所有界面显示一致，重启后也能保持
"""

import os
import json
from datetime import datetime

class GlobalSkillSync:
    def __init__(self):
        self.source_file = "/root/.openclaw/workspace/skills/unified_skills_source.md"
        self.sync_config_file = "/root/.openclaw/workspace/skills/sync_config.json"
        self.targets = [
            {
                "name": "TUI界面",
                "path": "/root/.openclaw/workspace/skills/tui_display.md",
                "enabled": True
            },
            {
                "name": "Web界面", 
                "path": "/root/.openclaw/workspace/docs/skills_web.md",
                "enabled": True
            },
            {
                "name": "聊天界面模板",
                "path": "/root/.openclaw/workspace/skills/chat_template.md",
                "enabled": True
            }
        ]
        self.load_config()
    
    def load_config(self):
        """加载同步配置"""
        if os.path.exists(self.sync_config_file):
            with open(self.sync_config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "version": "2.0",
                "last_sync": None,
                "sync_enabled": True,
                "created_at": datetime.now().isoformat()
            }
            self.save_config()
    
    def save_config(self):
        """保存配置"""
        with open(self.sync_config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def read_source(self):
        """读取中央源文件"""
        if not os.path.exists(self.source_file):
            raise FileNotFoundError("中央技能源文件不存在")
        
        with open(self.source_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新时间戳
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = content.replace("{{current_time}}", current_time)
        
        return content
    
    def sync_to_targets(self):
        """同步到所有目标"""
        source_content = self.read_source()
        
        results = []
        for target in self.targets:
            if not target["enabled"]:
                continue
                
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(target["path"]), exist_ok=True)
                
                # 写入目标文件
                with open(target["path"], 'w', encoding='utf-8') as f:
                    f.write(source_content)
                
                results.append({
                    "target": target["name"],
                    "path": target["path"],
                    "status": "success",
                    "size": len(source_content)
                })
            except Exception as e:
                results.append({
                    "target": target["name"],
                    "path": target["path"],
                    "status": "error",
                    "error": str(e)
                })
        
        # 更新同步时间
        self.config["last_sync"] = datetime.now().isoformat()
        self.save_config()
        
        return results
    
    def check_consistency(self):
        """检查一致性"""
        source_content = self.read_source()
        
        inconsistencies = []
        for target in self.targets:
            if not target["enabled"] or not os.path.exists(target["path"]):
                continue
            
            with open(target["path"], 'r', encoding='utf-8') as f:
                target_content = f.read()
            
            # 忽略时间戳差异进行比较
            source_clean = source_content.replace(
                datetime.now().strftime("%Y-%m-%d %H:%M"), "TIMESTAMP"
            )
            target_clean = target_content.replace(
                datetime.now().strftime("%Y-%m-%d %H:%M"), "TIMESTAMP"
            )
            
            if source_clean != target_clean:
                inconsistencies.append(target["name"])
        
        return inconsistencies
    
    def on_startup(self):
        """启动时调用"""
        print("🔍 检查技能展示一致性...")
        inconsistencies = self.check_consistency()
        
        if inconsistencies:
            print(f"⚠️ 发现 {len(inconsistencies)} 个不一致的目标:")
            for target in inconsistencies:
                print(f"  - {target}")
            
            print("🔄 执行同步...")
            results = self.sync_to_targets()
            
            print("✅ 同步完成:")
            for result in results:
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"  {status_icon} {result['target']}: {result.get('size', 'N/A')} 字符")
        else:
            print("✅ 所有目标一致，无需同步")

def main():
    """主函数"""
    sync = GlobalSkillSync()
    
    print("=== 全局技能同步系统 ===")
    print(f"源文件: {sync.source_file}")
    print(f"目标数量: {len([t for t in sync.targets if t['enabled']])}")
    
    # 模拟启动检查
    sync.on_startup()
    
    print(f"\n✅ 同步系统就绪!")
    print(f"下次重启时会自动检查一致性")

if __name__ == "__main__":
    main()