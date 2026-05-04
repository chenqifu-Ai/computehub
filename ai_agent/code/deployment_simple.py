#!/usr/bin/env python3
# OpenClaw装机技能核心实现

print("🚀 OpenClaw装机技能实现方式")
print("=" * 50)

# 1. 设备检测
print("\n🔧 1. 设备检测:")
print("   - SSH连接测试: sshpass -p密码 ssh -p端口 用户@主机 '命令'")
print("   - 系统信息收集: uname -a, free -h, df -h")
print("   - 资源评估: 内存、磁盘、网络")

# 2. OpenClaw安装  
print("\n📦 2. OpenClaw安装:")
print("   - 版本选择: openclaw@latest, openclaw@beta, openclaw@dev")
print("   - 安装命令: npm install -g 版本号")
print("   - 验证: openclaw --version")

# 3. 配置同步
print("\n🔄 3. 配置同步:")
print("   - 备份: tar -czf backup_时间戳.tar.gz .openclaw/")
print("   - 同步: tar -czf - -C .openclaw . | ssh tar -xzf - -C .openclaw")
print("   - 包含: workspace, extensions, config, skills")

# 4. 服务管理
print("\n⚡ 4. 服务管理:")
print("   - 停止服务: pkill -f 'openclaw'")
print("   - 启动服务: openclaw gateway --port 端口号 &")
print("   - 健康检查: curl http://127.0.0.1:端口/health")

# 5. 验证部署
print("\n✅ 5. 验证部署:")
print("   - 文件检查: ls -la .openclaw/")
print("   - 配置验证: grep apiKey .openclaw/openclaw.json")
print("   - 服务状态: netstat -tln | grep :端口")

print("\n🎯 核心命令示例:")
print("=" * 50)
print("# 完整部署命令:")
print("sshpass -p123 ssh -p8022 u0_a207@192.168.1.19 \\")
print("  'npm install -g openclaw@latest && \\")
print("   tar -czf - -C ~/.openclaw . | \\")
print("   sshpass -p123 ssh -p8022 u0_a207@192.168.1.19 \\")
print("     tar -xzf - -C ~/.openclaw && \\")
print("   openclaw gateway --port 18789 &'")

print("\n💡 特点:")
print("✅ 自动化 - 无需人工干预")
print("✅ 安全 - 配置备份和错误处理")  
print("✅ 灵活 - 支持自定义参数")
print("✅ 可靠 - 每一步都有验证")

print("\n📁 脚本位置: ~/.openclaw/workspace/skills/zhuangji-skill/deploy.sh")