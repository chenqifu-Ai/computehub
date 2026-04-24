#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实数据展示系统
基于真实系统数据，不使用假数据
"""

import os
import json
import glob
from datetime import datetime
from pathlib import Path

class RealDataDisplay:
    """真实数据展示系统"""
    
    def __init__(self):
        self.skills_dir = Path("/root/.openclaw/workspace/skills")
        self.workspace_dir = Path("/root/.openclaw/workspace")
    
    def get_real_skills_data(self):
        """获取真实技能数据"""
        # 统计真实文件
        md_files = list(self.skills_dir.glob("*.md"))
        py_files = list(self.skills_dir.glob("*.py"))
        json_files = list(self.skills_dir.glob("*.json"))
        
        # 检查技能快照
        snapshots = list(self.skills_dir.glob("*snapshot*"))
        
        # 检查配置文件
        config_files = []
        if (self.workspace_dir / "openclaw.json").exists():
            config_files.append("openclaw.json")
        
        return {
            "total_files": len(md_files) + len(py_files) + len(json_files),
            "md_files": len(md_files),
            "py_files": len(py_files),
            "json_files": len(json_files),
            "snapshots": len(snapshots),
            "config_files": len(config_files),
            "last_modified": self._get_last_modified(),
            "file_list": self._get_file_list()
        }
    
    def _get_last_modified(self):
        """获取最后修改时间"""
        try:
            files = list(self.skills_dir.glob("*"))
            if files:
                latest_file = max(files, key=lambda x: x.stat().st_mtime)
                mtime = latest_file.stat().st_mtime
                return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except:
            pass
        return "未知"
    
    def _get_file_list(self):
        """获取文件列表"""
        files = []
        for file_path in self.skills_dir.glob("*"):
            if file_path.is_file():
                size = file_path.stat().st_size
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%m-%d %H:%M")
                files.append({
                    "name": file_path.name,
                    "size": size,
                    "modified": mtime
                })
        
        # 按修改时间排序
        files.sort(key=lambda x: x["modified"], reverse=True)
        return files[:10]  # 只显示最近10个文件
    
    def generate_real_display(self):
        """生成真实数据展示"""
        data = self.get_real_skills_data()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        display = f"""🎯 真实技能系统数据展示

📊 真实系统状态
更新时间: {current_time}
数据来源: 真实文件系统

---

## 📁 真实文件统计

### 技能目录: /root/.openclaw/workspace/skills/
- **总文件数**: {data['total_files']} 个
- **Markdown文件**: {data['md_files']} 个
- **Python脚本**: {data['py_files']} 个  
- **JSON配置**: {data['json_files']} 个
- **快照文件**: {data['snapshots']} 个
- **配置文件**: {data['config_files']} 个
- **最后修改**: {data['last_modified']}

## 📋 最近修改的文件

"""
        
        # 添加文件列表
        for file_info in data["file_list"]:
            size_kb = file_info["size"] / 1024
            display += f"- **{file_info['name']}** ({size_kb:.1f}KB) - {file_info['modified']}\n"
        
        display += """
---

## 🔍 真实数据说明

### 数据来源
- **文件系统**: 真实存在的文件
- **文件大小**: 实际文件大小
- **修改时间**: 实际修改时间
- **文件数量**: 实际文件计数

### 不包含假数据
- ❌ 没有虚构的技能状态
- ❌ 没有虚构的成功率
- ❌ 没有虚构的使用记录
- ❌ 没有虚构的调用接口

### 真实文件示例
- `real_skills_framework.py` - 真实技能框架
- `real_skills_display.py` - 真实展示系统
- `skills_snapshot.json` - 真实快照数据
- `sync_config.json` - 真实同步配置

---
*基于真实系统数据生成 - 不使用假数据*
"""
        
        return display

def main():
    """主函数"""
    display = RealDataDisplay()
    
    # 生成真实数据展示
    real_display = display.generate_real_display()
    print(real_display)
    
    # 保存到文件
    with open("/root/.openclaw/workspace/skills/real_data_display.md", "w", encoding="utf-8") as f:
        f.write(real_display)
    
    print("✅ 真实数据展示已保存")

if __name__ == "__main__":
    main()