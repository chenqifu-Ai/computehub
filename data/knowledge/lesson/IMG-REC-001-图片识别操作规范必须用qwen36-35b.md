# Knowledge: IMG-REC-001: 图片识别操作规范（必须用qwen3.6-35b）
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 图片识别, IMG-REC-001, qwen3.6-35b, base64, deepseek不支持
> Timestamp: 2026-07-02T12:23:15+08:00

## Content

## 核心规则
当前session默认模型（deepseek-v4-flash）不支持图片输入！
所有图片识别必须直接调用 qwen3.6-35b API

## 推荐方式
直接调本地 qwen3.6-35b API（http://127.0.0.1:8765/v1）
将图片编码为base64，通过image_url字段传入
API返回后从reasoning字段读取结果

## 简要流程
调用 qwen3.6-35b → base64传图 → 读 reasoning

## 性能
本地API（127.0.0.1:8765）响应1-3秒
远程API（58.23.129.98:8000）需5-10秒

## 配置
API地址: http://127.0.0.1:8765/v1/chat/completions
备用: http://10.111.223.227:8765/v1
模型: qwen3.6-35b
API Key: sk-78sadn09bjawde123e

完整标准: memory/topics/执行规则/图片识别操作规范.md
