#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 OpenClaw装机技能演示脚本
展示装机技能的完整实现步骤
"""

import subprocess
import sys
import time
from typing import Dict, List, Optional

class DeploymentDemo:
    """装机技能演示类"""
    
    def __init__(self):
        self.steps = []
        self.results = {}
        
    def log_step(self, step_name: str, description: str):
        """记录执行步骤"""
        print(f"\n🔧 [{step_name}] {description}")
        print("-" * 50)
        self.steps.append({
            'name': step_name,
            'description': description,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def execute_command(self, cmd: str, check: bool = True) -> Dict:
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def demo_device_detection(self):
        """演示设备检测步骤"""
        self.log_step("设备检测", "检查本地设备信息和资源状态")
        
        # 检查系统信息
        commands = [
            "uname -a",
            "free -h",
            "df -h /data",
            "node --version",
            "npm --version"
        ]
        
        for cmd in commands:
            print(f"📊 执行: {cmd}")
            result = self.execute_command(cmd)
            if result['success']:
                print(f"✅ 成功: {result['stdout'].strip()}")
            else:
                print(f"❌ 失败: {result.get('error', 'Unknown error')}")
    
    def demo_openclaw_installation(self):
        """演示OpenClaw安装步骤"""
        self.log_step("OpenClaw安装", "检查当前安装状态和版本")
        
        # 检查OpenClaw安装状态
        check_cmds = [
            "which openclaw",
            "openclaw --version 2>/dev/null || echo '未安装'",
            "npm list -g | grep openclaw || echo '未找到OpenClaw包'"
        ]
        
        for cmd in check_cmds:
            result = self.execute_command(cmd, check=False)
            output = result['stdout'].strip() if result['success'] else result.get('error', '')
            print(f"📦 {cmd.split()[0]}: {output}")
    
    def demo_config_sync(self):
        """演示配置同步步骤"""
        self.log_step("配置同步", "展示配置文件和目录结构")
        
        # 检查配置目录
        config_path = "~/.openclaw"
        check_cmds = [
            f"ls -la {config_path} 2>/dev/null || echo '配置目录不存在'",
            f"find {config_path} -name '*.json' -o -name '*.md' | head -10 2>/dev/null || true",
            f"du -sh {config_path} 2>/dev/null || echo '无法计算大小'"
        ]
        
        for cmd in check_cmds:
            result = self.execute_command(cmd, check=False)
            if result['success'] and result['stdout'].strip():
                print(f"📁 {result['stdout'].strip()}")
    
    def demo_service_management(self):
        """演示服务管理步骤"""
        self.log_step("服务管理", "检查Gateway服务状态")
        
        # 检查服务状态
        service_cmds = [
            "ps aux | grep openclaw | grep -v grep || echo '无OpenClaw进程'",
            "netstat -tln | grep ':18789' || echo '18789端口未监听'",
            "curl -s http://127.0.0.1:18789/health 2>/dev/null || echo '健康检查失败'"
        ]
        
        for cmd in service_cmds:
            result = self.execute_command(cmd, check=False)
            output = result['stdout'].strip() if result['stdout'] else result.get('stderr', '')
            if output:
                print(f"🔄 {output}")
    
    def generate_deployment_script(self):
        """生成部署脚本示例"""
        self.log_step("脚本生成", "创建自动化部署脚本")
        
        script_content = '''#!/bin/bash
# OpenClaw自动化部署脚本示例

# 配置参数
TARGET_HOST="192.168.1.19"
TARGET_PORT="8022"
TARGET_USER="u0_a207"
TARGET_PASS="123"
DEPLOY_PORT="18789"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 设备检测
device_check() {
    log_info "检测目标设备..."
    sshpass -p "$TARGET_PASS" ssh -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "uname -a && free -h"
}

# 2. OpenClaw安装
install_openclaw() {
    log_info "安装OpenClaw..."
    sshpass -p "$TARGET_PASS" ssh -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "npm install -g openclaw@latest"
}

# 3. 配置同步
sync_config() {
    log_info "同步配置..."
    tar -czf - -C ~/.openclaw . | \
    sshpass -p "$TARGET_PASS" ssh -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "tar -xzf - -C ~/.openclaw"
}

# 4. 启动服务
start_service() {
    log_info "启动服务..."
    sshpass -p "$TARGET_PASS" ssh -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw gateway --port $DEPLOY_PORT &"
}

# 主流程
main() {
    device_check
    install_openclaw
    sync_config
    start_service
    log_info "部署完成!"
}

main "$@"
'''
        
        print("📜 生成的部署脚本:")
        print("=" * 50)
        print(script_content)
        print("=" * 50)
        
        # 保存脚本文件
        with open('/tmp/deploy_demo.sh', 'w') as f:
            f.write(script_content)
        
        print("💾 脚本已保存到: /tmp/deploy_demo.sh")
    
    def show_usage_examples(self):
        """显示使用示例"""
        self.log_step("使用示例", "装机技能的实际应用场景")
        
        examples = [
            "🔹 单设备部署: ./deploy.sh 192.168.1.19 8022 u0_a207 123",
            "🔹 自定义端口: ./deploy.sh 192.168.1.19 8022 u0_a207 123 28888",
            "🔹 批量部署: ./batch_deploy.sh",
            "🔹 仅同步配置: ./deploy.sh --sync-only 192.168.1.19",
            "🔹 版本指定: ./deploy.sh --version openclaw@beta 192.168.1.19"
        ]
        
        for example in examples:
            print(example)
    
    def run_demo(self):
        """运行完整演示"""
        print("🚀 OpenClaw装机技能演示")
        print("=" * 60)
        
        try:
            self.demo_device_detection()
            self.demo_openclaw_installation()
            self.demo_config_sync()
            self.demo_service_management()
            self.generate_deployment_script()
            self.show_usage_examples()
            
            print(f"\n🎯 演示完成! 共执行 {len(self.steps)} 个步骤")
            print("✅ 装机技能已就绪，可自动化完成多设备部署")
            
        except Exception as e:
            print(f"❌ 演示出错: {e}")
            return False
        
        return True

# 执行演示
if __name__ == "__main__":
    demo = DeploymentDemo()
    success = demo.run_demo()
    sys.exit(0 if success else 1)