package version

import "fmt"

// VERSION 由 ldflags 在构建时注入，来源为 git tag（由构建脚本解析）。
// 默认 "dev" — 仅开发环境使用。
var VERSION = "1.4.3"

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
