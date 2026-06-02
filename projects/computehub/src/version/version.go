// Package version 提供 ComputeHub 统一的版本号管理
// 所有组件从此处读取版本号，确保一致
package version

// VERSION 是 ComputeHub 当前版本
// 编译时由 build_all.sh 通过 ldflags 自动注入（来源: git tag / commit）
// 手动修改已无效，请通过 git tag 来管理版本号
var VERSION = "dev"

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
