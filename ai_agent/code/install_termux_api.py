#!/usr/bin/env python3
"""
Termux:API 安装脚本
"""

import os

def create_install_script():
    """创建安装脚本"""
    
    script_content = """#!/bin/bash
# Termux:API 安装脚本

echo "🔧 开始安装 Termux:API 环境..."

# 1. 安装 Termux:API APK (需要手动安装)
echo "📱 第一步：手动安装 Termux:API APK"
echo "请从 F-Droid 下载并安装："
echo "https://f-droid.org/packages/com.termux.api/"
echo ""

# 2. 安装必要的包
echo "📦 第二步：安装软件包"
pkg update -y
pkg upgrade -y
pkg install -y termux-api

# 3. 授予权限
echo "🔐 第三步：授予权限"
echo "请在 Android 设置中授予 Termux:API 以下权限："
echo "- 摄像头权限"
echo "- 闪光灯权限"
echo "- 存储权限"
echo ""

# 4. 测试功能
echo "🧪 第四步：测试功能"
echo "测试闪光灯控制："
termux-torch on
echo "闪光灯已打开，等待3秒..."
sleep 3
termux-torch off
echo "闪光灯已关闭"

# 5. 创建控制脚本
echo "📝 第五步：创建控制脚本"
cat > ~/flashlight_control.sh << 'EOF'
#!/bin/bash
# 闪光灯控制脚本

case "$1" in
    "on")
        termux-torch on
        echo "🔦 闪光灯已打开"
        ;;
    "off")
        termux-torch off
        echo "🔦 闪光灯已关闭"
        ;;
    "blink")
        for i in {1..3}; do
            termux-torch on
            sleep 0.5
            termux-torch off
            sleep 0.5
        done
        echo "🔦 闪光灯闪烁完成"
        ;;
    *)
        echo "用法: $0 {on|off|blink}"
        ;;
esac
EOF

chmod +x ~/flashlight_control.sh

# 6. 创建摄像头脚本
echo "📷 第六步：创建摄像头脚本"
cat > ~/camera_control.sh << 'EOF'
#!/bin/bash
# 摄像头控制脚本

case "$1" in
    "photo")
        termux-camera-photo /sdcard/photo_$(date +%Y%m%d_%H%M%S).jpg
        echo "📸 照片已保存到 /sdcard/"
        ;;
    "info")
        echo "摄像头信息："
        termux-camera-info
        ;;
    *)
        echo "用法: $0 {photo|info}"
        ;;
esac
EOF

chmod +x ~/camera_control.sh

echo ""
echo "✅ Termux:API 安装完成！"
echo ""
echo "📋 可用命令："
echo "- 闪光灯控制: ~/flashlight_control.sh on/off/blink"
echo "- 摄像头控制: ~/camera_control.sh photo/info"
echo "- 其他功能: termux-* 命令"
"""
    
    # 保存脚本
    script_path = "/root/.openclaw/workspace/termux_api_install.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # 创建简化版一键安装
    simple_script = """#!/bin/bash
# Termux:API 一键安装简化版

echo "📱 请先手动安装 Termux:API APK"
echo "下载地址: https://f-droid.org/packages/com.termux.api/"
read -p "安装完成后按回车继续..."

pkg install -y termux-api
chmod +x termux_api_install.sh
./termux_api_install.sh
"""
    
    simple_path = "/root/.openclaw/workspace/install_termux_api_simple.sh"
    with open(simple_path, 'w') as f:
        f.write(simple_script)
    
    return script_path, simple_path

def create_test_script():
    """创建测试脚本"""
    
    test_script = """#!/bin/bash
# Termux:API 功能测试

echo "🧪 开始测试 Termux:API 功能..."

# 测试闪光灯
echo "测试闪光灯..."
if command -v termux-torch >/dev/null 2>&1; then
    termux-torch on
    echo "✅ 闪光灯打开成功"
    sleep 2
    termux-torch off
    echo "✅ 闪光灯关闭成功"
else
    echo "❌ termux-torch 命令不存在"
fi

# 测试摄像头
echo "测试摄像头..."
if command -v termux-camera-photo >/dev/null 2>&1; then
    termux-camera-photo /sdcard/test_photo.jpg
    if [ -f "/sdcard/test_photo.jpg" ]; then
        echo "✅ 拍照成功"
    else
        echo "❌ 拍照失败"
    fi
else
    echo "❌ termux-camera-photo 命令不存在"
fi

# 测试其他功能
echo "测试其他功能..."
termux-battery-status && echo "✅ 电池状态正常"
termux-location && echo "✅ 位置服务正常"

echo "测试完成！"
"""
    
    test_path = "/root/.openclaw/workspace/test_termux_api.sh"
    with open(test_path, 'w') as f:
        f.write(test_script)
    
    return test_path

def main():
    """主函数"""
    
    print("🔧 创建 Termux:API 安装脚本...")
    
    # 创建安装脚本
    install_script, simple_script = create_install_script()
    print(f"📝 安装脚本: {install_script}")
    print(f"📝 简化脚本: {simple_script}")
    
    # 创建测试脚本
    test_script = create_test_script()
    print(f"🧪 测试脚本: {test_script}")
    
    # 创建使用指南
    guide = """# Termux:API 使用指南

## 安装步骤
1. 下载 Termux:API APK: https://f-droid.org/packages/com.termux.api/
2. 运行安装脚本: ./install_termux_api_simple.sh
3. 授予必要权限

## 可用功能
- 🔦 闪光灯控制
- 📷 拍照功能
- 📍 位置服务
- 🔋 电池状态
- 📞 电话功能
- 📧 短信功能

## 常用命令
- 闪光灯: termux-torch on/off
- 拍照: termux-camera-photo <filename>
- 电池: termux-battery-status
- 位置: termux-location

## 控制脚本
- 闪光灯控制: ~/flashlight_control.sh
- 摄像头控制: ~/camera_control.sh
"""
    
    guide_path = "/root/.openclaw/workspace/TERMUX_API_GUIDE.md"
    with open(guide_path, 'w') as f:
        f.write(guide)
    
    print(f"📖 使用指南: {guide_path}")
    print("")
    print("✅ Termux:API 安装包创建完成！")
    print("📱 请先手动安装 Termux:API APK，然后运行安装脚本")

if __name__ == "__main__":
    main()