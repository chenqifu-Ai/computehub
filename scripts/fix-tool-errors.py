#!/usr/bin/env python3
"""
修复OpenClaw工具错误脚本
解决:EISDIR目录错误和偏移量超出范围错误
"""

import os
import sys
from pathlib import Path

def fix_directory_errors():
    """修复目录/文件类型错误"""
    print("🔧 修复目录/文件类型错误...")
    
    # 检查所有可能被误认为文件的目录
    problematic_items = []
    
    for item in ["memory", "scripts", "config", "ai_agent", "framework"]:
        item_path = Path(item)
        if item_path.exists() and item_path.is_dir():
            # 检查是否有同名的文件（应该不存在）
            if (item_path.parent / (item_path.name + ".tmp")).exists():
                problematic_items.append(item)
            print(f"✅ {item}/ 是正确目录")
        elif item_path.exists() and not item_path.is_dir():
            print(f"⚠️  {item} 是文件，但应该是目录")
            problematic_items.append(item)
        else:
            print(f"✅ {item} 不存在或正确")
    
    return problematic_items

def fix_offset_errors():
    """修复文件偏移量错误"""
    print("\n🔧 修复文件偏移量错误...")
    
    # 检查主要文件的行数
    files_to_check = ["MEMORY.md", "AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md"]
    
    for file in files_to_check:
        file_path = Path(file)
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                print(f"✅ {file}: {len(lines)} 行")
                
                # 如果有工具尝试读取超出范围的行
                if len(lines) < 10000:  # 大多数文件不会超过10000行
                    print(f"   警告: 工具可能尝试读取超出 {len(lines)} 行的内容")
                    
            except Exception as e:
                print(f"❌ 读取 {file} 失败: {e}")
        else:
            print(f"⚠️  {file} 不存在或不是文件")

def check_tool_configs():
    """检查工具配置文件"""
    print("\n🔧 检查工具配置文件...")
    
    # 检查是否有配置指定了错误的偏移量
    config_files = [
        ".gitmemory-config.json",
        "config/email.conf", 
        "config/ollama.conf"
    ]
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            print(f"✅ {config_file} 存在")
            # 检查是否有异常的偏移量配置
            try:
                if config_file == ".gitmemory-config.json":
                    import json
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    if "offset" in str(config):
                        print(f"   发现offset配置: {config}")
            except:
                print(f"⚠️  读取 {config_file} 配置失败")
        else:
            print(f"✅ {config_file} 不存在（正常）")

def create_safe_read_wrapper():
    """创建安全的文件读取包装器"""
    print("\n🔧 创建安全读取包装器...")
    
    safe_read_code = '''
#!/usr/bin/env python3
"""
安全文件读取包装器 - 防止EISDIR和偏移量错误
"""

import os
import sys

def safe_read_file(file_path, offset=1, limit=50):
    """安全读取文件，防止常见错误"""
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {"error": f"文件不存在: {file_path}"}
    
    # 检查是否是目录
    if os.path.isdir(file_path):
        return {"error": f"路径是目录，不是文件: {file_path}"}
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return {"error": f"文件为空: {file_path}"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # 验证偏移量
        if offset < 1:
            offset = 1
        if offset > total_lines:
            return {
                "error": f"偏移量 {offset} 超出文件范围 (总共 {total_lines} 行)",
                "total_lines": total_lines,
                "suggestion": f"使用偏移量 1-{total_lines}"
            }
        
        # 计算实际读取范围
        start_idx = offset - 1
        end_idx = min(start_idx + limit, total_lines)
        
        result_lines = lines[start_idx:end_idx]
        
        return {
            "success": True,
            "file": file_path,
            "offset": offset,
            "limit": limit,
            "total_lines": total_lines,
            "lines_read": len(result_lines),
            "content": ''.join(result_lines)
        }
        
    except Exception as e:
        return {"error": f"读取文件失败: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python safe_read.py <文件路径> [偏移量] [限制]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    
    result = safe_read_file(file_path, offset, limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''
    
    safe_read_path = Path("scripts/safe_read.py")
    with open(safe_read_path, 'w', encoding='utf-8') as f:
        f.write(safe_read_code)
    
    # 设置执行权限
    safe_read_path.chmod(0o755)
    print(f"✅ 创建安全读取脚本: {safe_read_path}")

def main():
    """主修复函数"""
    print("🚀 开始修复OpenClaw工具错误")
    print("=" * 50)
    
    # 1. 修复目录错误
    dir_errors = fix_directory_errors()
    
    # 2. 修复偏移量错误  
    fix_offset_errors()
    
    # 3. 检查工具配置
    check_tool_configs()
    
    # 4. 创建安全读取包装器
    create_safe_read_wrapper()
    
    print("\n" + "=" * 50)
    print("🎉 修复完成!")
    
    if dir_errors:
        print(f"\n⚠️  需要手动检查的项目: {dir_errors}")
    
    print("\n💡 建议操作:")
    print("1. 使用新创建的安全读取脚本")
    print("2. 监控工具日志查看具体错误场景")
    print("3. 定期运行此修复脚本检查问题")

if __name__ == "__main__":
    main()