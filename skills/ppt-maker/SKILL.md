# 🎨 PPT制作技能

## 技能描述
专业的PPT演示文稿制作技能，支持多种格式输出和美化设计。

## 功能特性
- 📊 Markdown转PPT自动转换
- 🎨 智能排版和设计美化  
- 📝 多种模板风格选择
- 🔄 批量处理和格式转换
- 💼 商业演示文稿专业制作

## 支持格式
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

## 使用方法

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

## 模板系统

### 内置模板
- `business` - 商业风格
- `creative` - 创意风格  
- `academic` - 学术风格
- `minimal` - 简约风格
- `technical` - 技术风格

### 自定义模板
在 `templates/` 目录放置自定义模板文件：
- template.xml - 布局定义
- styles.css - 样式定义
- images/ - 背景图片

## 配置选项

### 主题配置
```json
{
  "title": "演示文稿标题",
  "author": "作者名称", 
  "company": "公司名称",
  "theme": "business",
  "colors": {
    "primary": "#007acc",
    "secondary": "#ff6b6b",
    "background": "#ffffff"
  },
  "fonts": {
    "title": "Arial",
    "body": "Calibri"
  }
}
```

### 幻灯片设置
```json
{
  "slide_width": 10,
  "slide_height": 7.5,
  "margin": 0.5,
  "transition": "fade",
  "duration": 3000
}
```

## 文件结构
```
ppt-maker/
├── 📁 templates/          # 模板文件
├── 📁 examples/           # 示例文件  
├── 📁 output/             # 输出目录
├── 📄 ppt_maker.py        # 主程序
├── 📄 config.json         # 配置文件
└── 📄 requirements.txt    # 依赖包
```

## 安装依赖
```bash
pip install python-pptx reportlab pillow
# 或者
pip install -r requirements.txt
```

## 示例代码

### Markdown转PPT
```python
from ppt_maker import PresentationBuilder

# 创建演示文稿
builder = PresentationBuilder(template="business")

# 添加幻灯片
builder.add_title_slide("项目计划", "2026年度发展规划")
builder.add_content_slide("市场分析", "• 市场规模\n• 竞争分析\n• 机会识别")
builder.add_image_slide("产品展示", "product_image.png")

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

## 高级功能

### 数据驱动生成
```python
# 从JSON数据生成PPT
import json

with open('data.json') as f:
    data = json.load(f)
    
builder = PresentationBuilder()
builder.generate_from_data(data)
builder.save("data_report.pptx")
```

### 自动化报告
```python
# 自动生成周报PPT
from datetime import datetime

def generate_weekly_report():
    week_num = datetime.now().isocalendar()[1]
    builder = PresentationBuilder(template="business")
    
    builder.add_title_slide(f"周报 - 第{week_num}周", datetime.now().strftime("%Y年%m月%d日"))
    # 添加各模块内容...
    
    filename = f"weekly_report_week_{week_num}.pptx"
    builder.save(filename)
    return filename
```

## 错误处理

### 常见错误
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

## 性能优化

### 内存管理
```python
# 分批处理大型文档
for chunk in read_large_markdown("large_doc.md", chunk_size=10):
    builder.add_content_slide(f"部分 {chunk['number']}", chunk['content'])
    
    # 每10页保存一次避免内存溢出
    if builder.slide_count % 10 == 0:
        intermediate_file = f"temp_{builder.slide_count}.pptx"
        builder.save(intermediate_file)
```

## 扩展开发

### 自定义插件
```python
# 开发自定义模板插件
class CustomTemplate(BaseTemplate):
    def __init__(self):
        super().__init__()
        self.name = "custom"
        self.colors = {"primary": "#2ecc71"}
        
    def apply_layout(self, slide, content):
        # 自定义布局逻辑
        pass

# 注册自定义模板
PresentationBuilder.register_template("custom", CustomTemplate)
```

---
**版本**: 1.0.0
**最后更新**: 2026-04-08
**维护者**: 小智AI助手