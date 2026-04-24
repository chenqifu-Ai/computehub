#!/usr/bin/env python3
"""
TUI界面含义思维导图生成脚本
"""

def create_tui_mindmap():
    """创建TUI界面含义的思维导图结构"""
    
    mindmap = {
        "中心主题": "OpenClaw TUI界面含义",
        "主要分支": [
            {
                "分支": "连接状态",
                "子项": [
                    "connected - 连接正常",
                    "connecting - 正在连接", 
                    "disconnected - 断开连接",
                    "reconnecting - 重新连接中",
                    "auth_failed - 认证失败"
                ]
            },
            {
                "分支": "运行状态",
                "子项": [
                    "running - 运行中",
                    "starting - 启动中",
                    "stopped - 已停止", 
                    "error - 错误状态",
                    "idle - 空闲状态"
                ]
            },
            {
                "分支": "时间显示",
                "子项": [
                    "• 18s - 秒级运行时间",
                    "• 2m 30s - 分钟级时间",
                    "• 1h 5m - 小时级时间",
                    "uptime - 总运行时间"
                ]
            },
            {
                "分支": "动画指示",
                "子项": [
                    "⠹ - 旋转动画(处理中)",
                    "✓ - 完成标记",
                    "✗ - 错误标记", 
                    "⏳ - 等待标记",
                    "⚠️ - 警告标记"
                ]
            },
            {
                "分支": "资源状态",
                "子项": [
                    "memory: 45% - 内存使用率",
                    "cpu: 12% - CPU使用率", 
                    "network: 2.3M/s - 网络流量",
                    "sessions: 3 - 活跃会话数",
                    "queue: 2 - 任务队列"
                ]
            },
            {
                "分支": "操作状态",
                "子项": [
                    "processing - 处理中",
                    "waiting - 等待输入",
                    "completed - 已完成",
                    "failed - 操作失败",
                    "cancelled - 已取消"
                ]
            }
        ]
    }
    
    return mindmap

def generate_markdown_mindmap(mindmap):
    """生成Markdown格式的思维导图"""
    
    markdown = f"# {mindmap['中心主题']}\n\n"
    
    for branch in mindmap['主要分支']:
        markdown += f"## {branch['分支']}\n\n"
        for item in branch['子项']:
            markdown += f"- {item}\n"
        markdown += "\n"
    
    return markdown

def generate_text_mindmap(mindmap):
    """生成文本格式的思维导图"""
    
    text = f"{mindmap['中心主题']}\n"
    text += "=" * 50 + "\n\n"
    
    for branch in mindmap['主要分支']:
        text += f"┌─ {branch['分支']}\n"
        for item in branch['子项']:
            text += f"│  ├─ {item}\n"
        text += "│\n"
    
    return text

def main():
    """主函数"""
    print("正在生成TUI界面含义思维导图...")
    
    # 创建思维导图结构
    mindmap = create_tui_mindmap()
    
    # 生成Markdown格式
    markdown_content = generate_markdown_mindmap(mindmap)
    
    # 生成文本格式
    text_content = generate_text_mindmap(mindmap)
    
    # 保存文件
    with open('/root/.openclaw/workspace/ai_agent/results/tui_mindmap.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    with open('/root/.openclaw/workspace/ai_agent/results/tui_mindmap.txt', 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    print("思维导图生成完成！")
    print("\n文本格式思维导图：")
    print(text_content)
    
    return {
        "status": "success",
        "files": [
            "/root/.openclaw/workspace/ai_agent/results/tui_mindmap.md",
            "/root/.openclaw/workspace/ai_agent/results/tui_mindmap.txt"
        ],
        "mindmap": mindmap
    }

if __name__ == "__main__":
    result = main()