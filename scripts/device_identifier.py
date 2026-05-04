#!/usr/bin/env python3
"""
设备唯一标识符识别脚本
用于识别华为设备 HWI-AL00
"""

import subprocess
import re

def get_device_identifier(ip_address="192.168.2.156", port=8022, username="u0_a46", password="123"):
    """获取设备唯一标识符"""
    
    try:
        # 通过SSH获取设备信息
        cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {username}@{ip_address}"
        
        # 获取设备型号
        model_cmd = "getprop ro.product.model"
        result = subprocess.run(f"{cmd} '{model_cmd}'", shell=True, capture_output=True, text=True, timeout=10)
        model = result.stdout.strip() if result.returncode == 0 else "未知"
        
        # 获取Android构建指纹
        fingerprint_cmd = "getprop ro.bootimage.build.fingerprint"
        result = subprocess.run(f"{cmd} '{fingerprint_cmd}'", shell=True, capture_output=True, text=True, timeout=10)
        fingerprint = result.stdout.strip() if result.returncode == 0 else "未知"
        
        # 获取序列号
        serial_cmd = "getprop ro.serialno"
        result = subprocess.run(f"{cmd} '{serial_cmd}'", shell=True, capture_output=True, text=True, timeout=10)
        serial = result.stdout.strip() if result.returncode == 0 else "未知"
        
        return {
            "ip_address": ip_address,
            "model": model,
            "fingerprint": fingerprint,
            "serial": serial,
            "status": "在线" if model != "未知" else "离线"
        }
        
    except subprocess.TimeoutExpired:
        return {"status": "连接超时"}
    except Exception as e:
        return {"status": f"错误: {e}"}

def identify_device(device_info):
    """识别设备是否为已知的华为设备"""
    
    # 已知设备标识
    known_devices = {
        "HWI-AL00": {
            "model": "HWI-AL00",
            "fingerprint": "Huawei/generic_a15/generic_a15:9/PPR1.180610.011/root202005281627:user/test-keys",
            "name": "华为机器",
            "username": "u0_a46",
            "password": "123"
        }
    }
    
    # 检查设备型号匹配
    if device_info["model"] in known_devices:
        known_device = known_devices[device_info["model"]]
        
        # 进一步验证指纹匹配
        if device_info["fingerprint"] == known_device["fingerprint"]:
            return {
                "identified": True,
                "device_name": known_device["name"],
                "username": known_device["username"],
                "password": known_device["password"],
                "confidence": "高"
            }
    
    return {"identified": False, "confidence": "低"}

def main():
    """主函数"""
    print("🔍 设备识别系统")
    print("正在识别设备 192.168.2.156...")
    
    # 获取设备信息
    device_info = get_device_identifier()
    
    if device_info["status"] != "在线":
        print(f"❌ 设备状态: {device_info['status']}")
        return
    
    print(f"📱 设备型号: {device_info['model']}")
    print(f"🔖 构建指纹: {device_info['fingerprint']}")
    print(f"📟 序列号: {device_info['serial']}")
    
    # 识别设备
    identification = identify_device(device_info)
    
    if identification["identified"]:
        print(f"✅ 设备识别成功: {identification['device_name']}")
        print(f"   🤖 用户名: {identification['username']}")
        print(f"   🔒 密码: {identification['password']}")
        print(f"   🎯 可信度: {identification['confidence']}")
    else:
        print("❌ 设备未识别，可能是新设备")
        print("💡 建议: 将设备信息添加到已知设备数据库")

if __name__ == "__main__":
    main()