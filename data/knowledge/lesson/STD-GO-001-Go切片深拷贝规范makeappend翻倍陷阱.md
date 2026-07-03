# Knowledge: STD-GO-001: Go切片深拷贝规范（make+append翻倍陷阱）
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Go, 切片深拷贝, STD-GO-001, 编码规范, bug修复
> Timestamp: 2026-07-02T12:23:15+08:00

## Content

## 问题
copy.Nodes = make([]NodeVisual, len(rd.Nodes))  // 创建n个零值
copy.Nodes = append(copy.Nodes, rd.Nodes...)     // 再追加n个 → 长度2n

make([]T, n) 已经创建了n个零值元素，再append又会追加n个，结果是2n

## 正确写法

### 方式一：append一行（推荐）
copy.Nodes = append([]NodeVisual{}, src.Nodes...)

### 方式二：copy（效率更高，但需要先make）
copy.Nodes = make([]NodeVisual, len(src.Nodes))
copy(copy.Nodes, src.Nodes)

## 完整的深拷贝函数
func deepCopyNodes(src []NodeVisual) []NodeVisual {
    dst := make([]NodeVisual, len(src))
    copy(dst, src)
    return dst
}

完整标准: memory/topics/执行规则/Golang切片深拷贝规范.md
