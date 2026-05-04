#!/usr/bin/env python3
"""
查找杀掉 openclaw-tui 的脚本
"""

import os
import re

def find_kill_scripts():
    """查找所有可能包含 kill openclaw-tui 的脚本"""
    
    print("🔍 开始查找杀掉 openclaw-tui 的脚本...")
    
    suspicious_files = []
    
    # 搜索范围
    search_paths = [
        "/root/.openclaw/workspace",
        "/root/.openclaw",
        "/root"
    ]
    
    # 搜索关键词
    keywords = ["kill", "openclaw", "tui", "pkill", "terminate"]
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
            
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if file.endswith(('.sh', '.py', '.bash')):
                    filepath = os.path.join(root, file)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                            
                            # 检查是否包含关键词
                            if any(keyword in content for keyword in keywords):
                                # 检查是否包含 openclaw-tui 相关的 kill 命令
                                if re.search(r'(kill|pkill).*openclaw', content) or \
                                   re.search(r'openclaw.*(kill|pkill)', content):
                                    suspicious_files.append({
                                        'file': filepath,
                                        'content': content[:500]  # 只取前500字符
                                    })
                                    print(f"⚠️  发现可疑脚本: {filepath}")
                                    
                    except Exception as e:
                        pass
    
    return suspicious_files

def analyze_scripts(suspicious_files):
    """分析可疑脚本"""
    
    print(f"\n📊 分析结果: 共找到 {len(suspicious_files)} 个可疑脚本")
    
    for script in suspicious_files:
        print(f"\n📄 文件: {script['file']}")
        print("📝 内容预览:")
        print(script['content'][:200] + "...")
        
        # 提取 kill 相关命令
        kill_commands = re.findall(r'.*(kill|pkill).*', script['content'])
        if kill_commands:
            print("🔪 发现的 kill 命令:")
            for cmd in kill_commands[:3]:  # 只显示前3个
                print(f"   - {cmd}")

def main():
    """主函数"""
    
    # 记录查找操作
    print("📝 开始查找危险脚本...")
    
    suspicious_files = find_kill_scripts()
    
    if suspicious_files:
        analyze_scripts(suspicious_files)
        
        # 建议操作
        print(f"\n💡 建议:")
        print("1. 检查这些脚本的内容")
        print("2. 确认是否需要删除")
        print("3. 删除危险脚本")
        
        return suspicious_files
    else:
        print("✅ 未发现可疑脚本")
        return []

if __name__ == "__main__":
    result = main()
    
    # 保存查找结果
    if result:
        import json
        with open("/root/.openclaw/workspace/kill_script_search_result.json", "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n📁 结果已保存到: /root/.openclaw/workspace/kill_script_search_result.json")