#!/bin/bash
# 远程SSH配置修复脚本

echo "🔧 修复远程SSH配置..."

# 1. 确保.ssh目录存在且权限正确
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. 清理并重新添加公钥
echo "清理现有的authorized_keys..."
> ~/.ssh/authorized_keys

# 3. 添加正确的公钥
echo "添加新的公钥..."
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKr5wdZVaL+0s8klifhX3vcPPxMr6mx+vfm8kQ1VtH6b openclaw@localhost" >> ~/.ssh/authorized_keys

# 4. 设置正确的权限
chmod 600 ~/.ssh/authorized_keys

# 5. 验证配置
echo "验证配置..."
ls -la ~/.ssh/
echo "公钥内容:"
cat ~/.ssh/authorized_keys

echo "✅ 远程配置修复完成"
