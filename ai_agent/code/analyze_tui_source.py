#!/usr/bin/env python3
"""
完整分析TUI源代码的脚本
"""

import os
import re
import json
from pathlib import Path

def find_tui_files():
    """查找所有TUI相关文件"""
    print("正在查找TUI相关文件...")
    
    openclaw_root = Path("/root/.openclaw")
    tui_files = []
    
    # 查找所有可能的TUI文件
    patterns = [
        "*tui*",
        "*terminal*",
        "*ui*",
        "*client*",
        "*gateway*"
    ]
    
    for pattern in patterns:
        for ext in [".js", ".ts", ".jsx", ".tsx", ".json", ".md", ".txt"]:
            for file_path in openclaw_root.rglob(f"*{pattern}*"):
                if file_path.suffix == ext and "node_modules" not in str(file_path):
                    tui_files.append(str(file_path))
    
    # 去重
    tui_files = list(set(tui_files))
    print(f"找到 {len(tui_files)} 个TUI相关文件")
    
    return tui_files

def analyze_status_patterns(files):
    """分析状态显示模式"""
    print("\n正在分析状态显示模式...")
    
    status_patterns = {
        "connection": [],
        "running": [],
        "time": [],
        "animation": [],
        "resource": [],
        "operation": []
    }
    
    # 搜索关键词
    keywords = {
        "connection": ["connected", "connecting", "disconnected", "reconnect"],
        "running": ["running", "starting", "stopped", "error", "idle"],
        "time": ["uptime", "duration", "seconds", "minutes", "hours"],
        "animation": ["⠹", "⠋", "⠙", "⠸", "⣾", "⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "✓", "✗", "⏳", "⚠️"],
        "resource": ["memory", "cpu", "network", "sessions", "queue"],
        "operation": ["processing", "waiting", "completed", "failed", "cancelled", "streaming"]
    }
    
    for file_path in files[:50]:  # 限制前50个文件避免太慢
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                for category, words in keywords.items():
                    for word in words:
                        if re.search(rf'\b{re.escape(word)}\b', content, re.IGNORECASE):
                            if word not in status_patterns[category]:
                                status_patterns[category].append(word)
        except Exception as e:
            continue
    
    return status_patterns

def analyze_actual_tui_source():
    """分析实际的TUI源代码结构"""
    print("\n正在分析TUI源代码结构...")
    
    # 查找可能的TUI入口文件
    possible_entry_points = [
        "/root/.openclaw/node_modules/openclaw-tui",
        "/root/.openclaw/workspace/node_modules/openclaw-tui",
        "/usr/local/lib/node_modules/openclaw-tui"
    ]
    
    tui_structure = {}
    
    for path in possible_entry_points:
        if os.path.exists(path):
            print(f"找到TUI目录: {path}")
            # 分析目录结构
            for root, dirs, files in os.walk(path):
                rel_root = os.path.relpath(root, path)
                if rel_root == ".":
                    rel_root = "/"
                
                js_files = [f for f in files if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]
                if js_files:
                    tui_structure[rel_root] = js_files[:10]  # 限制数量
            break
    
    return tui_structure

def generate_analysis_report(status_patterns, tui_structure):
    """生成分析报告"""
    print("\n生成分析报告...")
    
    report = {
        "summary": {
            "total_status_categories": len(status_patterns),
            "total_status_patterns": sum(len(v) for v in status_patterns.values()),
            "tui_source_found": bool(tui_structure)
        },
        "status_patterns": status_patterns,
        "tui_structure": tui_structure
    }
    
    # 保存报告
    output_dir = Path("/root/.openclaw/workspace/ai_agent/results")
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / "tui_source_analysis.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 生成Markdown报告
    md_report = "# TUI源代码分析报告\n\n"
    md_report += f"## 总结\n"
    md_report += f"- 状态类别数: {report['summary']['total_status_categories']}\n"
    md_report += f"- 具体状态模式: {report['summary']['total_status_patterns']}\n"
    md_report += f"- TUI源代码找到: {report['summary']['tui_source_found']}\n\n"
    
    md_report += "## 状态模式分析\n"
    for category, patterns in status_patterns.items():
        md_report += f"### {category}\n"
        for pattern in patterns:
            md_report += f"- {pattern}\n"
        md_report += "\n"
    
    md_report += "## TUI源代码结构\n"
    if tui_structure:
        for dir_path, files in tui_structure.items():
            md_report += f"### {dir_path}\n"
            for file in files:
                md_report += f"- {file}\n"
            md_report += "\n"
    else:
        md_report += "未找到TUI源代码目录\n"
    
    md_path = output_dir / "tui_source_analysis.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    return str(report_path), str(md_path)

def main():
    """主函数"""
    print("开始完整分析TUI源代码...")
    
    # 1. 查找TUI文件
    tui_files = find_tui_files()
    
    # 2. 分析状态模式
    status_patterns = analyze_status_patterns(tui_files)
    
    # 3. 分析TUI源代码结构
    tui_structure = analyze_actual_tui_source()
    
    # 4. 生成报告
    json_path, md_path = generate_analysis_report(status_patterns, tui_structure)
    
    print(f"\n分析完成！")
    print(f"JSON报告: {json_path}")
    print(f"Markdown报告: {md_path}")
    
    # 打印关键发现
    print("\n关键发现:")
    for category, patterns in status_patterns.items():
        if patterns:
            print(f"  {category}: {len(patterns)}种模式")
    
    return {
        "status": "success",
        "files_found": len(tui_files),
        "status_categories": len(status_patterns),
        "total_patterns": sum(len(v) for v in status_patterns.values()),
        "report_files": [json_path, md_path]
    }

if __name__ == "__main__":
    result = main()
    print(f"\n分析结果: {result}")
