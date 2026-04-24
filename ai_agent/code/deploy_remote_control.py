#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程控制部署脚本
目标：将远程控制方案部署到目标设备
"""

import subprocess
from pathlib import Path

def check_target_access():
    """检查目标设备访问性"""
    print("🔍 检查目标设备 192.168.2.134 访问性...")
    
    # 检查网络连通性
    try:
        result = subprocess.run(
            ["ping", "-c", "3", "192.168.2.134"],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            print("✅ 网络连通性正常")
            return True
        else:
            print("❌ 网络连接失败")
            return False
    except subprocess.TimeoutExpired:
        print("⏰ 网络检查超时")
        return False

def deploy_ssh_setup():
    """部署SSH设置脚本到目标设备"""
    print("🚀 部署SSH设置脚本到目标设备...")
    
    # 检查是否有SSH访问
    try:
        # 尝试复制脚本到目标设备
        result = subprocess.run([
            "scp", "/tmp/enable_ssh.sh", 
            "chen@192.168.2.134:/tmp/enable_ssh.sh"
        ], capture_output=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ SSH设置脚本已部署到目标设备")
            
            # 在目标设备上执行脚本
            exec_result = subprocess.run([
                "ssh", "chen@192.168.2.134",
                "chmod +x /tmp/enable_ssh.sh && echo '脚本就绪，可执行: sudo bash /tmp/enable_ssh.sh'"
            ], capture_output=True, timeout=30)
            
            if exec_result.returncode == 0:
                print("✅ 脚本在目标设备上准备就绪")
                print(exec_result.stdout.decode())
                return True
            else:
                print("❌ 在目标设备上准备脚本失败")
                return False
                
        else:
            print("❌ 无法部署脚本到目标设备")
            print(f"错误: {result.stderr.decode()}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ SSH访问不可用，需要其他部署方式")
        return False

def generate_deployment_guide():
    """生成部署指南"""
    guide = """# 🚀 远程控制部署指南

## 目标设备: 192.168.2.134 (Windows主机)

## 📋 部署前检查

### 1. 网络连通性
```bash
ping 192.168.2.134
```

### 2. 当前访问方式
- ❌ SSH: 连接被拒绝 (端口22未开放)
- ❌ RDP: 需要确认是否启用
- ✅ 网络: 可达

## 🎯 部署方案

### 方案A: 物理访问部署 (推荐)
如果可以直接操作目标设备:

1. **在目标设备上运行SSH设置脚本**
   ```bash
   # 将enable_ssh.sh复制到目标设备
   # 然后执行:
   sudo bash /tmp/enable_ssh.sh
   ```

2. **启用远程桌面**
   ```
   - 右键"此电脑" → 属性 → 远程桌面 → 启用
   - 防火墙允许端口3389
   ```

### 方案B: 远程部署
如果已有其他远程访问方式:

1. **通过现有远程方式部署**
   - 使用现有的远程桌面连接
   - 或者使用其他远程管理工具

2. **部署脚本**
   ```bash
   # 复制脚本到目标设备
   scp /tmp/enable_ssh.sh chen@192.168.2.134:/tmp/
   
   # 执行设置  
   ssh chen@192.168.2.134 "chmod +x /tmp/enable_ssh.sh"
   ```

## 📁 可用部署文件

### 在本地生成的脚本:
- `/tmp/enable_ssh.sh` - SSH服务设置脚本
- `/tmp/windows_remote.bat` - Windows远程桌面脚本
- `/tmp/windows_remote_guide.md` - 详细设置指南

### 需要部署到目标的:
- `enable_ssh.sh` - 需要复制到目标设备执行

## ⚡ 快速部署命令

### 如果SSH可用:
```bash
# 复制脚本到目标
scp /tmp/enable_ssh.sh chen@192.168.2.134:/tmp/

# 设置执行权限
ssh chen@192.168.2.134 "chmod +x /tmp/enable_ssh.sh"

# 执行设置 (需要sudo权限)
ssh chen@192.168.2.134 "echo '密码' | sudo -S bash /tmp/enable_ssh.sh"
```

### 如果只有物理访问:
1. 将脚本复制到U盘
2. 在目标设备上运行
3. 执行设置命令

## 🔧 备用方案

如果无法直接部署，可以考虑:
1. **TeamViewer/AnyDesk** - 第三方远程工具
2. **Windows远程协助** - 内置功能
3. **物理访问** - 直接操作设备

## 📞 支持信息

- **IP地址**: 192.168.2.134
- **用户名**: chen
- **密码**: c9fc9f,.
- **系统**: Windows

---
*部署状态: 等待执行*
"""
    
    guide_path = Path("/tmp/deployment_guide.md")
    guide_path.write_text(guide)
    return guide_path

def main():
    """主函数"""
    print("🚀 远程控制部署执行")
    print("=" * 50)
    
    # 检查目标访问性
    if not check_target_access():
        print("❌ 目标设备网络不可达，无法直接部署")
        print("💡 需要物理访问或其他远程方式")
    else:
        print("✅ 目标设备网络可达")
        
        # 尝试部署SSH设置
        if not deploy_ssh_setup():
            print("❌ 自动部署失败，需要手动部署")
    
    # 生成部署指南
    guide = generate_deployment_guide()
    print(f"\n📖 部署指南已生成: {guide}")
    
    print("\n" + "=" * 50)
    print("🎯 下一步行动:")
    print("1. 如果可以直接访问目标设备:")
    print("   - 运行 /tmp/enable_ssh.sh")
    print("   - 或手动启用远程桌面")
    print("2. 如果需要远程部署:")
    print("   - 使用现有远程方式连接")
    print("   - 复制并执行设置脚本")
    
    print("\n" + "=" * 50)
    print("⚡ 立即执行手动部署:")
    print("# 复制脚本到目标设备")
    print("scp /tmp/enable_ssh.sh chen@192.168.2.134:/tmp/")
    print("# 在目标设备上执行")
    print("sudo bash /tmp/enable_ssh.sh")

if __name__ == "__main__":
    main()