# 🏢 OPC OS — AI产业园孵化器操作系统
## 详细技术实现路线图

> **版本**: v1.0  
> **日期**: 2026-05-24  
> **总工期**: 约12~16周  
> **核心理念**: AI跟AI在沟通，零人工参与的自动化商业生态

---

## 一、实施总览

```
里程碑                                   时间线 (周)
                                        1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
Phase 0: 概念验证与基础设施改造            ██ ██
Phase 1: OpcCompany (一人公司 Worker)        ██ ██ ██
Phase 2: OpenClaw 公司主管 Agent               ██ ██ ██
Phase 3: 产业园CEO Gateway                          ██ ██ ██
Phase 4: AI协作网络                                        ██ ██ ██ ██
Phase 5: 生态完善与产品化                                             ██ ██ ██ ██
```

---

## 二、Phase 0: 概念验证与基础设施改造（1-2周）

### 目标
在现有 ComputeHub 架构上建立概念映射，不改核心代码，先跑通「一人公司」逻辑。

### 2.1 概念映射表（代码级）

```go
// 现有概念 → 新概念
NodeRegister.NodeID        → Company.CompanyID     // 公司ID
NodeRegister.NodeType      → Company.BusinessType  // 公司业务类型
NodeRegister.Region        → Company.Location       // 所在园区
NodeMetrics                → Company.Performance    // 公司运营指标
TaskSubmit                 → CompanyOrder           // 公司间订单
TaskSubmit.AssignedNode    → Order.AssignedCompany  // 接单公司
```

### 2.2 代码改动

```go
// 新增: company.go — 公司概念层（轻量包装，不改底层kernel）
package company

type CompanyID string  // 格式: "opc-{园区ID}-{编号}"

type Company struct {
    ID           CompanyID    `json:"id"`
    Name         string       `json:"name"`          // 公司名
    BusinessType string       `json:"business_type"` // marketing/production/finance/legal
    Status       string       `json:"status"`        // active/inactive/suspended
    WorkerNodeID string       `json:"worker_node_id"` // 对应 Worker 节点ID
    OpenClawID   string       `json:"openclaw_id"`    // OpenClaw主管ID
    Services     []Service    `json:"services"`       // 提供服务列表
    CreatedAt    time.Time
    LastActive   time.Time
}

type Service struct {
    Name        string `json:"name"`        // "视频制作"
    Description string `json:"description"` // "支持文档→TTS→视频全自动"
    Price       string `json:"price"`       // "¥99/条" 或 议价
    AvgResponse string `json:"avg_response"`// "2h"
}
```

### 2.3 新目录结构

```
projects/computehub/src/
├── gateway/        (现有)
├── kernel/         (现有)
├── scheduler/      (现有)
├── company/        ← 新增：公司概念层
│   ├── company.go      (公司结构体)
│   ├── registry.go     (公司注册/注销)
│   └── service_catalog.go (服务目录)
├── order/          ← 新增：公司间订单
│   ├── order.go        (订单结构体)
│   └── settlement.go   (结算逻辑)
└── mesh/           ← 新增：网关互连
    ├── peer.go          (对等节点)
    ├── trust.go         (信任模型)
    └── protocol.go      (通信协议)
```

### 2.4 配置文件扩展

```jsonc
// config.json 新增字段
{
  "opc": {
    "park_name": "智创产业园",         // 园区名称
    "park_id": "park-001",            // 园区ID
    "max_companies": 100,              // 最大入驻企业数
    "default_plan": "basic",          // 默认服务方案
    "services": [                      // 公共服务
      { "type": "finance", "enabled": true },
      { "type": "legal", "enabled": true },
      { "type": "data", "enabled": true }
    ],
    "mesh": {
      "enabled": false,               // 跨园区互连（Phase 4 启用）
      "trust_other_parks": false
    }
  }
}
```

### 2.5 交付物

| 交付物 | 文件 | 工作量 |
|--------|------|--------|
| 概念映射文档 | `docs/OPC_CONCEPT_MAP.md` | 2h |
| Company 结构体 + Registry | `src/company/` | 1天 |
| 服务目录定义 | `src/company/service_catalog.go` | 0.5天 |
| config.json OPC 配置扩展 | `config.json` + validator | 0.5天 |
| **总计** | | **2天** |

---

## 三、Phase 1: OpcCompany — 一人公司 Worker（3-5周）

### 目标
将 Worker 升级为「一人公司」实体，具备独立身份、业务能力、服务目录。

### 3.1 OpcCompany Worker 架构

```
┌─────────────────────────────────────────────┐
│         OpcCompany Worker (一人公司)           │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  Layer 1: 基础层                      │    │
│  │  ┌────────────────────────────────┐   │    │
│  │  │  Worker Core (现有)            │   │    │
│  │  │  - 注册/心跳/任务/回传          │   │    │
│  │  └────────────────────────────────┘   │    │
│  │  ┌────────────────────────────────┐   │    │
│  │  │  Company Identity              │   │    │
│  │  │  - CompanyID / 企业身份         │   │    │
│  │  │  - 业务类型 / 服务目录          │   │    │
│  │  │  - API Key / 认证              │   │    │
│  │  └────────────────────────────────┘   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  Layer 2: 业务层                      │    │
│  │  ┌────────────────────────────────┐   │    │
│  │  │  Business Module (按类型加载)   │   │    │
│  │  │  · marketing: 社媒/分析/SEO    │   │    │
│  │  │  · production: 视频/图片/TTS   │   │    │
│  │  │  · finance: 记账/税务/分析      │   │    │
│  │  │  · legal: 合同/版权/合规        │   │    │
│  │  └────────────────────────────────┘   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  Layer 3: OpenClaw 层 (Phase 2)      │    │
│  │  [预留接口]                          │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 3.2 业务模块接口

```go
// business/module.go — 业务模块接口
package business

// BusinessModule 业务模块接口
type BusinessModule interface {
    Type() string                          // "marketing" / "production" / ...
    Name() string                          // "营销服务" / "制作服务"
    Services() []Service                   // 提供的服务列表
    Execute(order *Order) (*Result, error) // 执行订单
    Capabilities() []string                // "社媒运营", "视频管线", ...
    Health() string                        // 模块健康状态
}

// 预设业务模块
var AvailableModules = map[string]func() BusinessModule{
    "marketing":  NewMarketingModule,
    "production": NewProductionModule,
    "finance":    NewFinanceModule,
    "legal":      NewLegalModule,
    "data":       NewDataModule,
}
```

### 3.3 服务目录 (Service Catalog)

```yaml
# 每个公司启动时向Gateway注册服务目录
company: opc-001
name: "小智影业制作部"
type: production
services:
  - name: "文字转视频"
    description: "输入文本/脚本，AI自动生成配音+配图+视频"
    price: "¥99/条"
    turnaround: "2h"
    input_types: [text, markdown, docx]
    output_types: [mp4]
    pricing_model: per_item

  - name: "文档转视频"
    description: "上传PPTX/PDF文档，自动提取内容生成视频"
    price: "¥199/条"
    turnaround: "4h"
    input_types: [pptx, pdf, docx]
    output_types: [mp4]
    pricing_model: per_item

  - name: "视频后期处理"
    description: "配音、去噪、加字幕、BGM"
    price: "¥49/次"
    turnaround: "1h"
    input_types: [mp4, mp3, wav]
    output_types: [mp4]
    pricing_model: per_item
```

### 3.4 Worker 启动参数扩展

```bash
# 现有 worker 启动
computehub worker --gw http://192.168.1.17:8282

# 新: OpcCompany 启动
computehub company \
  --gw http://park-01-gateway:8282 \
  --company-id opc-001 \
  --company-name "小智影业制作部" \
  --business-type production \
  --services "video-pptx,video-text,video-edit"
```

### 3.5 交付物

| 交付物 | 文件 | 工作量 |
|--------|------|--------|
| Company Worker 架构实现 | `src/workercmd/company.go` | 1周 |
| BusinessModule 接口 | `src/business/module.go` | 2天 |
| 预设业务模块 (4个) | `src/business/*.go` | 1周 |
| 服务目录注册逻辑 | `src/company/service_catalog.go` | 2天 |
| 启动参数扩展 | gateway + worker 命令行 | 1天 |
| 单元测试 | `*_test.go` | 2天 |
| **总计** | | **~3周** |

---

## 四、Phase 2: OpenClaw 公司主管 Agent（6-8周）

### 目标
每个 OpcCompany 内部运行一个 OpenClaw Agent，作为公司的AI主管/CEO，自主运营公司。

### 4.1 OpenClaw Agent 架构

```
┌─────────────────────────────────────────────┐
│        OpenClaw Agent (公司CEO/主管)          │
│                                              │
│  ┌─── Agent 核心 ──────────────────────┐    │
│  │  · 决策引擎 (基于LLM)               │    │
│  │  · 工具调用 (接BusinessModule)      │    │
│  │  · 任务规划 (多步任务分解)           │    │
│  │  · 记忆管理 (MEMORY.md持久化)        │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌─── 运营循环 ────────────────────────┐    │
│  │  每日巡逻 (HEARTBEAT)               │    │
│  │    ├── 检查待办订单                  │    │
│  │    ├── 检查生产任务状态               │    │
│  │    ├── 检查公司财务健康               │    │
│  │    ├── 检查客户满意度                 │    │
│  │    ├── 检查竞品/市场动态              │    │
│  │    └── 汇报给CEO Gateway             │    │
│  │                                      │    │
│  │  任务处理                            │    │
│  │    ├── 接单 → 评估 → 排期             │    │
│  │    ├── 执行 → 调用BusinessModule     │    │
│  │    └── 交付 → 回传结果 → 结算         │    │
│  │                                      │    │
│  │  自主决策                            │    │
│  │    ├── 在授权范围内自主决策            │    │
│  │    ├── 超出权限时向Gateway申请         │    │
│  │    └── 异常处理 (任务失败/超时/投诉)    │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌─── 知识库 ──────────────────────────┐    │
│  │  SOUL.md: 人格/公司文化              │    │
│  │  HEARTBEAT.md: 巡逻清单/KPI          │    │
│  │  SKILLS.md: 能力集/工具使用方法       │    │
│  │  MEMORY.md: 项目/客户/经验记忆       │    │
│  │  SOPs/: 业务标准操作流程             │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 4.2 OpenClaw 运行方式

```go
// openclaw/agent.go — OpenClaw Agent 核心
package openclaw

type Agent struct {
    ID        string            // Agent ID
    CompanyID string            // 所属公司
    Config    *AgentConfig      // 配置 (SOUL/HEARTBEAT/SKILLS)
    Memory    *MemoryStore      // 记忆存储
    LLM       *LLMClient        // LLM客户端
    Tools     *ToolRegistry     // 可调用的工具集
    
    // 运营状态
    Status    string            // idle/working/sleeping
    TaskQueue []*Task           // 待处理任务
    LastReport time.Time        // 上次汇报时间
}

type AgentConfig struct {
    SoulFile  string   // SOUL.md 路径 (人格定义)
    HBSpec    string   // HEARTBEAT.md 路径 (巡逻规格)
    SkillsDir string   // SKILLS/ 目录 (技能定义)
    MemoryDir string   // MEMORY/ 目录 (持久记忆)
    
    // 行为参数
    AutonomyLevel int    // 自主程度: 0-10 (0=全需批准, 10=全自主)
    MaxBudget     string // "¥500/天" 自主预算上限
    ReportFreq    string // "1h" 汇报频率
}
```

### 4.3 Agent ↔ BusinessModule 通信

```go
// 工作流示例: 营销公司OpenClaw接单
//
// 1. CEO Gateway 派单给营销公司
//    → OpenClaw 收到订单
//
// 2. OpenClaw 评估:
//    "这是一个产品宣传需求，需要分析卖点"
//    → 调用 marketing 模块: AnalyzeProduct(text)
//    → 得到 脚本需求文档
//
// 3. OpenClaw 决策:
//    "脚本完成，但我不会做视频"
//    → 查询 服务目录: 找到制作公司
//    → 向 CEO Gateway 请求: "委托opc-002制作视频"
//
// 4. CEO Gateway 转发:
//    → 制作公司 OpenClaw 收到委托
//
// 5. 制作公司 OpenClaw:
//    "收到脚本，调用视频管线"
//    → 调用 production 模块: RenderVideo(script)
//    → 得到 成品视频
//
// 6. 交付链路:
//    制作OpenClaw → CEO Gateway → 营销OpenClaw → 客户
```

### 4.4 Agent LLM 调用

```go
// 每个 Agent 需要独立的 LLM 连接
// 配置来源: Company 的 config/llm.conf

type LLMConfig struct {
    Provider string  // "zhangtuo-ai" / "ollama-cloud" / ...
    Model    string  // "qwen3.6-35b" / "deepseek-v4-flash"
    APIKey   string  // 公司独立API Key (或共享池)
    MaxTokens int   // 2048
}
```

### 4.5 OpenClaw 模板目录结构

```
/opc-companies/
└── opc-001/                      # 公司目录
    ├── openclaw/                  # OpenClaw 主管
    │   ├── SOUL.md                # 人格: 制作公司CEO
    │   ├── HEARTBEAT.md           # 巡逻: 每天查任务/质量/成本
    │   ├── SKILLS.md              # 技能: 视频管线/图片识别
    │   ├── MEMORY.md              # 记忆: 项目/客户/经验
    │   └── config/
    │       ├── llm.conf           # LLM连接配置
    │       └── autonomy.conf      # 自主权限配置
    ├── data/                      # 公司数据
    │   ├── projects/              # 项目文件
    │   └── assets/                # 素材/模板
    └── logs/                      # 运营日志
```

### 4.6 交付物

| 交付物 | 文件 | 工作量 |
|--------|------|--------|
| OpenClaw Agent 核心 | `src/openclaw/agent.go` | 1周 |
| Agent 配置系统 | `src/openclaw/config.go` | 3天 |
| LLM 集成 | `src/openclaw/llm.go` | 2天 |
| 工具注册/调用 | `src/openclaw/tools.go` | 3天 |
| 记忆系统 (MEMORY持久化) | `src/openclaw/memory.go` | 2天 |
| 巡逻循环 (HEARTBEAT) | `src/openclaw/heartbeat.go` | 2天 |
| 汇报机制 → CEO Gateway | `src/openclaw/report.go` | 2天 |
| 模板目录初始化 | `src/company/init.go` | 1天 |
| **总计** | | **~3周** |

---

## 五、Phase 3: 产业园 CEO Gateway（9-11周）

### 目标
将 OpcGateway 升级为产业园大脑，管理企业入驻/服务/调度/结算，作为所有 OPC 公司的调度中心。

### 5.1 CEO Gateway 新组件

```go
// gateway/ceo.go — CEO Gateway 核心
type CEOGateway struct {
    // ── 现有能力 ──
    Kernel    *OpcKernel     // 节点管理
    Gateway   *OpcGateway    // HTTP服务
    
    // ── 企业服务中心 ──
    Registry  *CompanyRegistry  // 企业注册/注销
    Directory *ServiceDirectory // 服务目录 (哪些公司提供什么服务)
    
    // ── 任务调度中心 ──
    Matcher   *ServiceMatcher   // 需求→公司匹配
    Orcher    *Orchestrator     // 跨公司任务编排
    
    // ── 公共服务 ──
    Finance   *FinanceCenter    // 财务结算中心
    Legal     *LegalCenter      // 法务合规中心
    DataHub   *DataHub          // 数据中台
    
    // ── 管理终端 ──
    Dashboard *ParkDashboard    // 产业园仪表盘
}
```

### 5.2 企业服务中心

```go
// company/registry.go — 企业全生命周期管理
type CompanyRegistry struct {
    companies map[CompanyID]*Company
    
    // 入驻
    Register(req *RegisterRequest) (*Company, error)
    // 企业入驻流程:
    //   1. 提交企业注册(名称/业务类型/服务目录)
    //   2. 分配 Worker 节点
    //   3. 分配 OpenClaw 模板
    //   4. 初始化公司目录
    //   5. 返回公司ID + 认证Token
    
    // 注销
    Unregister(companyID CompanyID) error
    // 企业注销流程:
    //   1. 检查未完成订单
    //   2. 结算资产/负债
    //   3. 归档公司数据
    //   4. 释放 Worker 节点
    //   5. 吊销认证Token
    
    // 暂停/恢复
    Suspend(companyID CompanyID, reason string) error
    Activate(companyID CompanyID) error
    
    // 状态查询
    Get(companyID CompanyID) *Company
    List(filter *CompanyFilter) []*Company
    Health(companyID CompanyID) string  // 公司健康检查
}
```

### 5.3 服务匹配引擎

```go
// company/matcher.go — 需求→公司自动匹配
type ServiceMatcher struct {
    directory *ServiceDirectory
}

// Match 根据客户需求，自动匹配合适的公司
func (m *ServiceMatcher) Match(req *ServiceRequest) ([]*MatchResult, error) {
    // 匹配算法:
    //   1. 解析需求: "我要做一支宣传视频" → video_production
    //   2. 查询服务目录: 哪些公司提供 video_production
    //   3. 评分排序:
    //      - 价格评分 (预算匹配度)
    //      - 时效评分 (交期匹配度)
    //      - 质量评分 (历史评价)
    //      - 负载评分 (当前任务量)
    //   4. 返回 Top-3 推荐
}
```

### 5.4 业务流程编排器

```go
// company/orchestrator.go — 跨企业业务流程编排
type Orchestrator struct {
    workflows map[string]*Workflow
}

// Workflow 定义跨公司业务流程
type Workflow struct {
    ID          string
    Name        string
    Steps       []WorkflowStep
    MaxDuration time.Duration
}

type WorkflowStep struct {
    StepID      string
    ServiceType string      // 需要的服务类型
    Input       interface{} // 输入
    AssignedTo  CompanyID   // 自动匹配的公司
    DependsOn   []string    // 依赖的上一步ID
    Timeout     time.Duration
    RetryCount  int
}
```

#### 预置业务流程模板

```yaml
# 示例: 产品宣传视频全流程
id: wf-product-video
name: "产品宣传视频制作"
steps:
  - id: step-1
    service_type: marketing_analysis
    timeout: 2h
    description: "分析产品卖点，输出脚本需求"
    
  - id: step-2
    service_type: video_production
    depends_on: [step-1]
    timeout: 24h
    description: "根据脚本生成宣传视频"
    
  - id: step-3
    service_type: finance_roi
    depends_on: [step-2]
    timeout: 30m
    description: "核算成本，输出ROI报告"
    
  - id: step-4
    service_type: ceo_review  # 园区级审批
    depends_on: [step-2, step-3]
    timeout: 1h
    description: "CEO审批，决定是否发布"
```

### 5.5 产业园仪表盘 (TUI 增强)

```go
// TUI 新增园区级面板

// 总览仪表盘
┌─────────────────────────────────────────────────────────────────┐
│  🏢 智创产业园  │  入驻企业: 12/100  │  活跃: 8  │  园区负载: 65% │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  企业列表                       服务市场                        │
│  ┌──────────────┬────────┬────┐  ┌──────────────┬──────┬─────┐ │
│  │ 公司名        │ 类型   │状态│  │ 服务          │ 价格  │ 公司│ │
│  ├──────────────┼────────┼────┤  ├──────────────┼──────┼─────┤ │
│  │ 小智制作部   │ production │🟢 │  │ 视频制作      │ ¥199 │ opc-001│ │
│  │ 小明营销部   │ marketing  │🟢 │  │ 社媒运营      │ ¥99  │ opc-002│ │
│  │ 财务部       │ finance    │🟢 │  │ 记账报税      │ ¥49  │ opc-003│ │
│  │ 法务部       │ legal      │🟡 │  │ 合同审查      │ ¥29  │ opc-004│ │
│  └──────────────┴────────┴────┘  └──────────────┴──────┴─────┘ │
│                                                                 │
│  活跃订单                       园区收入                        │
│  ┌──────────────────┬───────┐  ┌──────────────────┬──────────┐ │
│  │ 订单ID           │ 阶段  │  │ 今日收入         │ ¥2,340   │ │
│  │ order-001        │ 制作中 │  │ 本月收入         │ ¥45,200  │ │
│  │ order-002        │ 待审批 │  │ 累计收入         │ ¥128,900 │ │
│  │ order-003        │ 已完成 │  │ 园区收入(佣金)   │ ¥12,890  │ │
│  └──────────────────┴───────┘  └──────────────────┴──────────┘ │
│                                                                 │
│  🧠 今日AI对话                                                    │
│  09:23 营销公司→制作公司: "委托制作产品宣传视频"                   │
│  10:45 制作公司→财务公司: "核算视频成本"                         │
│  14:12 财务公司→CEO: "本月园区营收已超上月"                      │
└─────────────────────────────────────────────────────────────────┘
```

### 5.6 交付物

| 交付物 | 文件 | 工作量 |
|--------|------|--------|
| CEO Gateway 核心 | `src/gateway/ceo.go` | 3天 |
| 企业注册/注销 | `src/company/registry.go` | 1周 |
| 服务目录 | `src/company/service_catalog.go` (增强) | 3天 |
| 服务匹配引擎 | `src/company/matcher.go` | 1周 |
| 业务流程编排器 | `src/company/orchestrator.go` | 1周 |
| 业务流程模板 (预置4个) | `src/company/workflows/` | 3天 |
| 财务结算中心 | `src/company/settlement.go` | 1周 |
| TUI 园区仪表盘 | `src/tui/park.go` | 1周 |
| 认证/Token管理 | `src/company/auth.go` | 2天 |
| **总计** | | **~3周** |

---

## 六、Phase 4: AI协作网络 — Gateway Mesh（12-15周）

### 目标
实现 Gateway↔Gateway 互连，让不同产业园的 OPC 公司之间也能协作。

### 6.1 Gateway Mesh 协议

```go
// mesh/protocol.go — Gateway Mesh 协议定义
package mesh

// PeerInfo 对等网关信息
type PeerInfo struct {
    PeerID    string   // 网关ID
    ParkName  string   // 产业园区名称
    Endpoint  string   // 连接地址 ws://park-02:8282/mesh
    PublicKey string   // 公钥 (用于JWT认证)
    
    // 信任等级
    TrustLevel TrustLevel // 0=none, 1=read, 2=task, 3=full
    
    // 园区概况
    Companies  int      // 入驻企业数
    Services   []string // 园区提供的服务类型
    Capacity   string   // "100tasks/h"
}

// TrustLevel 信任等级
type TrustLevel int
const (
    TrustNone TrustLevel = iota // 不信任
    TrustRead                   // 只读 (可查看服务目录)
    TrustTask                   // 可委托任务
    TrustShare                  // 可共享资源
    TrustFull                   // 完全信任 (代码/数据/算力)
)

// 连接流程:
// 1. Park-A 发送连接请求 (含 JWT Token)
// 2. Park-B 验证 Token 签名
// 3. Park-B 查询信任等级配置
// 4. 握手成功 → 建立 WebSocket
// 5. 同步服务目录
// 6. 开始协作
```

### 6.2 跨园区任务委托

```go
// 跨园区工作流示例
//
// 园区A (智创产业园)              园区B (数字创意园)
// ─────────────────             ─────────────────
//  小智制作部 —产能不足—→   委托   →  大刘设计部
//                                      (有闲置产能)
//
// 1. 园区A CEO Gateway 查询服务目录
//     → 发现园区B有 "视频后期" 服务, 可用
// 2. 园区A → Mesh协议 → 园区B
//     → 提交委托订单
// 3. 园区B 大刘设计部 OpenClaw 接单
//     → 执行 → 输出视频
// 4. 园区B → 回传 → 园区A
//     → 交付给客户
// 5. 自动结算: 园区A支付园区B
```

### 6.3 Mesh 网络安全

```yaml
安全模型:
  1. 传输加密: TLS 1.3 (所有Gateway Mesh通信)
  2. 身份认证: JWT + Ed25519 签名
  3. 权限控制: TrustLevel 等级制
  4. 审计日志: 所有跨园区操作记录
  5. 熔断机制: 异常流量自动隔离
  
信任建立:
  - 首次连接: 手动添加对等网关 (exchange public keys)
  - 自动续签: JWT 24h有效期, 自动续签
  - 吊销: 管理端手动吊销
```

### 6.4 交付物

| 交付物 | 文件 | 工作量 |
|--------|------|--------|
| Mesh 协议定义 | `src/mesh/protocol.go` | 3天 |
| WebSocket 连接管理 | `src/mesh/connection.go` | 1周 |
| 信任模型 & JWT | `src/mesh/trust.go` | 3天 |
| 跨园区任务路由 | `src/mesh/routing.go` | 1周 |
| 跨园区结算 | `src/mesh/settlement.go` | 1周 |
| 安全审计日志 | `src/mesh/audit.go` | 2天 |
| 园区间服务目录同步 | `src/mesh/sync.go` | 3天 |
| TUI 网状视图 | `src/tui/mesh.go` | 3天 |
| **总计** | | **~4周** |

---

## 七、Phase 5: 生态完善与产品化（16周+）

### 目标
完善生态，提供模板市场/第三方开发/运维工具，使 OPC OS 可产品化。

### 7.1 业务模块商店

```
┌─────────────────────────────────────────┐
│  📦 OPC OS 业务模块商店                    │
│                                          │
│  预设模块 (免费)                          │
│  ├── 营销模块: 社媒运营/数据分析/SEO      │
│  ├── 制作模块: 视频管线/图片识别/TTS      │
│  ├── 财务模块: 记账/税务/ROI分析          │
│  ├── 法务模块: 合同/版权/合规             │
│  └── 数据模块: 采集/监控/报告             │
│                                          │
│  第三方模块 (付费/开源)                    │
│  ├── 编程开发: 代码生成/测试/部署          │
│  ├── 电商运营: 商品上架/客服/物流          │
│  ├── 教育培训: 课程制作/学生管理           │
│  └── ...                                  │
│                                          │
│  BusinessModule 接口规范                  │
│  └── 开发者文档: plugin-dev-guide.md      │
└─────────────────────────────────────────┘
```

### 7.2 运营工具

| 工具 | 用途 |
|------|------|
| `opc-admin` CLI | 园区管理: 企业入驻/监控/审计 |
| `opc-backup` | 公司数据自动备份/恢复 |
| `opc-migrate` | 公司迁移 (换机器/园区间迁移) |
| `opc-monitor` | 全链路监控 (Gateway/Worker/Agent) |
| `opc-billing` | 园区计费/分成/发票 |

### 7.3 产品化准备

```yaml
部署方案:
  最小化部署 (一人公司入门):
    - 1台 VPS (2C4G)
    - 1个 CEO Gateway
    - 1个 OpcCompany (自带OpenClaw)
    - 月成本 ≈ ¥50-100
  
  标准部署 (小型产业园):
    - 1台服务器 (4C8G)
    - 1个 CEO Gateway
    - 5-10个 OpcCompany
    - 月成本 ≈ ¥200-500
  
  集群部署 (大型产业园):
    - 集群服务器
    - 分布式 CEO Gateway
    - 100+ OpcCompany
    - 月成本 ≈ ¥1000+
```

---

## 八、项目总结

### 8.1 开发量估算

| Phase | 内容 | 时间 | 代码行数(估) |
|-------|------|------|-------------|
| Phase 0 | 概念验证 | 2周 | ~1,000 |
| Phase 1 | OpcCompany Worker | 3周 | ~3,000 |
| Phase 2 | OpenClaw Agent | 3周 | ~4,000 |
| Phase 3 | CEO Gateway | 3周 | ~5,000 |
| Phase 4 | Gateway Mesh | 4周 | ~4,000 |
| Phase 5 | 生态完善 | 持续 | ~3,000 |
| **总计** | **完整实现** | **~16周** | **~20,000** |

### 8.2 关键里程碑

```
Week 2:  概念验证完成 - "一人公司"可注册/注销
Week 5:  OpcCompany 跑通 - Worker可作为公司启动
Week 8:  OpenClaw 开始运营 - 第一家AI自主公司
Week 11: 产业园区跑通 - 多公司协作流程
Week 15: 跨园区协作跑通 - Gateway Mesh 连接
Week 20: MVP 发布 - 可部署给外部用户
```

### 8.3 一句话

> **OPC OS 不是做一个软件，而是构建一个 AI 自主运营的商业生态——产业园是平台，OPC 公司是租户，OpenClaw 是 CEO，AI 跟 AI 在沟通，人类只需要下订单和收结果。**

---

> **文档版本**: v1.0 | **最后更新**: 2026-05-24 | **作者**: 小智
