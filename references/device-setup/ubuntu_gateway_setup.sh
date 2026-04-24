#!/bin/bash
# Ubuntu环境OpenClaw安装和启动脚本

echo "🐧 开始在Ubuntu环境中安装OpenClaw..."

# 1. 在Ubuntu中安装OpenClaw
echo "📦 安装OpenClaw 2026.3.13..."
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- npm install -g openclaw@2026.3.13"

echo "✅ 安装完成，验证版本..."

# 2. 验证安装
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- openclaw --version"

echo ""
echo "🚀 启动Gateway服务..."

# 3. 停止现有服务
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- pkill -f openclaw 2>/dev/null || true"

sleep 2

# 4. 在Ubuntu中启动Gateway服务（使用完整服务模式）
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- nohup openclaw gateway start > ~/gateway.out 2> ~/gateway.err &"

echo "⏳ 等待服务启动..."
sleep 5

echo "🔍 检查服务状态..."

# 5. 检查服务状态
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- ps aux | grep openclaw | grep -v grep"

echo ""
echo "📋 检查端口监听..."

# 6. 检查端口监听
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- netstat -tln | grep :18789 || echo '端口检查工具不可用'"

echo ""
echo "📝 查看启动日志..."

# 7. 查看启动日志
sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \
    "proot-distro login ubuntu -- tail -5 ~/gateway.out 2>/dev/null || echo '无输出日志'"

sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘极速版状态: ✅ 正常 (v2极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 18:31% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 18:31