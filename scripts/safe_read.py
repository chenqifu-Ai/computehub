
#!/usr/bin/env python3
"""
安全文件读取包装器 - 防止EISDIR和偏移量错误
"""

import os
import sys
import json

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
