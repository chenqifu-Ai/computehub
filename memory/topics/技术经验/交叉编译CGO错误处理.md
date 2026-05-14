# 交叉编译 CGO 类型错误处理 (2026-05-13)

## 问题场景
在 Termux proot 环境下为 ComputeHub 进行交叉编译（linux/arm64）时，连续遇到两次相同的 CGO 类型错误：

```
# net
/data/data/com.termux/files/usr/lib/go/src/net/cgo_resnew.go:20:76:
cannot use _Ctype_socklen_t(len(b)) (value of uint32 type _Ctype_socklen_t)
as _Ctype_size_t value in argument to (_C2func_getnameinfo)
```

## 错误原因
**Termux proot 环境的内核/glibc 模拟层与 Go 的 cgo 网络解析不兼容。**

具体来说，Go 标准库 `net` 包在启用 CGO（默认）时会调用 C 库的 `getnameinfo` 函数。proot 环境下的 `_Ctype_socklen_t` 和 `_Ctype_size_t` 类型定义与 Go 的期望不一致（32-bit vs 64-bit），导致编译失败。

## 解决方案
**关掉 CGO 即可**：

```bash
CGO_ENABLED=0 go build ...
```

这是纯 Go 应用最常见的交叉编译方式，无需任何 C 依赖。

## 关键提示
1. **默认 CGO 在 Termux proot 下交叉编译必挂**，不是代码问题
2. **`CGO_ENABLED=0` 是标准做法**，不影响功能（Gateway/Worker/TUI 无 C 依赖）
3. 如果目标平台（如 140 的 Fedora）本身编译则没问题——只有交叉编译且中间环境是 proot 时才踩坑
4. `-ldflags="-s -w"` 可以同时去掉符号表和调试信息，减小二进制体积

## 经验教训
- **交叉编译第一条**：先关 CGO，能走通就不用开
- **遇到 CGO 网络相关错误** → 第一时间想到 `CGO_ENABLED=0`
- 如果确实需要 CGO（如 SQLite 驱动），需要设置正确的 `CC` 和 `CGO_CFLAGS`
- ComputeHub 三个组件（gateway/worker/tui）都无 C 依赖，`CGO_ENABLED=0` 永远够用
