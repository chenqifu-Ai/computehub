# Knowledge: Gallery 移动端截图 OCR 深度分析方法论
> Type: lesson
> Source: ecs-p2ph
> Confidence: 0.8
> TTL: 30 days
> Tags: ocr, gallery, 移动端, 截图分析, tesseract
> Timestamp: 2026-07-04T06:57:10+08:00

## Content

通过 Tesseract OCR 提取 Android 浏览器截图中的文字内容，结合结构化分析框架进行深度解读。关键步骤：1）定位图片文件；2）JPG 转 PNG；3）tesseract --psm 6 -l chi_sim+eng；4）多 PSM 模式对比；5）按状态栏/导航/内容/提示四区组织分析；6）结合文件名时间戳和上下文推断用户行为。深色模式需额外注意对比度，OCR 识别率可能下降。
