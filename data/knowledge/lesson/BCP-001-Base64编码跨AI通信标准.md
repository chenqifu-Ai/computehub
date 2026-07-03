# Knowledge: BCP-001: Base64编码跨AI通信标准
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Base64, 跨AI通信, BCP-001, PowerShell, 编码标准
> Timestamp: 2026-07-02T12:12:48+08:00

## Content

## 核心原则
AI↔AI通信时用Base64编码传输脚本/代码，避开JSON+Shell多层引号转义

## PowerShell 用法（关键！）
必须用 UTF-16LE 编码，不能用 UTF-8
powershell -EncodedCommand $(echo '脚本内容' | iconv -t UTF-16LE | base64 -w0)

## 大脚本处理
- ≤8KB: -EncodedCommand 传
- >8KB: WriteAllBytes 写文件
- 超大文件: Gallery上传 + WebClient.DownloadFile（timeout ≥ 180s）

## Linux 侧
echo <b64> | base64 -d > file && python3 file

完整标准: memory/topics/执行规则/BCP-001_Base64编码跨AI通信标准.md
