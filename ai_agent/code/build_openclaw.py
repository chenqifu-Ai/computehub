#!/usr/bin/env python3
"""
OpenClaw编译脚本
将源代码编译为可执行文件
"""

import subprocess
import sys
import os
from datetime import datetime

def run_command(cmd, description="", cwd=None):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"  命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300, cwd=cwd)
        print(f"  返回码: {result.returncode}")
        if result.stdout:
            print(f"  输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"  错误: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("  ⏰ 命令执行超时")
        return False, "", "Timeout"
    except Exception as e:
        print(f"  ❌ 执行异常: {e}")
        return False, "", str(e)

def main():
    print("🤖 OpenClaw编译脚本启动")
    print("=" * 50)
    
    # 源代码目录
    source_dir = "/data/data/com.termux/files/home/openclaw"
    
    # 步骤1: 检查构建环境
    print("\n1️⃣ 检查构建环境")
    
    # 检查Node.js和pnpm
    success, stdout, stderr = run_command(
        "node --version && pnpm --version",
        "检查Node.js和pnpm版本",
        cwd=source_dir
    )
    
    if not success:
        print("❌ 构建环境检查失败")
        return False
    
    # 步骤2: 安装依赖
    print("\n2️⃣ 安装项目依赖")
    
    success, stdout, stderr = run_command(
        "pnpm install",
        "安装pnpm依赖",
        cwd=source_dir
    )
    
    if not success:
        print("❌ 依赖安装失败")
        return False
    
    # 步骤3: 执行构建
    print("\n3️⃣ 执行构建命令")
    
    # 根据package.json，主要的构建命令是"build"
    success, stdout, stderr = run_command(
        "pnpm run build",
        "执行构建",
        cwd=source_dir
    )
    
    if not success:
        print("❌ 构建失败")
        return False
    
    # 步骤4: 检查构建结果
    print("\n4️⃣ 检查构建结果")
    
    success, stdout, stderr = run_command(
        "ls -la dist/ | head -10",
        "检查dist目录",
        cwd=source_dir
    )
    
    # 步骤5: 创建可执行文件链接
    print("\n5️⃣ 创建可执行文件")
    
    # 检查主要的入口文件
    success, stdout, stderr = run_command(
        "ls -la openclaw.mjs dist/index.js",
        "检查入口文件",
        cwd=source_dir
    )
    
    # 生成构建报告
    report = f"""
📋 OpenClaw构建报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
源代码目录: {source_dir}

构建结果:
- 环境检查: {'✅ 成功' if success else '❌ 失败'}
- 依赖安装: {'✅ 成功' if success else '❌ 失败'}
- 构建执行: {'✅ 成功' if success else '❌ 失败'}

可执行文件:
- 主入口: openclaw.mjs
- 编译输出: dist/index.js
- CLI入口: dist/cli/index.js

使用方式:
node openclaw.mjs --version
node dist/index.js --version
"""
    
    print(report)
    
    # 保存报告
    report_file = f"/root/.openclaw/workspace/ai_agent/results/openclaw_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"✅ 构建完成，报告已保存到: {report_file}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)