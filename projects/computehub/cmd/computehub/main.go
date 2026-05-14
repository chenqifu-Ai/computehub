// ComputeHub — All-in-One Binary
//
// Subcommands:
//   computehub gateway [--port N]   → 启动 Gateway 服务
//   computehub worker  [--gw ...]   → 启动 Worker Agent
//   computehub tui     [--gw ...]   → 启动 TUI 终端
//
// 每个子命令的详细参数见对应的 help 输出。

package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/computehub/opc/src/gatewaycmd"
	"github.com/computehub/opc/src/tuicmd"
	"github.com/computehub/opc/src/version"
	"github.com/computehub/opc/src/workercmd"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	subcmd := os.Args[1]
	subArgs := os.Args[2:]

	switch strings.ToLower(subcmd) {
	case "gateway", "gw", "g":
		gatewaycmd.Run(subArgs)

	case "worker", "w":
		workercmd.Run(subArgs)

	case "tui":
		tuicmd.Run(subArgs)

	case "version", "--version", "-v":
		fmt.Printf("ComputeHub v%s\n", version.Short())

	case "help", "--help", "-h":
		printUsage()

	default:
		fmt.Printf("❌ 未知子命令: %s\n\n", subcmd)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("ComputeHub — 算力调度平台")
	fmt.Printf("版本: %s\n\n", version.Short())
	fmt.Println("用法:")
	fmt.Println("  computehub gateway [--port N]          启动 Gateway 服务")
	fmt.Println("  computehub worker  [--gw URL] [--flags] 启动 Worker 节点")
	fmt.Println("  computehub tui     [--gw URL]           启动终端管理界面")
	fmt.Println("  computehub version                     显示版本号")
	fmt.Println("  computehub help                        显示帮助")
	fmt.Println()
	fmt.Println("各子命令详情:")
	fmt.Println("  computehub gateway --help    Gateway 配置参数")
	fmt.Println("  computehub worker  --help    Worker 配置参数")
	fmt.Println("  computehub tui               TUI 交互式界面（支持 --gw 指定 Gateway）")
}
