# Knowledge: 交叉编译CGO类型错误处理 — Termux proot环境
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 交叉编译, CGO, Termux, proot, Go编译, 错误处理
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 问题
Termux proot环境下交叉编译（linux/arm64）Go代码时CGO网络解析错误：
cannot use _Ctype_socklen_t as _Ctype_size_t

## 根因
Termux proot的glibc模拟层与Go的cgo网络解析不兼容

## 解决方案
CGO_ENABLED=0 go build ...
纯Go应用交叉编译的标准做法

## 关键提示
- 默认CGO在Termux proot下交叉编译必挂
- ComputeHub三个组件（gateway/worker/tui）都无C依赖
- CGO_ENABLED=0 永远够用，不影响功能
- ldflags="-s -w" 可减小二进制体积

完整文档: memory/topics/技术经验/交叉编译CGO错误处理.md
