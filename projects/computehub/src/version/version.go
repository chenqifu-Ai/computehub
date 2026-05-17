// Package version 提供 ComputeHub 统一的版本号管理
// 所有组件从此处读取版本号，确保一致
package version

// VERSION 是 ComputeHub 当前版本
// 修改规则: fix → +0.0.1, feature → +0.1.0, major → +1.0.0
const VERSION = "0.7.10"

// BUILD 是构建标识，编译时可通过 ldflags 注入
// go build -ldflags="-X github.com/computehub/opc/src/version.BUILD=$(date +%s)" ./cmd/gateway/
var BUILD = "dev"

// String 返回完整版本标识
func String() string {
	if BUILD != "dev" {
		return "v" + VERSION + "-" + BUILD
	}
	return "v" + VERSION
}

// Short 返回简短版本号
func Short() string {
	return VERSION
}
