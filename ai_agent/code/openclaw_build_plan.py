#!/usr/bin/env python3
"""
OpenClaw编译计划分析
先分析项目结构，制定详细编译方案
"""

import subprocess
import sys
from datetime import datetime

def run_ssh_command(cmd, description=""):
    """执行SSH命令并返回结果"""
    print(f"🔍 {description}")
    print(f"  命令: {cmd}")
    
    try:
        full_cmd = f"sshpass -p 123 ssh -p 8022 u0_a46@192.168.1.9 '{cmd}'"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"  返回码: {result.returncode}")
        if result.stdout:
            print(f"  输出: {result.stdout.strip()}")
        if result.stderr:
            print(f"  错误: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("  ⏰ 命令执行超时")
        return False, "", "Timeout"
    except Exception as e:
        print(f"  ❌ 执行异常: {e}")
        return False, "", str(e)

def analyze_project_structure():
    """分析项目结构"""
    print("🤖 OpenClaw项目结构分析")
    print("=" * 50)
    
    # 1. 检查项目基本信息
    print("\n1️⃣ 项目基本信息")
    run_ssh_command(
        "cd /data/data/com.termux/files/home/openclaw && pwd && ls -la | grep -E '(package.json|pnpm-lock)'",
        "检查项目根目录"
    )
    
    # 2. 检查构建配置
    print("\n2️⃣ 构建配置分析")
    run_ssh_command(
        "cd /data/data/com.termux/files/home/openclaw && grep -A 20 'scripts' package.json",
        "查看构建脚本配置"
    )
    
    # 3. 检查TypeScript配置
    print("\n3️⃣ TypeScript配置")
    run_ssh_command(
        "cd /data/data/com.termux/files/home/openclaw && ls -la tsconfig.json && head -10 tsconfig.json",
        "检查TypeScript配置"
    )
    
    # 4. 检查现有构建输出
    print("\n4️⃣ 现有构建输出")
    run_ssh_command(
        "cd /data/data/com.termux/files/home/openclaw && ls -la dist/ 2>/dev/null || echo 'dist目录不存在'",
        "检查dist目录"
    )
    
    # 5. 检查依赖状态
    print("\n5️⃣ 依赖状态检查")
    run_ssh_command(
        "cd /data/data/com.termux/files/home/openclaw && ls -la node_modules/ | head -5",
        "检查node_modules"
    )

def create_build_plan():
    """创建详细的编译计划"""
    print("\n🎯 编译计划制定")
    print("=" * 50)
    
    plan = """
# 📋 OpenClaw编译执行计划

## 🎯 目标
将OpenClaw源代码编译为可执行文件，使用2026.3.13版本

## 📊 环境分析
- **平台**: Android Termux
- **Node.js**: v25.8.2
- **包管理**: pnpm 10.23.0
- **项目类型**: TypeScript Monorepo

## 🔧 构建步骤

### 阶段一：环境准备
1. ✅ 检查Node.js和pnpm版本
2. ✅ 确认项目目录结构
3. 🔲 清理旧的构建输出 (如有)

### 阶段二：依赖安装  
1. 🔲 执行 `pnpm install` 安装所有依赖
2. 🔲 验证依赖安装完整性
3. 🔲 检查依赖冲突

### 阶段三：TypeScript编译
1. 🔲 执行 `pnpm run build` 主构建命令
2. 🔲 包含的步骤:
   - TypeScript编译 (tsc)
   - UI组件打包
   - 资源文件复制
   - 元数据生成

### 阶段四：输出验证
1. 🔲 检查dist目录结构
2. 🔲 验证入口文件
3. 🔲 测试基本功能

### 阶段五：部署准备
1. 🔲 创建可执行脚本
2. 🔲 设置执行权限
3. 🔲 验证版本信息

## ⚠️ 风险预估
1. **内存不足**: Android设备内存限制
2. **编译时间**: 大型项目可能需要较长时间
3. **网络依赖**: 需要下载大量npm包
4. **平台兼容性**: Android环境特殊要求

## 🚀 优化策略
1. 分阶段执行，避免内存溢出
2. 使用pnpm的缓存机制
3. 监控构建过程，及时处理错误
4. 准备回滚方案

## 📝 验收标准
1. ✅ dist目录包含完整编译输出
2. ✅ 可执行文件能正常运行
3. ✅ 版本信息显示正确
4. ✅ 基本命令功能正常
"""
    
    print(plan)
    
    # 保存计划
    plan_file = f"/root/.openclaw/workspace/ai_agent/results/openclaw_build_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(plan_file, "w") as f:
        f.write(plan)
    
    print(f"✅ 编译计划已保存到: {plan_file}")
    return True

def main():
    print("🤖 开始OpenClaw编译计划分析")
    print("=" * 50)
    
    # 先分析后计划
    analyze_project_structure()
    create_build_plan()
    
    print("\n✅ 计划制定完成！")
    print("\n📋 下一步行动:")
    print("1. 审核编译计划")
    print("2. 确认资源需求") 
    print("3. 按计划分步执行")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)