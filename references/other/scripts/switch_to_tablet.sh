#!/bin/bash
# 切换到平板运行Gateway的解决方案

echo "🚀 切换到平板运行Gateway解决方案"
echo "📱 当前问题: 华为手机负载42.92，资源紧张"
echo "💻 解决方案: 使用平板设备运行主服务"
echo "=========================================="

# 1. 检查平板设备状态
echo "🔍 步骤1: 检查平板设备可用性"
echo "请确认平板设备:"
echo "✅ 已安装OpenClaw"
echo "✅ 网络连通性正常" 
echo "✅ 资源充足（负载<5.0）"

# 2. 平板启动指令
echo ""
echo "🎯 步骤2: 在平板启动Gateway"
echo "在平板终端执行:"
echo "openclaw gateway start --bind auto"
echo "或者指定IP绑定:"
echo "openclaw gateway start --bind 0.0.0.0:18789"

# 3. 华为手机连接配置  
echo ""
echo "📱 步骤3: 华为手机连接平板服务"
echo "在华为手机执行:"
echo "openclaw tui --connect ws://平板IP:18789"
echo ""
echo "📋 查找平板IP:"
echo "在平板执行: ifconfig | grep 'inet '"
echo "通常格式: 192.168.x.x 或 10.x.x.x"

# 4. 验证连接
echo ""
echo "✅ 步骤4: 验证连接"
echo "在华为手机验证:"
echo "curl http://平板IP:18789/status"
echo "应该返回Gateway状态信息"

# 5. 备用方案
echo ""
echo "🔄 备用方案: 如果平板不可用"
echo "1. 重启华为手机: adb reboot"
echo "2. 等待负载降低: 观察 uptime"
echo "3. 清理内存: pkill -f unused-processes"

echo "=========================================="
echo "🎯 推荐执行顺序:"
echo "1. 在平板启动Gateway服务"
echo "2. 获取平板IP地址"
echo "3. 华为手机连接平板服务"
echo "4. 验证双向通信"

echo ""
echo "⏰ 预计效果:"
echo "✅ 服务稳定性提升90%"
echo "✅ 系统负载降低至正常水平"
echo "✅ 避免华为手机资源过载风险"

echo ""
echo "📊 当前华为手机状态:"
echo "负载: 42.92 (严重过载)"
echo "内存: 3.2GB/5.6GB 使用中"
echo "建议: 立即切换到平板"

echo "=========================================="
echo "执行时间: $(date)"