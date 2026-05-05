# Go 多二进制合并为一个的思考 (2026-05-04)

## 背景

ComputeHub 有 4 个二进制文件，各 ~8MB，总 32.5MB，`strip` 后总 22MB。
原因：Go 静态编译，每个二进制自带 Go Runtime + 标准库，这部分占 ~3-4MB。

| 文件 | strip前 | strip后 |
|------|---------|---------|
| computehub-gateway | 8.3MB | 5.7MB |
| compute-worker | 8.0MB | 5.4MB |
| compute-node | 8.0MB | 5.4MB |
| computehub-tui | 8.2MB | 5.5MB |
| **合计** | **32.5MB** | **22.0MB** |

## 合并方案（已实现但撤回）

做了 `cmd/computehub/main.go` + 4 个 refactored package，把 `main()` 改成 `Run()`，统一入口：

```bash
computehub gateway [flags]    # 相当于 computehub-gateway
computehub worker [flags]     # 相当于 compute-worker
computehub node [flags]       # 相当于 compute-node
computehub tui [flags]        # 相当于 computehub-tui
```

**预计效果**: 1 个文件 ~6MB（合并后 + strip），相比 22MB 省 70%

## 撤回原因

老大决定保留分开的二进制，因为：
- **独立部署** — 每个模块可以单独部署，gateway 跑在平板，worker 跑在 GPU 机器
- **解耦** — 不需要整个包都下载
- **清晰** — 每个二进制职责单一

## 合并的核心挑战

Go 不同包不能互相 import `package main`，需要抽成独立包名（如 `gatewaycmd`），然后把 `main()` 重构为 `Run(args []string) int`，内部所有 `os.Exit()` → `return`，`os.Args` → 参数传入。

## 以后合并的参考步骤

1. 创建 `cmd/computehub/main.go` 做统一入口
2. 把每个 `cmd/xxx/main.go` 复制为 `cmd/xxxcmd/xxx.go`，改 `package main` → `package xxxcmd`
3. 改 `func main()` → `func Run(args []string) int`
4. 全局替换 `os.Exit(1)` → `return 1`，`os.Exit(0)` → `return 0`
5. 检查 `os.Args` 引用，替换为接收的 `args` 参数
6. 编译测试 + strip 去调试符号

**下次合并前先评估**: 是否需要独立部署？是否在不同机器上？如果答案是"是"，就别合。
