#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
适配层版本发布工具
用于将 qwen36_adapter 发布到 PyPI 或内部包管理器
"""
import os
import sys
import subprocess
import json
from pathlib import Path

def get_current_version():
    """获取当前适配器版本"""
    adapter_path = Path(__file__).parent.parent / "config" / "qwen36_adapter.py"
    content = adapter_path.read_text()
    
    for line in content.split("\n"):
        if line.startswith("__version__"):
            return line.split('"')[1]
    return "unknown"

def build_package():
    """构建 Python 包"""
    print("📦 构建适配层包...")
    
    # 创建临时构建目录
    build_dir = Path(__file__).parent.parent.parent / "dist"
    build_dir.mkdir(exist_ok=True)
    
    # 复制适配层文件
    adapter_src = Path(__file__).parent.parent / "config" / "qwen36_adapter.py"
    adapter_dest = build_dir / "qwen36_adapter.py"
    adapter_dest.write_text(adapter_src.read_text())
    
    # 创建 setup.py
    setup_py = build_dir / "setup.py"
    version = get_current_version()
    setup_py.write_text(f'''
from setuptools import setup, find_packages

setup(
    name="qwen36-adapter",
    version="{version}",
    py_modules=["qwen36_adapter"],
    description="qwen3.6-35b API 统一适配层",
    author="小智 AI",
    license="MIT",
    python_requires=">=3.10",
)
''')
    
    print(f"✅ 包构建完成: {build_dir}")
    return build_dir

def publish_to_pypi():
    """发布到 PyPI"""
    print("🚀 发布到 PyPI...")
    
    # 检查是否有 PyPI API Token
    if not os.getenv("PYPI_API_TOKEN"):
        print("❌ 未设置 PYPI_API_TOKEN 环境变量")
        return False
    
    # 构建并上传
    result = subprocess.run(
        ["twine", "upload", "dist/*"],
        cwd=str(Path(__file__).parent.parent.parent),
        env={**os.environ, "TWINE_USERNAME": "__token__", "TWINE_PASSWORD": os.getenv("PYPI_API_TOKEN")}
    )
    
    if result.returncode == 0:
        print("✅ 发布成功!")
        return True
    else:
        print("❌ 发布失败")
        return False

def publish_to_internal_registry():
    """发布到内部包管理器"""
    print("📦 发布到内部包管理器...")
    
    # 这里可以根据实际情况配置内部包管理器的发布命令
    version = get_current_version()
    print(f"  版本: {version}")
    print("  发布命令: 请配置内部包管理器的发布命令")
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 适配层版本发布工具")
    print("=" * 60)
    
    version = get_current_version()
    print(f"📋 当前版本: {version}")
    
    action = input("📝 选择操作 [build/publish/all]: ").strip().lower()
    
    if action in ["build", "all"]:
        build_package()
    
    if action in ["publish", "all"]:
        # 选择发布目标
        target = input("🎯 发布目标 [pypi/internal/both]: ").strip().lower()
        
        if target in ["pypi", "both"]:
            publish_to_pypi()
        
        if target in ["internal", "both"]:
            publish_to_internal_registry()
    
    print("\n✅ 发布流程完成")

if __name__ == "__main__":
    main()
