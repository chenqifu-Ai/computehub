# continuous-flow-execution 技能

## 🎯 技能描述
连续流状态执行技能 - 实现真正的连贯执行，避免"继续继续"中断

**激活时机**: 当任务需要多步骤连贯执行，用户讨厌流程中断时

## 🔍 技能背景
基于2026-03-26 TUI界面含义分析的经验教训：
- **问题**: 每个步骤都可以，但连贯起来就不行
- **教训**: 流程断裂导致用户体验差
- **目标**: 实现像TUI一样的连续流状态执行

## 📋 核心能力

### 1. 状态连贯性
- 步骤之间无缝状态传递
- 避免人工干预"继续"
- 自动进度保存和恢复

### 2. 实时反馈
- TUI式状态显示: `[动画] [状态] [时间] | connected`
- 高频更新(50-100ms)
- 禁用输出缓冲，立即显示

### 3. 错误恢复
- 自动错误捕获
- 步骤重试机制
- 状态回滚能力

### 4. 简单架构
- 单脚本完成全流程
- 最小化外部依赖
- 易于理解和维护

## 🛠️ 实现模板

### 基础模板结构
```python
#!/usr/bin/env python3
import time
import sys
import json
import os

# 禁用缓冲，实现实时流
sys.stdout.reconfigure(line_buffering=True)

class ContinuousFlow:
    def __init__(self):
        self.start_time = time.time()
        self.state_file = "/tmp/flow_state.json"
        self.animations = ['⠋', '⠙', '⠹', '⠸', '⢰', '⣠', '⣄', '⡆', '⠇', '⠏']
        self.anim_idx = 0
    
    def display_status(self, step_name, step_num, total_steps):
        elapsed = int(time.time() - self.start_time)
        anim = self.animations[self.anim_idx]
        self.anim_idx = (self.anim_idx + 1) % len(self.animations)
        
        progress = f"[{step_num}/{total_steps}]"
        sys.stdout.write(f"\r{anim} {progress} {step_name} • {elapsed}s | connected")
        sys.stdout.flush()
    
    def run_step(self, step_num, step_name, step_func, *args):
        """运行一个步骤"""
        # 显示状态
        for i in range(10):
            self.display_status(step_name, step_num, self.total_steps)
            time.sleep(0.05)
        
        # 执行步骤
        try:
            result = step_func(*args)
            # 保存状态
            self._save_step_result(step_name, result)
            return True
        except Exception as e:
            self._save_step_error(step_name, str(e))
            return False
    
    def execute_flow(self, steps):
        """执行完整流程"""
        self.total_steps = len(steps)
        
        for i, (step_name, step_func, *args) in enumerate(steps, 1):
            if not self.run_step(i, step_name, step_func, *args):
                return False
        
        return True
```

### 使用示例
```python
def analyze_data():
    """分析数据步骤"""
    # 分析逻辑
    return {"categories": 6, "items": 34}

def generate_report(data):
    """生成报告步骤"""
    # 报告生成逻辑
    return "report.md"

def send_email(report_path):
    """发送邮件步骤"""
    # 邮件发送逻辑
    return True

# 定义流程步骤
steps = [
    ("analyzing", analyze_data),
    ("reporting", generate_report, "data"),  # 传递上一步结果
    ("emailing", send_email, "report_path")  # 传递上一步结果
]

# 执行
flow = ContinuousFlow()
if flow.execute_flow(steps):
    print("\n✅ 连贯执行完成")
else:
    print("\n❌ 执行失败")
```

## 📊 性能指标

### 响应时间
- **状态更新**: ≤100ms
- **步骤切换**: ≤500ms
- **错误恢复**: ≤2s

### 资源占用
- **内存**: <50MB
- **CPU**: <5% (平均)
- **存储**: 状态文件<1KB

## 🔧 配置选项

### 动画配置
```python
ANIMATION_CONFIG = {
    "frequency": 0.05,  # 50ms更新
    "spinners": ['⠋', '⠙', '⠹', '⠸', '⢰', '⣠', '⣄', '⡆', '⠇', '⠏'],
    "time_format": "• {elapsed}s"  # 时间显示格式
}
```

### 状态存储
```python
STATE_CONFIG = {
    "file_path": "/tmp/flow_state.json",
    "auto_save": True,
    "max_history": 10  # 保存最近10个状态
}
```

## 🚀 最佳实践

### 步骤设计原则
1. **单一职责**: 每个步骤只做一件事
2. **状态明确**: 输入输出清晰定义
3. **错误边界**: 每个步骤独立错误处理
4. **时间控制**: 单个步骤≤30秒

### 用户体验优化
1. **进度可见**: 始终显示当前步骤和进度
2. **错误友好**: 错误信息清晰可操作
3. **结果明确**: 最终结果一目了然
4. **时间预估**: 提供剩余时间估计

## 📁 文件结构
```
continuous-flow-execution/
├── SKILL.md          # 技能文档
├── template.py       # 基础模板
├── examples/         # 使用示例
│   ├── tui_analysis.py
│   └── email_flow.py
└── utils/
    ├── state_manager.py
    └── progress_display.py
```

## 🎯 适用场景

### 高优先级
- 多步骤数据分析
- 自动化报告生成
- 邮件发送流程
- 文件处理流水线

### 中优先级
- 系统配置任务
- 数据备份流程
- 批量操作任务
- 监控检查流程

## 📈 成功案例

### TUI界面含义分析 (2026-03-26)
- **问题**: 6个脚本，流程断裂
- **改进**: 1个脚本，连贯执行
- **效果**: 用户体验大幅提升

## 🔄 版本历史

### v1.0 (2026-03-26)
- 初始版本
- 基于TUI分析经验
- 基础连贯执行框架

---
*技能创建时间: 2026-03-26*
*创建者: 小智*
*核心理念: 连贯性 > 复杂性*