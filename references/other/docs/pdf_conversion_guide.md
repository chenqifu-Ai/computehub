# 📄 PDF转换指南 - 智企通规格书

## 🎯 问题说明

由于当前Android Termux环境的系统限制，无法直接安装PDF生成所需的编译依赖（Pillow库）。这是Termux环境的已知限制，不是权限问题。

## 🔧 解决方案

### 方案一：浏览器打印（推荐）
```bash
# 1. 下载附件中的HTML文件
# 2. 用Chrome/Firefox/Safari浏览器打开
# 3. 按 Ctrl+P (Windows) 或 Cmd+P (Mac)
# 4. 选择"另存为PDF"
# 5. 调整设置：
#    - 纸张大小: A4
#    - 边距: 无
#    - 背景图形: 勾选
# 6. 保存为PDF
```

### 方案二：在线转换工具
```markdown
🌐 推荐在线工具:

1. **html2pdf.com**
   - 网址: https://www.html2pdf.com
   - 特点: 免费，支持中文，保持样式

2. **Sejda HTML to PDF**  
   - 网址: https://www.sejda.com/html-to-pdf
   - 特点: 专业，高质量转换

3. **Smallpdf**
   - 网址: https://smallpdf.com/html-to-pdf
   - 特点: 知名品牌，界面友好

4. **CloudConvert**
   - 网址: https://cloudconvert.com/html-to-pdf
   - 特点: 支持多种格式转换
```

### 方案三：桌面软件
```markdown
💻 本地软件方案:

1. **Adobe Acrobat**
   - 专业PDF工具，支持HTML转PDF
   - 下载: https://acrobat.adobe.com

2. **WPS Office**
   - 打开HTML文件后另存为PDF
   - 下载: https://www.wps.com

3. **LibreOffice**
   - 免费开源办公软件
   - 下载: https://www.libreoffice.org
```

## 📋 详细步骤（浏览器打印）

### Chrome浏览器
1. **打开HTML文件**
   - 右键点击HTML文件 → 打开方式 → Chrome
   - 或拖动文件到Chrome窗口

2. **打印设置**
   - 按 `Ctrl+P` (Windows) 或 `Cmd+P` (Mac)
   - 目标打印机选择"另存为PDF"
   - 点击"更多设置"

3. **优化设置**
   ```
   纸张大小: A4
   边距: 无  
   选项: 勾选"背景图形"
   缩放: 100%
   ```

4. **保存**
   - 点击"保存"按钮
   - 选择保存位置和文件名

### Firefox浏览器
1. **打开文件**
   - 文件 → 打开文件 → 选择HTML文件

2. **打印设置**  
   - 按 `Ctrl+P` 或 菜单 → 打印
   - 选择"Microsoft Print to PDF"(Win)或"保存为PDF"(Mac)

3. **页面设置**
   ```
   缩放: 缩小以适应可打印区域
   选项: 打印背景(颜色和图像)
   ```

4. **导出**
   - 点击"打印" → 选择保存位置

## 🎨 保持样式技巧

### 确保完美转换
```markdown
✅ 背景颜色: 确保勾选"打印背景图形"
✅ 字体嵌入: 使用常见字体(宋体、黑体、微软雅黑)  
✅ 图片显示: 确保图片链接有效
✅ 响应式布局: 电脑上打开以获得最佳布局
```

### 常见问题解决
```markdown
❌ 背景丢失 → 勾选"背景图形"选项
❌ 排版错乱 → 使用Chrome浏览器
❌ 中文乱码 → 确保HTML指定UTF-8编码
❌ 图片缺失 → 检查图片路径
```

## 📊 质量检查

### 转换后检查清单
```markdown
1. ✅ 所有文字清晰可读
2. ✅ 图片和图表完整显示  
3. ✅ 颜色和样式保持原样
4. ✅ 页面布局整齐
5. ✅ 超链接正常工作(如需要)
6. ✅ 文件大小合理(通常1-5MB)
```

### 文件规格
```markdown
📏 页面大小: A4 (210×297mm)
🎨 颜色模式: RGB (屏幕显示)
📄 分辨率: 72-96 DPI (屏幕分辨率)
💾 文件格式: PDF 1.4+ (兼容性好)
```

## 🚀 批量处理

### 如果需要批量转换
```markdown
🔧 工具推荐:

1. **Pandoc** (命令行)
   ```bash
   # 安装pandoc
   sudo apt install pandoc
   
   # 转换单个文件
   pandoc input.html -o output.pdf
   
   # 批量转换
   for file in *.html; do
     pandoc "$file" -o "${file%.html}.pdf"
   done
   ```

2. **wkhtmltopdf**
   ```bash
   # 安装
   sudo apt install wkhtmltopdf
   
   # 使用
   wkhtmltopdf input.html output.pdf
   ```

3. **Python脚本**
   ```python
   # 需要安装weasyprint
   from weasyprint import HTML
   HTML('input.html').write_pdf('output.pdf')
   ```
```

## 💡 专业建议

### 最佳实践
```markdown
🎯 使用Chrome浏览器 - 转换效果最好
🎯 电脑上操作 - 屏幕大，便于预览  
🎯 先预览再保存 - 检查排版效果
🎯 保存高质量 - 选择较高分辨率
```

### 备用方案
```markdown
📧 如果需要，我可以为您：
1. 提供纯文本版本
2. 生成Word文档格式  
3. 创建Markdown版本
4. 发送到其他设备转换
```

## 📞 技术支持

### 遇到问题？
```markdown
🆘 常见问题支持:

1. **转换失败**
   - 尝试不同的浏览器
   - 使用在线转换工具
   
2. **样式丢失**  
   - 确保勾选"背景图形"
   - 使用Chrome浏览器
   
3. **中文乱码**
   - 检查HTML文件编码
   - 使用包含中文字体的系统
```

### 联系我们
```markdown
📞 智企科技技术支持
邮箱: support@zhiqi.ai
电话: 400-888-智企
```

---

## ✅ 总结

虽然当前环境无法直接生成PDF，但通过浏览器打印或在线工具可以轻松获得高质量的PDF文档。HTML文件已经精心设计，转换后将保持专业的视觉效果。

**推荐使用Chrome浏览器打印功能，这是最简单且效果最好的方法！**

---

*最后更新: 2026-04-16*
*文档版本: v1.1*