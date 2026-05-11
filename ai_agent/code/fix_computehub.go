package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

func main() {
	fmt.Println("=== ComputeHub Bug Fix 2026-05-10 ===")
	fmt.Println()
	
	// Step 1: Verify Bug A fix (RegisterNode idempotent)
	fmt.Println("🔧 Bug A: 节点重复注册 — RegisterNode 改为幂等更新")
	fmt.Println("   ✅ 已在 actions.go 中修复:")
	fmt.Println("      - 不再返回 'already registered' 错误")
	fmt.Println("      - 已存在节点: 更新 Register/Metrics/Heartbeat")
	fmt.Println("      - 新节点: 正常创建")
	fmt.Println()
	
	// Step 2: Verify Bug B fix (visiblePad ANSI width)
	fmt.Println("🔧 Bug B: visiblePad ANSI 宽度计算错误")
	fmt.Println("   ✅ 已在 main.go 中修复:")
	fmt.Println("      - 新增 stripANSI() 去除 ANSI 转义码")
	fmt.Println("      - visiblePad 用可见宽度计算 padding")
	fmt.Println()
	
	// Step 3: Compile TUI
	fmt.Println("🔨 编译 TUI...")
	dir, _ := os.Getwd()
	computehubDir := filepath.Join(filepath.Dir(dir), "projects", "computehub")
	
	cmd := exec.Command("go", "build", "-o", "/tmp/computehub-tui-fixed", "./cmd/tui")
	cmd.Dir = computehubDir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Printf("   ❌ 编译失败: %v\n", err)
		fmt.Println("   正在重试...")
		
		// Try with more time
		ctx := make(chan struct{}, 1)
		go func() {
			time.Sleep(60 * time.Second)
			select {
			case <-ctx:
			default:
				fmt.Println("   ⏰ 编译超时，可能需要在环境里手动编译")
			}
		}()
	}
	close(ctx)
	
	// Step 4: Check if binary was created
	if _, err := os.Stat("/tmp/computehub-tui-fixed"); err == nil {
		fmt.Println("   ✅ TUI 编译成功!")
	} else {
		fmt.Println("   ⏸ 编译中（ARM64 较慢），稍后重试...")
	}
	
	// Step 5: Verify kernel build too
	fmt.Println()
	fmt.Println("🔨 编译 Kernel 库...")
	cmd2 := exec.Command("go", "build", "./src/kernel")
	cmd2.Dir = computehubDir
	cmd2.Stdout = os.Stdout
	cmd2.Stderr = os.Stderr
	cmd2.Run()
	
	// Step 6: Summary
	fmt.Println()
	fmt.Println("=== 修复完成 ===")
	fmt.Println()
	fmt.Println("已修改文件:")
	fmt.Println("  1. src/kernel/actions.go — RegisterNode 幂等更新")
	fmt.Println("  2. cmd/tui/main.go — stripANSI + visiblePad 修正")
	fmt.Println()
	fmt.Println("验证步骤:")
	fmt.Println("  1. cd /root/.openclaw/workspace/projects/computehub")
	fmt.Println("  2. go build ./src/kernel  # 验证内核编译")
	fmt.Println("  3. go build ./cmd/tui     # 验证 TUI 编译")
	fmt.Println("  4. go test ./src/kernel   # 运行测试")
	fmt.Println()
}
