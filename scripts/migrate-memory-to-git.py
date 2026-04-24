#!/usr/bin/env python3
"""
OpenClaw记忆系统迁移到Git记忆体系
将现有MEMORY.md和memory/目录内容迁移到Git版本控制的记忆系统
"""

import os
import re
from datetime import datetime
from pathlib import Path

class MemoryMigrator:
    def __init__(self, repo_path="."):
        self.repo_path = os.path.abspath(repo_path)
        self.memory_dir = os.path.join(self.repo_path, "memory")
        self.git_memory_dir = os.path.join(self.repo_path, "memory")
        
    def analyze_memory_structure(self):
        """分析MEMORY.md结构"""
        memory_file = os.path.join(self.repo_path, "MEMORY.md")
        
        if not os.path.exists(memory_file):
            return {"error": "MEMORY.md not found"}
        
        # 分析章节结构
        sections = []
        current_section = None
        
        with open(memory_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.startswith('## '):
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'title': line[3:].strip(),
                    'start_line': i + 1,
                    'end_line': None,
                    'content': []
                }
            elif current_section:
                current_section['content'].append(line)
        
        if current_section:
            sections.append(current_section)
        
        # 设置结束行号
        for i, section in enumerate(sections):
            if i < len(sections) - 1:
                section['end_line'] = sections[i + 1]['start_line'] - 1
            else:
                section['end_line'] = len(lines)
        
        return {
            'total_lines': len(lines),
            'total_sections': len(sections),
            'sections': sections
        }
    
    def create_section_files(self, sections):
        """为每个章节创建独立文件"""
        created_files = []
        
        # 创建主题目录
        topics_dir = os.path.join(self.git_memory_dir, "topics")
        os.makedirs(topics_dir, exist_ok=True)
        
        for section in sections:
            # 清理文件名
            title = section['title']
            filename = re.sub(r'[<>:"/\\|?*]', '', title)  # 移除非法字符
            filename = re.sub(r'\s+', '_', filename)  # 空格替换为下划线
            filename = filename[:100]  # 限制长度
            
            # 添加时间戳（如果有）
            time_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
            if time_match:
                file_date = time_match.group(1)
                filename = f"{file_date}_{filename}"
            
            filepath = os.path.join(topics_dir, f"{filename}.md")
            
            # 写入文件内容
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**来源**: MEMORY.md (第{section['start_line']}-{section['end_line']}行)\n\n")
                f.write(f"**迁移时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.writelines(section['content'])
            
            created_files.append({
                'original_title': title,
                'filename': filename + ".md",
                'filepath': filepath,
                'lines': section['end_line'] - section['start_line'] + 1
            })
        
        return created_files
    
    def migrate_daily_memory(self):
        """迁移每日记忆文件"""
        daily_dir = os.path.join(self.memory_dir, "daily")
        git_daily_dir = os.path.join(self.git_memory_dir, "daily")
        
        if not os.path.exists(daily_dir):
            return {"status": "skipped", "reason": "No daily directory"}
        
        # 确保目标目录存在
        os.makedirs(git_daily_dir, exist_ok=True)
        
        migrated_files = []
        
        for file in os.listdir(daily_dir):
            if file.endswith('.md'):
                src_path = os.path.join(daily_dir, file)
                dest_path = os.path.join(git_daily_dir, file)
                
                # 复制文件
                with open(src_path, 'r', encoding='utf-8') as src, \
                     open(dest_path, 'w', encoding='utf-8') as dest:
                    content = src.read()
                    dest.write(content)
                
                migrated_files.append({
                    'filename': file,
                    'source': src_path,
                    'destination': dest_path
                })
        
        return {
            'status': 'success',
            'migrated_files': migrated_files,
            'total_files': len(migrated_files)
        }
    
    def create_index_file(self, sections, daily_files):
        """创建索引文件"""
        index_file = os.path.join(self.git_memory_dir, "INDEX.md")
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write("# OpenClaw记忆系统索引\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## 📊 迁移统计\n\n")
            f.write(f"- 总章节数: {len(sections)}\n")
            f.write(f"- 每日文件数: {len(daily_files)}\n")
            f.write(f"- 总记忆条目: {len(sections) + len(daily_files)}\n\n")
            
            f.write("## 📚 主题记忆\n\n")
            for section in sections:
                f.write(f"- [{section['original_title']}](topics/{section['filename']})\n")
            
            f.write("\n## 📅 每日记忆\n\n")
            for daily in daily_files:
                f.write(f"- [{daily['filename']}](daily/{daily['filename']})\n")
            
            f.write("\n## 🔧 使用说明\n\n")
            f.write("使用Git记忆搜索工具进行搜索:\n")
            f.write("```bash\n")
            f.write("python scripts/git-memory-search.py keyword \"搜索词\"\n")
            f.write("python scripts/git-memory-search.py commit \"提交信息\"\n")
            f.write("python scripts/git-memory-manager.py maintenance\n")
            f.write("```\n")
        
        return index_file
    
    def run_migration(self):
        """执行完整迁移"""
        print("🚀 开始OpenClaw记忆系统迁移...")
        
        # 1. 分析MEMORY.md结构
        print("📊 分析MEMORY.md结构...")
        analysis = self.analyze_memory_structure()
        if 'error' in analysis:
            return analysis
        
        print(f"发现 {analysis['total_sections']} 个章节，共 {analysis['total_lines']} 行")
        
        # 2. 创建章节文件
        print("📝 创建主题记忆文件...")
        section_files = self.create_section_files(analysis['sections'])
        print(f"创建了 {len(section_files)} 个主题文件")
        
        # 3. 迁移每日记忆
        print("📅 迁移每日记忆文件...")
        daily_result = self.migrate_daily_memory()
        if daily_result['status'] == 'success':
            print(f"迁移了 {daily_result['total_files']} 个每日文件")
        
        # 4. 创建索引
        print("📋 创建索引文件...")
        index_file = self.create_index_file(section_files, daily_result.get('migrated_files', []))
        print(f"索引文件创建: {index_file}")
        
        # 5. 添加到Git
        print("🔧 添加到Git版本控制...")
        self.add_to_git()
        
        return {
            'status': 'success',
            'sections_migrated': len(section_files),
            'daily_files_migrated': daily_result.get('total_files', 0),
            'total_memory_items': len(section_files) + daily_result.get('total_files', 0),
            'index_file': index_file
        }
    
    def add_to_git(self):
        """添加到Git"""
        try:
            import subprocess
            # 添加所有记忆文件
            subprocess.run(["git", "add", "memory/"], cwd=self.repo_path, check=True)
            # 提交
            commit_msg = f"记忆系统迁移: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.repo_path, check=True)
            return True
        except Exception as e:
            print(f"Git操作失败: {e}")
            return False

def main():
    migrator = MemoryMigrator()
    result = migrator.run_migration()
    
    print("\n🎉 迁移完成!")
    print(f"迁移统计: {result}")
    
    if result['status'] == 'success':
        print("\n💡 下一步操作:")
        print("1. 验证迁移结果: ls -la memory/")
        print("2. 测试搜索功能: python scripts/git-memory-search.py keyword \"关键词\"")
        print("3. 查看索引: cat memory/INDEX.md")

if __name__ == "__main__":
    main()