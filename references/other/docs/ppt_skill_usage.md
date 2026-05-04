# 🎨 PPT制作技能使用指南

## 📋 技能概述
我最近创建了专业的PPT制作技能，支持多种格式转换和美化设计。

## 🏗️ 技能位置
```
/root/.openclaw/workspace/skills/ppt-maker/
├── 📄 SKILL.md          # 完整使用文档
├── 🐍 ppt_maker.py      # 主程序
├── 📁 templates/        # 模板文件
├── 📁 examples/        # 示例文件
└── 📁 output/          # 输出目录
```

## 🚀 使用方法

### 基础用法
```bash
# Markdown转PPT
python ppt_maker.py convert input.md output.pptx

# 使用指定模板
python ppt_maker.py convert input.md output.pptx --template business

# 批量转换
python ppt_maker.py batch convert ./docs/ ./output/ --format pptx
```

### 高级选项
```bash
# 自定义主题颜色
python ppt_maker.py convert input.md output.pptx --theme-color "#007acc"

# 添加公司Logo
python ppt_maker.py convert input.md output.pptx --logo company_logo.png

# 设置动画效果
python ppt_maker.py convert input.md output.pptx --animation fade
```

## 🎨 模板系统

### 内置模板
- `business` - 商业风格 (蓝色主题)
- `creative` - 创意风格 (红色主题)
- `technical` - 技术风格 (灰色主题)
- `minimal` - 简约风格 (黑白主题)

### 自定义模板
在 `templates/` 目录放置自定义模板：
- template.xml - 布局定义
- styles.css - 样式定义
- images/ - 背景图片

## 📊 支持格式

### 输入格式
- Markdown (.md)
- 纯文本 (.txt)
- JSON 数据结构
- Python字典格式

### 输出格式
- PowerPoint (.pptx)
- PDF 演示文稿
- HTML 在线演示
- 图片幻灯片 (.png)

## 💡 示例代码

### Python API使用
```python
from ppt_maker import PresentationBuilder

# 创建演示文稿
builder = PresentationBuilder(template="business")

# 添加幻灯片
builder.add_title_slide("项目计划", "2026年度发展规划")
builder.add_content_slide("市场分析", "• 市场规模\\n• 竞争分析\\n• 机会识别")

# 保存文件
builder.save("project_plan.pptx")
```

### 批量处理
```python
from ppt_maker import BatchConverter

# 批量转换Markdown文件
converter = BatchConverter(input_dir="./markdown/", output_dir="./ppt/")
converter.convert_all(format="pptx", template="technical")
```

## ⚙️ 安装依赖
```bash
pip install python-pptx reportlab pillow
# 或者
pip install -r requirements.txt
```

## 🎯 功能特性

### 核心功能
- ✅ Markdown自动转换PPT
- ✅ 多种模板风格选择
- ✅ 批量处理支持
- ✅ 自定义样式配置
- ✅ 高级排版功能

### 设计特色
- 🎨 智能排版和美化
- 📱 响应式设计
- 🔄 批量处理能力
- 💼 商业级输出质量

## 📝 文件结构说明

### Markdown格式要求
```markdown
# 幻灯片标题

## 子标题
- 项目符号1
- 项目符号2
- 项目符号3

### 小标题
普通文本内容
```

### 转换规则
- `# 标题` → 幻灯片标题
- `## 子标题` → 幻灯片子标题
- `- 项目符号` → 项目符号列表
- 普通文本 → 正文内容

## 🔧 错误处理

### 常见问题
```python
try:
    builder = PresentationBuilder()
    builder.add_slide("内容")
    builder.save("output.pptx")
except FileNotFoundError:
    print("模板文件不存在")
except PermissionError:
    print("没有写入权限")
except Exception as e:
    print(f"生成失败: {e}")
```

## 📞 技术支持

### 获取帮助
```bash
# 查看帮助文档
python ppt_maker.py --help

# 查看模板列表
python ppt_maker.py templates list

# 检查系统状态
python ppt_maker.py status
```

### 问题排查
1. 确保依赖包已安装
2. 检查文件读写权限
3. 验证Markdown格式正确
4. 确认模板文件存在

---
**版本**: 1.0.0
**最后更新**: 2026-04-08
**维护者**: 小智AI助手

*此技能持续开发中，欢迎反馈和改进建议！*