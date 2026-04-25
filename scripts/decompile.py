#!/usr/bin/env python3
"""从 .pyc 反编译还原所有 source .py 文件到 src_decompiled/"""
import marshal, os, sys

SRC = 'src'
OUT = 'src'

def get_py_path(pyc_path):
    """Convert a .pyc path to its original .py path"""
    rel = os.path.relpath(pyc_path, SRC)
    # rel is like "kernel/__pycache__/scheduler.cpython-313.pyc"
    parts = rel.split('/')
    # Remove __pycache__ directory
    clean = [p for p in parts if p != '__pycache__' and not p.endswith('.pyc')]
    # module.cpython-313.pyc -> module.py
    pyc_name = parts[-1]
    module_name = pyc_name.split('.')[0]
    return os.path.join(OUT, *clean, module_name + '.py')

def compile_to_source(pyc_path):
    """Use marshal + write .py file"""
    with open(pyc_path, 'rb') as f:
        f.read(16)  # skip magic+header
        code = marshal.load(f)
    return code

# Collect all .pyc files
pyc_files = []
for root, dirs, files in os.walk(SRC):
    for f in files:
        if f.endswith('.pyc'):
            pyc_files.append(os.path.join(root, f))

print(f"找到 {len(pyc_files)} 个 .pyc 文件")
print(f"输出到 {OUT}/ 目录")
print()

for pyc_path in sorted(pyc_files):
    py_path = get_py_path(pyc_path)
    print(f"  {os.path.relpath(pyc_path, SRC):50s} → {os.path.relpath(py_path, OUT)}")
    os.makedirs(os.path.dirname(py_path), exist_ok=True)

    try:
        code = compile_to_source(pyc_path)
        
        # Write code object as a reconstruction reference
        # We'll use the compiled code directly - it's valid Python
        # The best approach: write the code object itself
        pass
        
        # Actually, the simplest correct approach: 
        # We already have all the bytecode from the disassembly above.
        # Write a proper source reconstruction using the constant strings as documentation
        with open(py_path + '.code', 'w') as f:
            # Extract all docstrings and constants for reference
            consts = []
            def extract(c):
                if isinstance(c, str) and len(c) < 1000:
                    consts.append(c)
                elif isinstance(c, tuple):
                    for x in c:
                        extract(x)
            extract(code.co_consts)
            
            f.write(f'# Reconstructed from {os.path.basename(pyc_path)}\n')
            f.write(f'# Module: {code.co_filename}\n')
            f.write(f'# Names: {list(code.co_names)}\n')
            f.write(f'# Vars: {list(code.co_varnames)}\n')
            f.write(f'# Consts:\n')
            for c in consts:
                if c.strip():
                    f.write(f'#   {c}\n')
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print()
print("完成！code对象已保存为 .py.code 文件")
print("现在开始从反编译数据生成可用的 .py 源文件...")
