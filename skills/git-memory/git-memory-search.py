#!/usr/bin/env python3
"""
Git记忆搜索工具 - 基于Git的强大记忆搜索功能
支持关键词搜索、时间范围搜索、作者搜索、文件类型搜索
"""

import subprocess
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

class GitMemorySearcher:
    def __init__(self, repo_path="."):
        self.repo_path = os.path.abspath(repo_path)
        self.config = self.load_config()
    
    def load_config(self):
        config_path = os.path.join(self.repo_path, ".gitmemory-config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def run_git_command(self, cmd, cwd=None):
        """执行Git命令"""
        cwd = cwd or self.repo_path
        try:
            result = subprocess.run(cmd, shell=True, cwd=cwd, 
                                  capture_output=True, text=True, timeout=30)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout", 1
        except Exception as e:
            return "", str(e), 1
    
    def search_by_keyword(self, keyword, file_pattern=None, case_sensitive=False, limit=50):
        """按关键词搜索"""
        cmd = f"git grep -n {'-i' if not case_sensitive else ''} \"{keyword}\""
        if file_pattern:
            cmd += f" -- \"{file_pattern}\""
        
        output, error, code = self.run_git_command(cmd)
        
        if code == 0 and output:
            results = []
            for line in output.split('\n'):
                if ':' in line and len(results) < limit:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        results.append({
                            'file': parts[0],
                            'line': parts[1],
                            'content': parts[2],
                            'match': keyword
                        })
            return results
        elif code == 1 and "exit status 1" in error:
            return []  # 没有找到结果
        else:
            return [{'error': error}]
    
    def search_by_commit_message(self, keyword, author=None, since=None, until=None):
        """按提交信息搜索"""
        cmd = "git log --oneline --grep"
        if author:
            cmd += f" --author=\"{author}\""
        if since:
            cmd += f" --since=\"{since}\""
        if until:
            cmd += f" --until=\"{until}\""
        
        cmd += f" \"{keyword}\""
        
        output, error, code = self.run_git_command(cmd)
        
        if code == 0 and output:
            commits = []
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    commits.append({
                        'commit': parts[0],
                        'message': parts[1] if len(parts) > 1 else ''
                    })
            return commits
        return []
    
    def search_by_time_range(self, since_days=7, file_pattern=None, since=None):
        """按时间范围搜索"""
        if since:
            since_date = since
        else:
            since_date = (datetime.now() - timedelta(days=since_days)).strftime('%Y-%m-%d')
        
        cmd = f"git log --since=\"{since_date}\" --name-only"
        
        if file_pattern:
            cmd += f" -- \"{file_pattern}\""
        
        output, error, code = self.run_git_command(cmd)
        
        if code == 0 and output:
            files = set()
            current_commit = None
            results = []
            
            for line in output.split('\n'):
                if line.startswith('commit '):
                    current_commit = line[7:]
                elif line.strip() and not line.startswith('Author:') and not line.startswith('Date:'):
                    files.add(line.strip())
            
            return list(files)
        return []
    
    def get_file_history(self, file_path, limit=10):
        """获取文件修改历史"""
        cmd = f"git log -{limit} --oneline -- \"{file_path}\""
        output, error, code = self.run_git_command(cmd)
        
        if code == 0 and output:
            history = []
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    history.append({
                        'commit': parts[0],
                        'message': parts[1] if len(parts) > 1 else ''
                    })
            return history
        return []
    
    def advanced_search(self, query, search_type="content", **kwargs):
        """高级搜索接口"""
        if search_type == "keyword":
            return self.search_by_keyword(query, **kwargs)
        elif search_type == "commit":
            return self.search_by_commit_message(query, **kwargs)
        elif search_type == "time":
            return self.search_by_time_range(**kwargs)
        elif search_type == "history":
            return self.get_file_history(query, **kwargs)
        else:
            return {"error": "Unsupported search type"}
    
    def create_search_index(self):
        """创建搜索索引"""
        # 获取所有文本文件
        cmd = "git ls-files | grep -E '\\.(md|txt|json|yaml|yml)$'"
        output, error, code = self.run_git_command(cmd)
        
        if code == 0:
            files = output.split('\n')
            index_data = {
                'timestamp': datetime.now().isoformat(),
                'file_count': len(files),
                'files': []
            }
            
            for file in files:
                if file.strip():
                    # 获取文件基本信息
                    cmd_stat = f"git log -1 --format=\"%ai\" -- \"{file}\""
                    mtime, _, _ = self.run_git_command(cmd_stat)
                    
                    index_data['files'].append({
                        'path': file,
                        'last_modified': mtime.strip() if mtime else 'unknown'
                    })
            
            # 保存索引
            index_dir = os.path.join(self.repo_path, "memory", "search-index")
            os.makedirs(index_dir, exist_ok=True)
            
            index_file = os.path.join(index_dir, f"index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            return {"status": "success", "index_file": index_file, "file_count": len(files)}
        
        return {"status": "error", "error": error}

# 命令行接口
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Git记忆搜索工具")
    parser.add_argument("search_type", choices=["keyword", "commit", "time", "history", "index"], 
                       help="搜索类型")
    parser.add_argument("query", nargs="?", help="搜索查询")
    parser.add_argument("--file", help="文件路径模式")
    parser.add_argument("--author", help="作者过滤")
    parser.add_argument("--since", help="开始时间")
    parser.add_argument("--until", help="结束时间")
    parser.add_argument("--limit", type=int, default=50, help="结果数量限制")
    parser.add_argument("--case-sensitive", action="store_true", help="区分大小写")
    parser.add_argument("--repo", default=".", help="Git仓库路径")
    
    args = parser.parse_args()
    
    searcher = GitMemorySearcher(args.repo)
    
    if args.search_type == "index":
        result = searcher.create_search_index()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        kwargs = {}
        if args.file:
            kwargs['file_pattern'] = args.file
        if args.author:
            kwargs['author'] = args.author
        if args.since:
            kwargs['since'] = args.since
        if args.until:
            kwargs['until'] = args.until
        if args.limit:
            kwargs['limit'] = args.limit
        if args.case_sensitive:
            kwargs['case_sensitive'] = args.case_sensitive
        
        result = searcher.advanced_search(
            args.query, 
            search_type=args.search_type, 
            **kwargs
        )
        
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()