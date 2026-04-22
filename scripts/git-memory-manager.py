#!/usr/bin/env python3
"""
Git记忆管理器 - 自动化记忆提交、备份和搜索
"""

import subprocess
import json
import os
import time
from datetime import datetime
from pathlib import Path

class GitMemoryManager:
    def __init__(self, repo_path="."):
        self.repo_path = os.path.abspath(repo_path)
        self.config = self.load_config()
    
    def load_config(self):
        config_path = os.path.join(self.repo_path, ".gitmemory-config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认配置
        return {
            "memorySystem": {
                "enabled": True,
                "autoCommit": True,
                "commitMessageTemplate": "记忆更新: {timestamp} - {summary}",
                "searchEnabled": True
            },
            "git": {
                "authorName": "AI Assistant",
                "authorEmail": "ai@openclaw.ai"
            }
        }
    
    def run_git_command(self, cmd, cwd=None):
        """执行Git命令"""
        cwd = cwd or self.repo_path
        try:
            result = subprocess.run(cmd, shell=True, cwd=cwd, 
                                  capture_output=True, text=True, timeout=30)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except Exception as e:
            return "", str(e), 1
    
    def git_add(self, files="*"):
        """添加文件到暂存区"""
        cmd = f"git add {files}"
        output, error, code = self.run_git_command(cmd)
        return code == 0
    
    def git_commit(self, message):
        """提交更改"""
        author = self.config['git']['authorName']
        email = self.config['git']['authorEmail']
        cmd = f'git commit -m "{message}" --author="{author} <{email}>"'
        output, error, code = self.run_git_command(cmd)
        return code == 0
    
    def git_status(self):
        """检查Git状态"""
        output, error, code = self.run_git_command("git status --porcelain")
        if code == 0:
            return output.split('\n') if output else []
        return []
    
    def auto_commit(self, summary="自动记忆更新"):
        """自动提交更改"""
        changes = self.git_status()
        if not changes:
            return {"status": "no_changes"}
        
        # 添加所有更改
        self.git_add("*")
        
        # 生成提交信息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_msg = self.config['memorySystem']['commitMessageTemplate']
        commit_msg = commit_msg.format(timestamp=timestamp, summary=summary)
        
        if self.git_commit(commit_msg):
            return {
                "status": "success", 
                "message": commit_msg, 
                "changes": len(changes)
            }
        else:
            return {"status": "error", "message": "Commit failed"}
    
    def create_memory_snapshot(self):
        """创建记忆快照"""
        # 确保memory目录存在
        memory_dir = os.path.join(self.repo_path, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        
        # 创建每日记忆文件
        daily_dir = os.path.join(memory_dir, "daily")
        os.makedirs(daily_dir, exist_ok=True)
        
        today_file = os.path.join(daily_dir, f"{datetime.now().strftime('%Y-%m-%d')}.md")
        
        # 获取系统状态信息
        status_info = self.get_system_status()
        
        # 写入每日记忆
        with open(today_file, 'a', encoding='utf-8') as f:
            f.write(f"# 每日记忆 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 系统状态\n")
            f.write(f"- 时间: {datetime.now().isoformat()}\n")
            f.write(f"- 变更文件: {len(self.git_status())}\n")
            f.write(f"- 内存使用: {status_info.get('memory', 'N/A')}\n")
            f.write(f"- 磁盘空间: {status_info.get('disk', 'N/A')}\n\n")
            f.write(f"## 今日摘要\n")
            f.write(f"自动生成的记忆快照。记录系统状态和变更情况。\n\n")
        
        return today_file
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            # 内存信息
            mem_info = subprocess.run("free -m", shell=True, capture_output=True, text=True)
            memory = "N/A"
            if mem_info.returncode == 0:
                lines = mem_info.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) > 2:
                        memory = f"{parts[2]}MB/{parts[1]}MB"
            
            # 磁盘信息
            disk_info = subprocess.run("df -h .", shell=True, capture_output=True, text=True)
            disk = "N/A"
            if disk_info.returncode == 0:
                lines = disk_info.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) > 4:
                        disk = parts[4]
            
            return {"memory": memory, "disk": disk}
        except:
            return {"memory": "N/A", "disk": "N/A"}
    
    def backup_memory(self):
        """备份记忆数据"""
        backup_dir = os.path.join(self.repo_path, "backups", "memory")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f"memory_backup_{timestamp}.tar.gz")
        
        # 创建备份
        cmd = f"tar -czf {backup_file} memory/"
        output, error, code = self.run_git_command(cmd)
        
        if code == 0:
            return {"status": "success", "backup_file": backup_file}
        else:
            return {"status": "error", "error": error}
    
    def run_daily_maintenance(self):
        """每日维护任务"""
        results = {}
        
        # 1. 创建记忆快照
        results['snapshot'] = self.create_memory_snapshot()
        
        # 2. 自动提交
        results['commit'] = self.auto_commit("每日自动维护")
        
        # 3. 备份记忆
        results['backup'] = self.backup_memory()
        
        return results

# 命令行接口
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Git记忆管理器")
    parser.add_argument("action", choices=["commit", "snapshot", "backup", "maintenance", "status"],
                       help="执行动作")
    parser.add_argument("--message", "-m", help="提交信息")
    parser.add_argument("--repo", default=".", help="Git仓库路径")
    
    args = parser.parse_args()
    
    manager = GitMemoryManager(args.repo)
    
    if args.action == "status":
        status = manager.git_status()
        print(f"变更文件: {len(status)}")
        for change in status:
            print(f"  {change}")
    
    elif args.action == "commit":
        message = args.message or "自动记忆更新"
        result = manager.auto_commit(message)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.action == "snapshot":
        result = manager.create_memory_snapshot()
        print(f"记忆快照创建: {result}")
    
    elif args.action == "backup":
        result = manager.backup_memory()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.action == "maintenance":
        result = manager.run_daily_maintenance()
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()