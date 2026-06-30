// Package version 提供 ComputeHub 统一的版本号管理。
//
// 版本来源：
//   生产构建 — ldflags 注入 VERSION（由构建脚本从 git tag 读取并传入）
//   开发环境 — 源码中硬编码为 "dev"（go run / go build 不带 ldflags 时）
//
// 版本标准化流程:
//   VERSION=$(git describe --tags --abbrev=0 | sed 's/^v//')
//   go build -ldflags="-X github.com/computehub/opc/src/version.VERSION=${VERSION}"
//
// 不用 git tag 就别提交，也不用改这里的 VERSION。
// 包路径注意：go.mod module = github.com/computehub/opc，不是 computehub/computehub。
package version

import "fmt"

// VERSION 由 ldflags 在构建时注入，来源为 git tag（由构建脚本解析）。
// 默认 "dev" — 仅开发环境使用。
var VERSION = "1.3.48"

// BUILD 是 Unix 时间戳构建标识，由 ldflags 注入。
// 默认 "dev"。
var BUILD = "dev"

// Short 返回简洁版本号（仅数字，无前缀）。
func Short() string {
	return VERSION
}

// String 返回完整版本标识，格式: v{version}-{build}。
func String() string {
	if BUILD != "dev" {
		return "v" + VERSION + "-" + BUILD
	}
	return "v" + VERSION
}

// Full 返回格式化的版本信息字符串。
func Full() string {
	return fmt.Sprintf("ComputeHub v%s (build: %s)", VERSION, BUILD)
}