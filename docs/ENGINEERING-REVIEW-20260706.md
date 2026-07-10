# ComputeHub 工程评审报告 — 2026-07-06

**评审人**: 小智  
**代码库**: ComputeHub (51K Go + 6.7K Python + 2.4K Shell)  
**提交数**: 7 (当前分支) | **标签**: v1.3.53 | **测试文件**: 29

---

## 一、总体评价

ComputeHub 是一个功能完整的分布式计算平台，Gateway + Worker + Agent 三层架构清晰，功能覆盖了任务调度、AI Agent、知识共享、OCR、视频处理、Gallery 文件服务等。代码质量整体中等偏上，但存在一些工程化问题需要解决。

**评分**: 7/10 — 功能丰富，工程化有提升空间

---

## 二、发现的问题（按严重程度排序）

### 🔴 P0 — 必须修复

#### 1. API Key 明文存储

**位置**: `config.json`  
**问题**: API Key `sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB` 以明文存储在配置文件中，已提交到 Git 历史。

**建议**:
- 立即从 Git 历史中清除（`git filter-branch` 或 `bfg`）
- 轮换该 Key
- 改用环境变量 `COMPUTEHUB_API_KEY` 注入
- `config.json` 只存占位符 `${API_KEY}`

---

#### 2. 硬编码路径

**位置**: 多处（gallery.go:70, gateway.go:236/242/2046, video.go:236 等）  
**问题**: `/home/computehub` 硬编码在源码中，无法部署到其他环境。

**建议**:
- 统一用 `config.json` 的 `data_dir` 字段
- 所有路径通过配置或环境变量注入
- 加一个 `paths.go` 集中管理所有路径

---

#### 3. 两个 JSON 响应函数

**位置**: `gateway.go:748` (`sendResponse`) vs `gallery.go:1019` (`writeJSON`)  
**问题**: 两个函数做同一件事，11 个文件混用，不一致。

```go
// gateway.go — 方法接收器
func (g *OpcGateway) sendResponse(w http.ResponseWriter, resp Response)

// gallery.go — 普通函数
func writeJSON(w http.ResponseWriter, data interface{})
```

**建议**: 统一为 `writeJSON(w, resp)`，删除 `sendResponse`。

---

### 🟡 P1 — 建议修复

#### 4. 重复的 binary 目录

| 目录 | 文件数 | 大小 | 用途 |
|------|:-----:|:----:|------|
| `bin/` | 14 | 85M | 编译输出 |
| `deploy/` | 61 | 45M | 部署包 |
| `build/` | 1 | 11M | 构建缓存 |

**问题**: 三个目录存同样的 binary，`deploy/` 还混入了 hall 文件、wheels、logs 等。

**建议**:
- `bin/` = 编译输出（gitignore）
- `deploy/` = 部署包（只含 binary + 必要配置）
- 删除 `build/`（未使用）
- 清理 `deploy/` 中的 logs/、wheels/ 等杂项

---

#### 5. 模块名不一致

**位置**: `go.mod:1`  
**问题**: 模块名 `github.com/computehub/opc`，但仓库名是 `ComputeHub`，import 路径用 `github.com/computehub/opc/src/...`。

**建议**: 统一为 `github.com/computehub/computehub` 或 `computehub.io/computehub`。

---

#### 6. 测试覆盖不足

| 包 | 源文件 | 测试文件 | 覆盖率 |
|---|:-----:|:--------:|:-----:|
| gateway | 25 | 5 | 20% |
| workercmd | 20 | 3 | 15% |
| agent | 6 | 3 | 50% |
| **executil** | **1** | **0** | **0%** |
| **prometheus** | **1** | **0** | **0%** |
| **version** | **1** | **0** | **0%** |
| **gatewaycmd** | **1** | **0** | **0%** |

**建议**: 优先为无测试的包加基础测试，目标整体覆盖率 ≥ 40%。

---

#### 7. 全局变量泛滥

**位置**: 多个文件  
**问题**: 大量包级全局变量，难以测试和并发控制。

```go
var globalKnowledgeStore = &KnowledgeStore{...}
var clusterMem = &ClusterMemory{...}
var ocrStats = OCRStats{}
var hall = &HallState{...}
var globalReplyStore = NewReplyStore()
```

**建议**: 通过 `OpcGateway` 结构体持有这些状态，依赖注入。

---

#### 8. 大文件需要拆分

| 文件 | 行数 | 建议 |
|------|:----:|------|
| `tuicmd/tui_main.go` | 2385 | 拆为 3-4 个文件 |
| `gateway/gateway.go` | 2105 | 拆为 2-3 个文件 |
| `gateway/gallery.go` | 2052 | 拆为 2-3 个文件 |
| `agent/memory.go` | 1696 | 拆为 2 个文件 |
| `workercmd/worker_agent.go` | 1488 | 拆为 2 个文件 |

**建议**: 按功能拆分，每个文件不超过 800 行。

---

### 🟢 P2 — 值得改进

#### 9. 缺少 Makefile

**问题**: 构建用 shell 脚本，没有标准化的 `make build` / `make test` / `make deploy`。

**建议**: 加 Makefile，统一入口。

#### 10. 缺少 CHANGELOG / CONTRIBUTING

**问题**: 没有版本变更记录和贡献指南。

**建议**: 加 `CHANGELOG.md` 和 `CONTRIBUTING.md`。

#### 11. 日志系统原始

**问题**: 用 `fmt.Printf` 加时间戳，没有日志级别、结构化输出、文件轮转。

**建议**: 引入 `slog`（Go 1.21+ 标准库）或 `log/slog`。

#### 12. 无速率限制

**问题**: API 端点无任何限流保护。

**建议**: 加简单的令牌桶或基于 IP 的限流中间件。

#### 13. 无 CI/CD

**问题**: 没有 GitHub Actions 或任何 CI 流水线。

**建议**: 加 GitHub Actions，每次 push 自动跑测试 + 编译。

#### 14. OCR 并发问题

**问题**: Tesseract 是 CPU 密集型，5 并发需要 16-25s。无连接池/队列。

**建议**: 加 Tesseract 工作池（最大 2-3 并发），超时请求排队。

#### 15. API 版本混乱

**问题**: 同时存在 `/api/` 和 `/api/v1/` 端点，无版本策略。

**建议**: 统一为 `/api/v1/`，旧端点加 deprecated 标记。

---

## 三、架构建议

### 短期（1-2 天）

| 优先级 | 事项 | 预估 |
|:-----:|------|:----:|
| 🔴 | 清除 Git 中的 API Key + 轮换 | 30min |
| 🔴 | 统一 `sendResponse` / `writeJSON` | 15min |
| 🟡 | 路径硬编码改为配置驱动 | 1h |
| 🟡 | 清理重复 binary 目录 | 30min |
| 🟡 | 加 Makefile | 30min |

### 中期（1 周）

| 事项 | 说明 |
|------|------|
| 大文件拆分 | gateway.go / gallery.go / tui_main.go |
| 全局变量 → 依赖注入 | 提高可测试性 |
| 测试覆盖 executil/prometheus/version | 加基础测试 |
| 引入 slog 日志 | 替代 fmt.Printf |
| OCR 工作池 | 解决并发超时 |

### 长期（1 月）

| 事项 | 说明 |
|------|------|
| CI/CD 流水线 | GitHub Actions |
| API 版本统一 | 废弃 `/api/` 端点 |
| 速率限制 | 令牌桶中间件 |
| 配置验证 | 启动时校验 config.json |
| 模块名修正 | go.mod 统一命名 |

---

## 四、亮点

1. **功能完整** — 任务调度、AI Agent、知识共享、OCR、视频、Gallery、Hall 通信，覆盖全面
2. **并发安全** — 大量使用 `sync.RWMutex`，竞态控制到位
3. **测试覆盖** — 29 个测试文件，核心逻辑有测试
4. **版本管理** — 规范的 git tag 和版本号
5. **文档** — 30 份文档，API 使用、设计规范、部署流程都有
6. **跨平台** — 5 个平台编译支持
7. **自动升级** — Worker 自动升级机制完善
8. **知识共享** — KSP-001 协议 + ClusterMemory 实现

---

## 五、总结

ComputeHub 是一个**功能强大但工程化有提升空间**的项目。核心架构和功能设计合理，但存在 API Key 泄露、硬编码路径、代码重复、大文件、测试不足等典型的"快速迭代后遗症"。

**建议优先处理 P0 安全问题和 P1 工程化问题**，特别是 API Key 清理和路径配置化，这是部署到其他环境的阻塞项。
