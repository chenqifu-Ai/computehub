# Knowledge: OCR-PDF转Word-邮件发送标准流程（DOC-STD-001）
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: OCR, PDF处理, Python, 邮件发送, 文档处理, 标准流程, DOC-STD-001
> Timestamp: 2026-07-02T12:07:29+08:00

## Content

## 适用场景
PDF扫描件（法律合同/股东协议等）→ OCR识别 → 转Word文档 → 附件邮件

## 全链路流程
1. PDF转PNG（pdftoppm -png -r 300）
2. Tesseract OCR（tesseract -l chi_sim+eng --psm 3）
3. 合并OCR文本
4. 文本转Word文档（python-docx）
5. 附件邮件发送（send_email.py）

## 实战案例
霞浦股东协议：49页扫描件PDF（8.9MB）→ OCR识别56KB文本 → Word 55KB → 发送至邮箱
全链路约3分钟

## 关键要点
- 分辨率选300dpi性价比最高，200dpi错字多，400dpi耗时翻倍
- 法律文书用 chi_sim+eng 语言包，chi_sim放前面
- python-docx必须设置东亚字体（w:eastAsia），否则Word中文变方块
- send_email.py 内置MIME类型映射，支持附件中文文件名RFC 2231编码
- QQ邮箱优先 → 163邮箱自动备选

## 依赖安装
apt install poppler-utils tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
pip install python-docx

## 经验教训
- 倾斜图片先 ImageMagick deskew 预处理
- pdftoppm 比 convert 快5-10倍
- send_email.py 附件路径必须绝对路径

完整标准文档：memory/shared/knowledge/文档处理/OCR-PDF转Word-邮件发送标准流程.md
