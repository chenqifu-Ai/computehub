# PDF转Word工具

一个简单高效的PDF转Word文档工具，支持命令行和Web界面。

## 功能特点

- ✅ 文本提取：提取PDF中的文本内容
- ✅ 批量转换：支持文件夹批量处理
- ✅ Web界面：可视化操作界面
- ✅ 本地处理：数据不上传，保护隐私
- ✅ 零依赖：使用Python标准库

## 安装

```bash
# 克隆或下载项目
git clone https://github.com/your-repo/pdf-to-word.git
cd pdf-to-word

# 无需安装额外依赖，Python标准库即可运行
```

## 使用方法

### Web界面（推荐）

```bash
# 启动Web服务
python3 pdf2word.py --web

# 或指定端口
python3 pdf2word.py --web --port 8080
```

然后访问 http://localhost:5000

### 命令行

```bash
# 转换单个文件
python3 pdf2word.py input.pdf

# 指定输出路径
python3 pdf2word.py input.pdf -o output.docx

# 批量转换
python3 pdf2word.py /path/to/pdf/folder -o /path/to/output
```

## API接口

### 检查状态
```
GET /api/status
返回: {"status": "ok", "version": "1.0.0"}
```

### 上传转换
```
POST /api/convert
Content-Type: multipart/form-data

参数:
- file: PDF文件

返回:
{
  "success": true,
  "filename": "output.docx",
  "pages": 10,
  "text_length": 5000,
  "download_url": "data:application/..."
}
```

## 项目结构

```
pdf-to-word/
├── pdf2word.py          # 主程序
├── README.md            # 说明文档
├── start.sh             # 启动脚本
└── examples/            # 示例文件
    ├── sample.pdf
    └── sample.docx
```

## 注意事项

1. **文本提取限制**：简单PDF解析器适用于文本型PDF，扫描版PDF可能无法提取文字
2. **复杂格式**：表格、图片等复杂格式可能无法完美保留
3. **文件大小**：建议单文件不超过50MB

## 常见问题

**Q: 转换后是空白？**
A: 可能是扫描版PDF，请使用专业OCR工具

**Q: 中文显示乱码？**
A: 确保PDF使用标准字体编码

**Q: 如何保留图片？**
A: 当前版本不支持图片提取，建议使用专业工具

## 技术栈

- Python 3.8+
- 纯标准库实现
- 无需第三方依赖

## License

MIT License