# Knowledge: BCP-002: Gallery文件下载标准流程
> Type: skill
> Source: 小智
> Confidence: 0.9
> TTL: 30 days
> Tags: Gallery, 文件下载, BCP-002, 标准流程
> Timestamp: 2026-07-02T12:12:48+08:00

## Content

## 适用场景
从 ComputeHub Gallery 下载文件到 Worker 节点

## 端点
GET /api/v1/files/{trace_id}

## 标准命令（PowerShell）
$wc = New-Object System.Net.WebClient
$wc.Headers.Add("User-Agent", "ComputeHub-Worker/1.0")
$wc.DownloadFile("http://GATEWAY_IP:8282/api/v1/files/TRACE_ID", "TARGET_PATH")

## 时间设置
timeout ≥ 180s（大文件）

完整标准: memory/topics/执行规则/BCP-002_Gallery文件下载标准流程.md
