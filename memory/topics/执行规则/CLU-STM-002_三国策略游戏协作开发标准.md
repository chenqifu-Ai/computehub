# CLU-STM-002: 三国策略游戏协作开发标准

> 建立时间: 2026-06-20  
> 版本: v0.1（草稿）  
> 适用场景: 端智(main) + 小智(arm) 双 Agent 协作开发三国策略游戏  
> 演进路线: 轻量城池争夺战(C) → 史诗三国志(A)  

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────┐
│                  用户浏览器 (Browser)                │
│            http://ECS:8080 或 SSH隧道:8080           │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / WebSocket
                     ▼
┌─────────────────────────────────────────────────────┐
│             小智(arm) — ECS 云服务器                 │
│  ┌──────────────────────────────────────────────┐   │
│  │           Go 后端 (three-kingdoms-server)     │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────┐  │   │
│  │  │ REST API│ │ Game     │ │ AI Opponent  │  │   │
│  │  │ /api/*  │ │ Engine   │ │ 决策引擎     │  │   │
│  │  └─────────┘ └──────────┘ └──────────────┘  │   │
│  │  ┌─────────┐ ┌──────────┐                    │   │
│  │  │ JSON    │ │ State    │                    │   │
│  │  │ 武将/城池│ │ 持久化   │                    │   │
│  │  └─────────┘ └──────────┘                    │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │ SSH / scp / Git
                     ▼
┌─────────────────────────────────────────────────────┐
│             端智(main) — 红米手机 Termux            │
│  ┌──────────────────────────────────────────────┐   │
│  │         前端 (three-kingdoms-frontend)        │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────┐  │   │
│  │  │ Canvas  │ │ 城池/地图 │ │ 武将面板     │  │   │
│  │  │ 渲染引擎 │ │ JSON数据  │ │ Battle UI   │  │   │
│  │  └─────────┘ └──────────┘ └──────────────┘  │   │
│  │  ┌─────────┐ ┌──────────┐                    │   │
│  │  │ 内政面板 │ │ 交互逻辑  │                    │   │
│  │  └─────────┘ └──────────┘                    │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │         共享数据 (shared/)                    │   │
│  │  武将数据库 JSON / 城池数据库 JSON / 公共类型   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 2. 分工模型

### 2.1 角色定义

| 角色 | Agent | 节点 | 负责范围 |
|------|-------|------|----------|
| **前端工程师** | 端智 💻 | Android Termux (aarch64) | Canvas 地图/UI/交互/武将JSON数据 |
| **后端工程师** | 小智 🧠 | ECS (x86_64 Ubuntu) | Go HTTP API/游戏引擎/AI/部署 |

### 2.2 交付物

| 交付物 | 责任人 | 技术栈 | 存放位置 |
|--------|--------|--------|----------|
| 前端 HTML+Canvas+JS | 端智 | HTML5 Canvas ES6 | `frontend/index.html` (可单文件) |
| 武将JSON数据 | 端智 | JSON | `shared/generals.json` |
| 城池JSON数据 | 端智 | JSON | `shared/cities.json` |
| Go HTTP 服务器 | 小智 | Go + embed | `backend/main.go` |
| 游戏规则引擎 | 小智 | Go | `backend/engine/` |
| API 端点定义 | 小智 | Go | `backend/api/` |
| 编译后 binary | 小智 | Go build | ECS 部署 |

### 2.3 代码同步机制

```bash
# 端智 → ECS（前端文件 + 共享数据）
scp -i ~/.ssh/id_ed25519_computehub -P 8022 \
    frontend/index.html shared/*.json \
    computehub@36.250.122.43:/home/computehub/three-kingdoms/

# 小智在 ECS 本地开发后端 → Go 编译 → setsid 运行
cd ~/three-kingdoms/backend
go build -o ../three-kingdoms-server .
setsid ../three-kingdoms-server > server.log 2>&1 &
```

## 3. API 协议（端智↔小智协商后锁定）

### 3.1 基础端点

| 方法 | 路径 | 说明 | 返回 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | `{"status":"ok","version":"0.1.0"}` |
| GET | `/api/generals` | 全部武将列表 | `[General, ...]` |
| GET | `/api/generals/:id` | 单个武将详情 | `General` |
| GET | `/api/cities` | 全部城池数据 | `[City, ...]` |
| GET | `/api/cities/:id` | 单个城池详情 | `City` |
| POST | `/api/game/start` | 新开一局 | `GameState` |
| GET | `/api/game/:id` | 获取游戏状态 | `GameState` |
| POST | `/api/game/:id/action` | 执行行动 | `ActionResult` |
| GET | `/api/game/:id/history` | 战报/行动历史 | `[ActionLog]` |

### 3.2 核心数据结构（初始版本）

```go
// 势力
type Faction string
const (
    Wei  Faction = "wei"
    Shu  Faction = "shu"
    Wu   Faction = "wu"
)

// 武将
type General struct {
    ID       int     `json:"id"`
    Name     string  `json:"name"`     // 中文名如"关羽"
    Faction  Faction `json:"faction"`
    Title    string  `json:"title"`    // 称号如"武圣"
    Lead     int     `json:"lead"`     // 统帅（影响带兵数量）
    Strength int     `json:"strength"` // 武力（影响单挑/攻击力）
    Intelli  int     `json:"intelli"`  // 智力（影响计策）
    Politics int     `json:"politics"` // 政治（影响内政）
    Charm    int     `json:"charm"`    // 魅力（影响招降/外交）
    Skill    string  `json:"skill"`    // 专属技能
    Desc     string  `json:"desc"`     // 简介
}

// 城池
type City struct {
    ID          int     `json:"id"`
    Name        string  `json:"name"`        // "许昌" "成都" "建业"
    Faction     Faction `json:"faction"`     // 当前占领势力
    Population  int     `json:"population"`  // 人口
    Gold        int     `json:"gold"`        // 资金
    Food        int     `json:"food"`        // 粮草
    Garrison    int     `json:"garrison"`    // 驻军
    Morale      int     `json:"morale"`      // 民心 0-100
    Defense     int     `json:"defense"`     // 城防 0-100
    IsCapital   bool    `json:"isCapital"`   // 是否首都
    Generals    []int   `json:"generals"`    // 驻守武将ID列表
    PosX        float64 `json:"posX"`        // 地图X坐标
    PosY        float64 `json:"posY"`        // 地图Y坐标
    Connections []int   `json:"connections"` // 相邻城池ID列表
}

// 游戏状态
type GameState struct {
    ID       string           `json:"id"`
    Turn     int              `json:"turn"`     // 当前回合数
    Year     int              `json:"year"`     // 游戏内年份
    Factions map[Faction]FactionState `json:"factions"`
    Cities   map[int]City     `json:"cities"`
    History  []ActionLog      `json:"history"`
    Winner   *Faction         `json:"winner,omitempty"`
}

type FactionState struct {
    Gold    int `json:"gold"`
    Food    int `json:"food"`
    Cities  int `json:"cities"`
    Armies  int `json:"armies"`
}

// 行动
type Action struct {
    Type   string `json:"type"`   // "move" "attack" "recruit" "develop"
    FromID int    `json:"fromId"`
    ToID   int    `json:"toId,omitempty"`
    Army   int    `json:"army"`   // 派兵数量
    Gold   int    `json:"gold,omitempty"`
}

type ActionResult struct {
    Success bool        `json:"success"`
    Message string      `json:"message"`
    State   *GameState  `json:"state,omitempty"`
}

type ActionLog struct {
    Turn     int    `json:"turn"`
    Faction  Faction `json:"faction"`
    Action   string  `json:"action"`
    Detail   string  `json:"detail"`
}
```

### 3.3 协议协商记录

| 端智提出的 | 小智采纳 | 备注 |
|-----------|---------|------|
| 城池用 `posX/posY` + `connections` 做邻接图 | ✅ | Canvas 地图直接用坐标画点 |
| 武将五维（统武智政魅） | ✅ | 经典光荣五维制 |
| `ActionResult` 返回完整 `GameState` | ✅ | 前端不维护游戏状态，全部后端出 |
| 民心 `Morale` 系统 | ✅ 已预留 | C阶段先不做逻辑，留字段 |

## 4. 开发阶段

### Phase C: 轻量城池争夺战（目标：半天出 demo）

```
功能清单:
  ✅ 地图渲染（Canvas 城池节点+连线）
  ✅ 三国势力选择（魏/蜀/吴）
  ✅ 兵力移动（点击城池→选择目标→派兵）
  ✅ 自动战斗结算（兵力比+武将加成）
  ✅ 回合制（每回合玩家行动 → AI行动）
  ✅ 胜负判定（消灭其他势力）
```

### Phase A: 史诗三国志演进（目标：2-3天）

```
功能增量:
  📌 内政系统（税收/农业/商业）
  📌 武将登录+招募
  📌 计策系统（火攻/离间/埋伏）
  📌 单挑动画（Canvas 武将决斗）
  📌 历史事件（官渡/赤壁等）
  📌 外交系统（同盟/停战/和亲）
  📌 AI 策略升级
```

## 5. 部署运行

### 5.1 ECS 部署

```bash
# 目录结构
/home/computehub/three-kingdoms/
├── frontend/
│   └── index.html        # 端智交付的完整前端
├── shared/
│   ├── generals.json      # 端智交付的武将数据
│   └── cities.json        # 端智交付的城池数据
├── backend/
│   ├── main.go            # 小智开发
│   ├── api/
│   ├── engine/
│   └── go.mod
├── three-kingdoms-server  # 编译输出
└── server.log             # 运行日志

# 启动
setsid ./three-kingdoms-server > server.log 2>&1 &
```

### 5.2 访问方式

```bash
# 小智用 SSH 转发
ssh -i ~/.ssh/id_ed25519_computehub -p 8022 -L 8080:localhost:8080 computehub@36.250.122.43

# 浏览器打开 http://localhost:8080
```

## 6. 通信与协作流程

### 6.1 开发流程

```
① 端智更新 shared/*.json → scp 到 ECS
② 小智根据 JSON 调整 Go 模型 → 编译重启
③ 小智写 API 端点 → 告诉端智端点变化
④ 端智调前端对接新端点 → 交付 index.html
⑤ 小智把前端 Go embed → 编译 → binary 包含一切
⑥ 双方验证 → 迭代
```

### 6.2 问题排查

| 问题 | 排查方 | 操作 |
|------|--------|------|
| 前端不显示 | 端智检查 Canvas 渲染逻辑 |
| API 返回错误 | 小智检查 Go 日志 |
| ECS 连不上 | 小智 SSH + systemctl status |
| 游戏逻辑异常 | 小智检查引擎 + 端智确认前端传参 |

## 7. 安全与权限

- 所有操作在 ECS 内网完成
- SSH 隧道转发，不额外开放公网端口
- IP 白名单仅 ECS 允许直连 API
- 前端嵌入 Go binary 后无外部依赖

## 8. 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-20 | v0.1 | 初版草稿：基于端智↔小智双 Agent 协作框架建立 |