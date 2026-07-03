# Knowledge: COM-DEP-001: 编译部署标准流程
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 编译部署, COM-DEP-001, Go编译, 全平台, Gallery
> Timestamp: 2026-07-02T12:12:50+08:00

## Content

## 完整部署流程
1. 代码修改 → go vet / go build 验证
2. 全平台编译（5/5: linux-amd64/arm64, windows-amd64, darwin-amd64/arm64）
3. Gallery上传 binary
4. systemctl restart gateway
5. 节点自动升级（5min→30min间隔）
6. 验证：SHA256 + 节点在线

## 版本管理
- 版本号由 git tag 控制（scripts/get_version.sh）
- 编译时 ldflags 注入 VERSION

## 验证标准
- go build ./... 零错误
- 5/5 平台编译通过
- 节点 30s 内重新注册

完整标准: memory/topics/执行规则/COM-DEP-001_编译部署标准流程.md
