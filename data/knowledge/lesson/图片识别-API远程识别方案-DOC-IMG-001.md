# Knowledge: 图片识别-API远程识别方案 (DOC-IMG-001)
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 图片识别, API, 远程识别, DOC-IMG-001, qwen3.6
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 适用场景
Termux/Android 环境无法本地跑图片识别，通过 API 远程传图识别

## 核心方法
API端点（OpenAI兼容）:
http://10.111.223.227:8765/v1/chat/completions
备用: http://192.168.2.54:8765/v1/chat/completions
模型: qwen3.6-35b
API Key: sk-78sadn09bjawde123e

## 请求格式
Python 代码:
1. 图片转为 Base64（data URI）
2. 通过 messages.content 传 image_url
3. 模型自动分析图片内容

## 方案对比
- API远程识别: 无依赖，准确率高 ✅ 推荐
- Base64编码传图: 简单但payload过大 ⚠️ 备选

完整文档: memory/topics/技术经验/图片识别-API 远程识别方案.md
