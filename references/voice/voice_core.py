#!/usr/bin/env python3
"""
简单语音交互核心
直接干活，不废话
"""

import subprocess
import time

def play_audio(text):
    """播放语音"""
    try:
        # 尝试使用espeak
        subprocess.run(["espeak", "-v", "zh", text], 
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      timeout=3)
        return True
    except:
        # 失败就打印文本
        print(f"语音: {text}")
        return False

def main():
    print("🎧 语音交互就绪")
    print("💡 直接对手机或电脑说话")
    print("🔊 我会通过音箱响应")
    
    # 简单命令映射
    commands = {
        "你好": "你好，我是小智",
        "时间": f"现在时间 {time.strftime('%H:%M')}",
        "日期": f"今天 {time.strftime('%m月%d日')}",
        "测试": "语音测试成功",
        "退出": "好的，再见"
    }
    
    while True:
        try:
            # 模拟语音输入（实际需要语音识别）
            cmd = input("请输入命令: ").strip()
            
            if cmd == "退出":
                play_audio("好的，再见")
                break
            elif cmd in commands:
                play_audio(commands[cmd])
            else:
                print("未知命令，尝试: 你好, 时间, 日期, 测试, 退出")
                
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
