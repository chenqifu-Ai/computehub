#!/bin/bash
# 实际语音交互实施脚本
# 基于蓝牙音频重定向的真实方案

echo "🎯 开始实际语音交互实施"
echo "🔧 基于蓝牙音频重定向方案"
echo "⏰ 预计时间: 2-3小时"
echo "=========================================="

# 检查系统要求
check_requirements() {
    echo "🔍 检查系统要求..."
    
    # 检查蓝牙工具
    if command -v bluetoothctl >/dev/null 2>&1; then
        echo "✅ bluetoothctl 可用"
    else
        echo "❌ bluetoothctl 未安装"
        echo "请安装: sudo apt install bluez"
        exit 1
    fi
    
    # 检查音频工具
    if command -v pactl >/dev/null 2>&1; then
        echo "✅ pactl 可用"
    else
        echo "❌ pactl 未安装"
        echo "请安装: sudo apt install pulseaudio-utils"
        exit 1
    fi
    
    # 检查Python
    if command -v python3 >/dev/null 2>&1; then
        echo "✅ Python3 可用"
    else
        echo "❌ Python3 未安装"
        exit 1
    fi
}

# 蓝牙设备扫描
scan_bluetooth_devices() {
    echo ""
    echo "📡 扫描蓝牙设备..."
    echo "请确保小米音箱进入配对模式（通常长按电源键）"
    echo "扫描可能需要30-60秒..."
    
    # 启动扫描
    sudo systemctl start bluetooth
    sleep 2
    
    echo "正在扫描，请等待..."
    bluetoothctl scan on &
    SCAN_PID=$!
    sleep 15
    kill $SCAN_PID
    
    echo ""
    echo "找到的蓝牙设备:"
    bluetoothctl devices | head -10
    
    echo ""
    echo "请从上面列表中找到小米音箱的MAC地址（类似 XX:XX:XX:XX:XX:XX）"
    echo "然后编辑这个脚本，填入MAC地址"
}

# 简单的语音处理示例（实际可用的部分）
create_voice_demo() {
    echo ""
    echo "🎤 创建简单的语音交互演示..."
    
    # 创建简单的语音响应脚本
    cat > simple_voice_response.py << 'EOF'
#!/usr/bin/env python3
"""
简单的语音响应演示
实际可用的基础功能
"""

import os
import time
import subprocess

def play_audio(text):
    """使用文本转语音播放"""
    try:
        # 使用espeak进行文本转语音（如果安装）
        subprocess.run(["espeak", "-v", "zh", text])
        return True
    except:
        print(f"无法播放: {text}")
        return False

def simple_voice_interaction():
    """简单的语音交互演示"""
    print("🎧 简单的语音交互演示")
    print("💡 这不是真正的'小爱同学'对话模式")
    print("🔊 但这是真实可用的基础功能")
    print("=" * 50)
    
    # 简单的命令响应
    responses = {
        "你好": "你好！我是小智",
        "时间": f"现在时间是 {time.strftime('%H:%M')}",
        "天气": "今天天气不错",
        "停止": "好的，再见"
    }
    
    print("可用的简单命令:")
    for cmd in responses.keys():
        print(f"  - {cmd}")
    
    print("\n🎯 演示方式:")
    print("1. 手动输入命令（模拟语音输入）")
    print("2. 我会通过音箱响应（如果蓝牙已连接）")
    print("3. 说'停止'结束")
    
    while True:
        try:
            command = input("\n请输入命令: ").strip()
            if command == "停止":
                play_audio("好的，再见")
                break
            elif command in responses:
                response = responses[command]
                print(f"响应: {response}")
                play_audio(response)
            else:
                print("未知命令，请说: 你好, 时间, 天气, 停止")
                
        except KeyboardInterrupt:
            print("\n👋 演示结束")
            break

if __name__ == "__main__":
    simple_voice_interaction()
EOF
    
    chmod +x simple_voice_response.py
    echo "✅ 创建简单的语音响应脚本"
}

# 安装必要的依赖
install_dependencies() {
    echo ""
    echo "📦 安装必要的依赖..."
    
    # 检查并安装espeak（文本转语音）
    if ! command -v espeak >/dev/null 2>&1; then
        echo "安装 espeak (文本转语音)..."
        sudo apt update
        sudo apt install -y espeak espeak-data
    else
        echo "✅ espeak 已安装"
    fi
    
    echo "✅ 依赖安装完成"
}

# 显示实际使用说明
show_usage() {
    echo ""
    echo "🚀 实际使用说明:"
    echo "=========================================="
    echo "1. 首先完成蓝牙配对:"
    echo "   - 确保小米音箱蓝牙可被发现"
    echo "   - 运行: bluetoothctl scan on"
    echo "   - 找到音箱MAC地址"
    echo "   - 配对: bluetoothctl pair [MAC地址]"
    echo "   - 连接: bluetoothctl connect [MAC地址]"
    echo ""
    echo "2. 设置音频输出:"
    echo "   - 查看设备: pactl list short sinks"
    echo "   - 设置默认: pactl set-default-sink bluez_sink.[MAC地址]"
    echo ""
    echo "3. 测试音频:"
    echo "   - speaker-test -t wav -c 2"
    echo ""
    echo "4. 运行演示:"
    echo "   - ./simple_voice_response.py"
    echo ""
    echo "💡 重要说明:"
    echo "   - 这不是真正的'小爱同学开启对话模式'"
    echo "   - 这是真实可用的蓝牙音频重定向"
    echo "   - 语音交互需要通过其他方式输入"
    echo "   - 但音频输出确实通过小米音箱"
    echo ""
    echo "⏰ 预计实际耗时: 2-3小时（包括学习曲线）"
}

# 主执行流程
main() {
    echo "🎯 语音交互真实实施开始"
    echo "=========================================="
    
    check_requirements
    install_dependencies
    create_voice_demo
    
    echo ""
    echo "🔍 现在需要你的参与:"
    echo "=========================================="
    scan_bluetooth_devices
    
    show_usage
    
    echo ""
    echo "✅ 实际实施准备完成!"
    echo "🔧 请按照上面的说明操作"
    echo "🎯 这是一个真实可行的方案，不是虚假承诺"
}

# 执行主函数
main