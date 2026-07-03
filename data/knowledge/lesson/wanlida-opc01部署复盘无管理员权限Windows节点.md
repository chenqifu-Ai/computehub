# Knowledge: wanlida-opc01部署复盘（无管理员权限Windows节点）
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Windows, 无权限安装, wanlida, 部署复盘, GPU节点, RTX4060
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 节点信息
Windows / amd64 / 移动宽带 / 10× RTX 4060 / admin用户（无管理员权限）

## 部署时间线（~5小时）
- Python 3.12.9: 已有，无需安装 ✅
- Go: msiexec 失败（无管理员权限）→ 交叉编译11个exe ✅
- Node.js v18.20.8: nvm-windows 安装 ✅
- Git 2.54.0: 直接从阿里云镜像下载 ✅

## 关键教训
1. 无管理员权限时，msiexec 不可用，必须用 portable 版
2. 网络不稳定（移动宽带到阿里云），大文件用 Python urllib + Gallery
3. 部署前先探测已有环境，避免重复安装
4. 交叉编译 Go 工具链：CGO_ENABLED=0 + 指定 GOOS=windows GOARCH=amd64

完整文档: memory/topics/项目/wanlida-opc01部署复盘_2026-06-12.md
