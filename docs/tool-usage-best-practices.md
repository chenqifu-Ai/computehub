# OpenClaw工具使用最佳实践

## 🚨 常见工具错误及解决方案

### 错误1: `EISDIR: illegal operation on a directory`
**问题**: 尝试读取目录而不是文件
**原因**: 工具期望文件路径但收到了目录路径

**解决方案**:
```bash
# 错误用法
read {"path": "memory"}  # memory是目录

# 正确用法  
read {"path": "memory/2026-04-23.md"}  # 具体文件
read {"path": "MEMORY.md"}  # 具体文件
```

### 错误2: `Offset X is beyond end of file (Y lines total)`
**问题**: 尝试读取超出文件范围的行
**原因**: 偏移量参数大于文件实际行数

**解决方案**:
```bash
# 错误用法（文件只有1040行）
read {"path": "MEMORY.md", "offset": 14000, "limit": 50}

# 正确用法
read {"path": "MEMORY.md", "offset": 1, "limit": 50}  # 从第1行开始
read {"path": "MEMORY.md", "offset": 1000, "limit": 40}  # 最后40行
```

## 🔧 预防措施

### 1. 使用安全读取脚本
新提供了安全读取包装器，自动处理错误：

```bash
# 使用安全读取脚本
python scripts/safe_read.py <文件路径> [偏移量] [限制]

# 示例
python scripts/safe_read.py MEMORY.md 1 10
python scripts/safe_read.py memory/2026-04-23.md 5 20
```

### 2. 预先检查文件信息
在读取前检查文件状态：

```python
# 检查文件是否存在和类型
import os
path = "MEMORY.md"

if not os.path.exists(path):
    print("文件不存在")
elif os.path.isdir(path):
    print("这是目录，不是文件")
else:
    # 安全读取文件
    with open(path, 'r') as f:
        lines = f.readlines()
    print(f"文件有 {len(lines)} 行")
```

### 3. 合理的偏移量检查
```python
def safe_offset(offset, total_lines):
    """确保偏移量在有效范围内"""
    if offset < 1:
        return 1
    if offset > total_lines:
        return total_lines
    return offset
```

## 📊 主要文件行数参考

| 文件 | 行数 | 建议偏移量范围 |
|------|------|----------------|
| MEMORY.md | ~1040 | 1-1040 |
| AGENTS.md | ~254 | 1-254 |
| SOUL.md | ~90 | 1-90 |
| USER.md | ~21 | 1-21 |
| TOOLS.md | ~99 | 1-99 |

## 🛡️ 错误处理最佳实践

### 1. 始终验证输入
```python
# 在工具调用前验证
def validate_read_params(path, offset=1, limit=50):
    if not os.path.exists(path):
        return {"error": "文件不存在"}
    if os.path.isdir(path):
        return {"error": "路径是目录"}
    
    # 读取文件获取实际行数
    with open(path, 'r') as f:
        lines = f.readlines()
    
    if offset > len(lines):
        return {"error": f"偏移量超出范围"}
    
    return {"valid": True, "total_lines": len(lines)}
```

### 2. 提供有用的错误信息
```python
# 不好的错误信息
{"error": "读取失败"}

# 好的错误信息  
{
  "error": "偏移量 14000 超出文件范围",
  "file": "MEMORY.md",
  "total_lines": 1040,
  "suggestion": "请使用偏移量 1-1040"
}
```

### 3. 日志记录和监控
```bash
# 记录工具使用情况
echo "$(date): 工具调用 - read {path: $path, offset: $offset}" >> tool_usage.log
```

## 🔍 调试技巧

### 1. 检查文件状态
```bash
# 检查文件基本信息
ls -la 文件路径
wc -l 文件路径    # 行数统计
file 文件路径     # 文件类型检查
```

### 2. 使用调试模式
```python
# 在工具中添加调试信息
def debug_read(path, offset, limit):
    print(f"调试: 读取 {path}, 偏移量 {offset}, 限制 {limit}")
    
    if not os.path.exists(path):
        print(f"调试: 文件不存在")
        return None
    
    # ... 其余逻辑
```

### 3. 监控工具调用
查看OpenClaw日志了解具体的工具调用参数：
```bash
tail -f /var/log/openclaw/tools.log
grep "read failed" /var/log/openclaw/error.log
```

## 📝 总结

1. **始终验证**: 在读取前检查文件存在性和类型
2. **合理偏移**: 确保偏移量在文件行数范围内  
3. **使用安全工具**: 优先使用 `scripts/safe_read.py`
4. **提供详细错误**: 给出具体的错误信息和解决方案
5. **监控日志**: 定期检查工具使用日志

通过遵循这些最佳实践，可以避免大多数工具使用错误，提高系统稳定性。