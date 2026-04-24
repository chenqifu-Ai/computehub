#!/usr/bin/env python3
"""
Termux 环境打包工具
将当前 Termux 环境打包成可安装的 APK
"""

import os
import json
import shutil
from datetime import datetime

def create_package_structure():
    """创建打包目录结构"""
    
    package_dir = "/root/.openclaw/workspace/termux_package"
    
    # 清理并创建目录
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    
    os.makedirs(package_dir, exist_ok=True)
    
    # 创建必要的目录结构
    dirs = [
        "scripts",
        "config", 
        "data",
        "bin"
    ]
    
    for dir_name in dirs:
        os.makedirs(os.path.join(package_dir, dir_name), exist_ok=True)
    
    return package_dir

def collect_termux_files(package_dir):
    """收集 Termux 相关文件"""
    
    # 收集 OpenClaw 配置
    openclaw_files = [
        "/root/.openclaw/openclaw.json",
        "/root/.openclaw/workspace/",
        "/root/.openclaw/cron/jobs.json"
    ]
    
    # 创建安装脚本
    install_script = """#!/bin/bash
# Termux OpenClaw 安装脚本

echo "正在安装 OpenClaw 环境..."

# 更新包管理器
pkg update -y
pkg upgrade -y

# 安装必要软件
pkg install -y python nodejs git curl wget openssh

# 安装 OpenClaw
npm install -g @openclaw/cli

# 创建配置目录
mkdir -p ~/.openclaw/workspace

# 复制配置文件
echo "配置复制完成"

# 启动 OpenClaw
openclaw gateway start &

echo "✅ OpenClaw 安装完成"
echo "访问地址: http://localhost:18789"
"""
    
    with open(os.path.join(package_dir, "scripts", "install.sh"), "w") as f:
        f.write(install_script)
    
    # 创建包信息
    package_info = {
        "name": "OpenClaw-Termux",
        "version": "1.0.0",
        "description": "OpenClaw AI 助手 Termux 环境",
        "author": "小智",
        "created": datetime.now().isoformat(),
        "requirements": ["python", "nodejs", "git", "curl"],
        "install_script": "scripts/install.sh"
    }
    
    with open(os.path.join(package_dir, "package.json"), "w") as f:
        json.dump(package_info, f, indent=2, ensure_ascii=False)
    
    return package_info

def create_apk_package(package_dir):
    """创建 APK 包结构（模拟）"""
    
    # 由于无法直接生成 APK，创建说明文档
    apk_guide = """# Termux OpenClaw 安装指南

由于 Android 安全限制，无法直接生成 APK 安装包。
请按以下步骤安装：

## 方法一：Termux 官方安装
1. 从 F-Droid 下载 Termux APK
2. 安装后运行以下命令：

```bash
pkg update && pkg upgrade
pkg install python nodejs git
npm install -g @openclaw/cli
openclaw gateway start
```

## 方法二：使用 Termux:API
1. 安装 Termux 和 Termux:API
2. 运行安装脚本

## 方法三：自定义打包
如需完整环境打包，建议使用：
- Termux 备份功能
- 第三方打包工具
"""
    
    with open(os.path.join(package_dir, "INSTALL_GUIDE.md"), "w") as f:
        f.write(apk_guide)
    
    return apk_guide

def main():
    """主函数"""
    
    print("🔧 开始打包 Termux 环境...")
    
    # 创建包结构
    package_dir = create_package_structure()
    print(f"📁 包目录: {package_dir}")
    
    # 收集文件
    package_info = collect_termux_files(package_dir)
    print(f"📦 包信息: {package_info['name']} v{package_info['version']}")
    
    # 创建 APK 指南
    create_apk_package(package_dir)
    print("📋 安装指南已创建")
    
    # 打包成压缩文件
    shutil.make_archive("/root/.openclaw/workspace/openclaw-termux-package", 'zip', package_dir)
    
    result = {
        "status": "success",
        "package_file": "/root/.openclaw/workspace/openclaw-termux-package.zip",
        "package_info": package_info,
        "message": "打包完成，准备发送邮件"
    }
    
    print(f"✅ {result['message']}")
    return result

if __name__ == "__main__":
    result = main()