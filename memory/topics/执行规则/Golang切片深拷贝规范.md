# STD-GO-001 | Go 切片深拷贝规范

> **标准编号**: STD-GO-001
> **创建日期**: 2026-05-02
> **来源错误**: E-003 | Go深拷贝 make+append 翻倍
> **适用范围**: ComputeHub 项目及所有 Go 项目

---

## 问题

```go
// ❌ 错误写法：make + append 导致翻倍
copy.Nodes = make([]NodeVisual, len(rd.Nodes)) // 创建 n 个零值
copy.Nodes = append(copy.Nodes, rd.Nodes...)    // 再追加 n 个 → 长度 n*2
```

`make([]T, n)` 已经创建了 n 个零值元素，再 `append` 又会追加 n 个，结果是 2n。

## 正确写法

### 方式一：append 一行（推荐）
```go
copy.Nodes = append([]NodeVisual{}, src.Nodes...)
```

### 方式二：copy（效率更高，但需要先 make）
```go
copy.Nodes = make([]NodeVisual, len(src.Nodes))
copy(copy.Nodes, src.Nodes)
```

### 方式三：append nil 切片（和方式一等价）
```go
var dst []NodeVisual
dst = append(dst, src.Nodes...)
```

## 检查清单

复制切片时，问自己：
1. ✅ `make` 的第二个参数是 `0` 还是 `len`？
   - 如果是 `len` → 必须用 `copy`，不能 `append`
   - 如果不确定 → 用 `append([]T{}, src...)`
2. ✅ 测试时看 `got` 是不是 `expected*2` → 翻倍 bug
3. ✅ 有多处深拷贝时全部检查，同一个坑不会只出现一次

## 参考

- [Go Slices: usage and internals](https://go.dev/blog/slices-intro)
- [Go Wiki: SliceTricks](https://go.dev/wiki/SliceTricks)
