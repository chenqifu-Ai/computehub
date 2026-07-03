// Package agent — 专家 Agent 注册表
// Phase 3: 将 OpenClaw 的 5 个专家技能接入 ComputeHub Hall
//
// 每个专家是一个预定义的 Agent，拥有：
// - 领域特定的系统提示（system prompt）
// - 独立的记忆空间
// - 在 Hall 中的身份（可被 @ 调用）
// - 自主判断话题参与能力

package agent

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/composer"
)

// ══════════════════════════════════════════════════════════════════════
//  Expert 定义
// ══════════════════════════════════════════════════════════════════════

// Expert 专家 Agent 定义
type Expert struct {
	// 标识
	ID       string `json:"id"`       // 唯一 ID，如 "finance-expert"
	Name     string `json:"name"`     // 显示名，如 "财务专家"
	Nickname string `json:"nickname"` // @ 名，如 "财务专家"

	// 领域
	Domain      string   `json:"domain"`      // 领域分类
	Description string   `json:"description"` // 一句话描述
	Tags        []string `json:"tags"`        // 触发标签

	// 系统提示
	SystemPrompt string `json:"system_prompt"` // LLM 系统提示

	// 运行时
	llm      *composer.LLMClient
	memory   Memory
	sessions map[string][]composer.ChatMessage
	mu       sync.RWMutex

	// Phase 2: 共享记忆搜索回调（SPEC-DMEM-001）
	// 由 workercmd 注入，Think 时自动搜索相关记忆
	memorySearchFn func(query string, limit int) (string, error)
}

// ExpertRegistry 专家注册表
type ExpertRegistry struct {
	experts map[string]*Expert // key: expert ID
	byName  map[string]*Expert // key: @名（如 "财务专家"）
	byTag   map[string]*Expert // key: 标签关键词
	mu      sync.RWMutex
	llm     *composer.LLMClient
}

// NewExpertRegistry 创建专家注册表
func NewExpertRegistry(llm *composer.LLMClient) *ExpertRegistry {
	er := &ExpertRegistry{
		experts: make(map[string]*Expert),
		byName:  make(map[string]*Expert),
		byTag:   make(map[string]*Expert),
		llm:     llm,
	}
	er.registerDefaults()
	return er
}

// Register 注册一个专家
func (er *ExpertRegistry) Register(expert *Expert) {
	er.mu.Lock()
	defer er.mu.Unlock()

	expert.llm = er.llm
	expert.sessions = make(map[string][]composer.ChatMessage)

	er.experts[expert.ID] = expert
	er.byName[expert.Name] = expert
	er.byName[expert.Nickname] = expert

	for _, tag := range expert.Tags {
		er.byTag[tag] = expert
	}

	fmt.Printf("[ExpertRegistry] ✅ 注册专家: %s (%s)\n", expert.Name, expert.ID)
}

// Get 通过 ID 获取专家
func (er *ExpertRegistry) Get(id string) *Expert {
	er.mu.RLock()
	defer er.mu.RUnlock()
	return er.experts[id]
}

// GetByName 通过 @ 名获取专家
func (er *ExpertRegistry) GetByName(name string) *Expert {
	er.mu.RLock()
	defer er.mu.RUnlock()

	// 精确匹配
	if e, ok := er.byName[name]; ok {
		return e
	}

	// 模糊匹配：去掉 @ 前缀
	name = strings.TrimPrefix(name, "@")
	if e, ok := er.byName[name]; ok {
		return e
	}

	return nil
}

// MatchByContent 根据内容匹配专家（用于自动参与话题）
func (er *ExpertRegistry) MatchByContent(content string) []*Expert {
	er.mu.RLock()
	defer er.mu.RUnlock()

	lower := strings.ToLower(content)
	var matched []*Expert
	seen := make(map[string]bool)

	for tag, expert := range er.byTag {
		if seen[expert.ID] {
			continue
		}
		if strings.Contains(lower, strings.ToLower(tag)) {
			matched = append(matched, expert)
			seen[expert.ID] = true
		}
	}

	return matched
}

// List 列出所有专家
func (er *ExpertRegistry) List() []*Expert {
	er.mu.RLock()
	defer er.mu.RUnlock()

	list := make([]*Expert, 0, len(er.experts))
	for _, e := range er.experts {
		list = append(list, e)
	}
	return list
}

// ListDescriptions 返回专家描述（用于 LLM 系统提示）
func (er *ExpertRegistry) ListDescriptions() string {
	er.mu.RLock()
	defer er.mu.RUnlock()

	var b strings.Builder
	b.WriteString("可用专家 Agent（通过 hall_speak 工具 @ 他们）:\n\n")
	for _, e := range er.experts {
		b.WriteString(fmt.Sprintf("- @%s — %s\n", e.Nickname, e.Description))
	}
	return b.String()
}

// Think 让专家思考并回答一个问题
func (e *Expert) Think(ctx context.Context, task string, sessionID string) (string, error) {
	if sessionID == "" {
		sessionID = fmt.Sprintf("expert-%s-%d", e.ID, time.Now().UnixNano())
	}

	// 构建对话历史
	e.mu.Lock()
	if _, ok := e.sessions[sessionID]; !ok {
		e.sessions[sessionID] = make([]composer.ChatMessage, 0, 10)
	}
	history := e.sessions[sessionID]
	e.mu.Unlock()

	// Phase 2: 搜索共享记忆层中的相关经验
	var memoryContext string
	if e.memorySearchFn != nil {
		if memResult, err := e.memorySearchFn(task, 5); err == nil && memResult != "" {
			memoryContext = "\n\n## 集群共享记忆中的相关经验\n" + memResult
		}
	}

	// 构建消息
	systemContent := e.SystemPrompt
	if memoryContext != "" {
		systemContent += memoryContext
	}
	msgs := []composer.ChatMessage{
		{Role: "system", Content: systemContent},
	}

	// 追加历史（最多 5 轮）
	startIdx := 0
	if len(history) > 10 {
		startIdx = len(history) - 10
	}
	msgs = append(msgs, history[startIdx:]...)

	// 当前问题
	msgs = append(msgs, composer.ChatMessage{Role: "user", Content: task})

	// 调用 LLM
	result, err := e.llm.Chat(msgs, 2048)
	if err != nil {
		return "", fmt.Errorf("expert %s think failed: %w", e.Name, err)
	}

	// 保存历史
	e.mu.Lock()
	e.sessions[sessionID] = append(e.sessions[sessionID],
		composer.ChatMessage{Role: "user", Content: task},
		composer.ChatMessage{Role: "assistant", Content: result},
	)
	// 限制历史长度
	if len(e.sessions[sessionID]) > 20 {
		e.sessions[sessionID] = e.sessions[sessionID][len(e.sessions[sessionID])-20:]
	}
	e.mu.Unlock()

	// 记录到记忆
	if e.memory != nil {
		e.memory.AppendSession(sessionID, "User", task)
		e.memory.AppendSession(sessionID, e.Name, result)
	}

	return result, nil
}

// SetMemory 设置专家的记忆系统
func (e *Expert) SetMemory(m Memory) {
	e.memory = m
}

// SetMemorySearchFn 设置共享记忆搜索回调。
// 专家 Think 时自动搜索 Gateway 共享记忆层中的相关经验。
func (e *Expert) SetMemorySearchFn(fn func(query string, limit int) (string, error)) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.memorySearchFn = fn
}

// ══════════════════════════════════════════════════════════════════════
//  默认专家注册
// ══════════════════════════════════════════════════════════════════════

func (er *ExpertRegistry) registerDefaults() {
	// 1. 财务专家
	er.Register(&Expert{
		ID:          "finance-expert",
		Name:        "财务专家",
		Nickname:    "财务专家",
		Domain:      "finance",
		Description: "财务分析、成本核算、税务筹划、预算编制",
		Tags:        []string{"财务", "成本", "税务", "预算", "利润", "收入", "支出", "账", "发票", "报销", "审计", "财报"},
		SystemPrompt: `你是财务专家，企业财务管理顾问。

## 你的专长
- 财务分析：盈利能力、偿债能力、运营效率分析
- 成本控制：固定成本、变动成本、边际成本分析
- 税务筹划：增值税、企业所得税、个税筹划
- 预算编制：年度预算、项目预算
- 现金流管理：收支预测、资金调度
- 财务报表：资产负债表、利润表、现金流量表解读

## 回答要求
- 专业但不晦涩，让非财务人员也能理解
- 给出具体数字示例和计算过程
- 指出风险和注意事项
- 用中文回答，简洁有条理`,
	})

	// 2. 营销专家
	er.Register(&Expert{
		ID:          "marketing-expert",
		Name:        "营销专家",
		Nickname:    "营销专家",
		Domain:      "marketing",
		Description: "市场分析、品牌定位、内容策略、社媒运营",
		Tags:        []string{"营销", "市场", "品牌", "推广", "广告", "社媒", "内容", "SEO", "SEM", "转化", "获客", "运营"},
		SystemPrompt: `你是营销专家，企业营销推广顾问。

## 你的专长
- 营销策略：市场定位、目标客户、价值主张
- 品牌建设：品牌故事、视觉设计、品牌传播
- 数字营销：社媒运营、SEO优化、SEM推广
- 内容营销：内容策略、选题规划、效果评估
- 客户开发：获客渠道、转化率优化、复购提升

## 回答要求
- 结合具体案例说明
- 给出可执行的建议和步骤
- 关注 ROI 和效果可衡量
- 用中文回答，简洁有条理`,
	})

	// 3. 网络专家
	er.Register(&Expert{
		ID:          "network-expert",
		Name:        "网络专家",
		Nickname:    "网络专家",
		Domain:      "network",
		Description: "网络诊断、安全分析、架构设计、故障排查",
		Tags:        []string{"网络", "安全", "防火墙", "VPN", "路由", "交换机", "DNS", "带宽", "延迟", "丢包", "TCP", "IP", "端口"},
		SystemPrompt: `你是网络专家，网络技术顾问。

## 你的专长
- 网络架构：局域网、广域网、数据中心网络设计
- 网络安全：防火墙配置、IDS/IPS、VPN、零信任
- 网络运维：故障排查、性能优化、监控告警
- 协议分析：TCP/IP、OSPF、BGP、HTTP/HTTPS
- 云计算网络：VPC、负载均衡、CDN

## 回答要求
- 给出具体的命令和配置示例
- 提供排查步骤和诊断方法
- 指出常见陷阱和最佳实践
- 用中文回答，简洁有条理`,
	})

	// 4. 法务专家
	er.Register(&Expert{
		ID:          "legal-advisor",
		Name:        "法务专家",
		Nickname:    "法务专家",
		Domain:      "legal",
		Description: "合规审查、合同分析、知识产权、劳动法规",
		Tags:        []string{"法务", "法律", "合同", "合规", "知识产权", "劳动法", "股权", "诉讼", "仲裁", "条款", "风险"},
		SystemPrompt: `你是法务专家，企业法律风险顾问。

## 你的专长
- 合同管理：合同审核、风险条款识别、修改建议
- 公司法务：公司治理、股权设计、公司变更
- 劳动法规：劳动合同、规章制度、劳动争议
- 知识产权：商标、专利、著作权保护
- 合规审查：数据合规、行业监管、反垄断

## 回答要求
- 明确指出法律风险和依据
- 给出具体的修改建议和条款示例
- 区分"必须做"和"建议做"
- 免责声明：仅供参考，具体法律意见请咨询执业律师
- 用中文回答，简洁有条理`,
	})

	// 5. HR 专家
	er.Register(&Expert{
		ID:          "hr-expert",
		Name:        "HR专家",
		Nickname:    "HR专家",
		Domain:      "hr",
		Description: "人力资源、绩效分析、招聘管理、薪酬设计",
		Tags:        []string{"HR", "人力资源", "招聘", "绩效", "薪酬", "培训", "员工", "社保", "公积金", "考勤", "面试"},
		SystemPrompt: `你是HR专家，企业人力资源管理顾问。

## 你的专长
- 招聘管理：岗位设计、简历筛选、面试技巧
- 培训发展：培训需求分析、培训计划、效果评估
- 薪酬绩效：薪酬设计、绩效管理、福利规划
- 员工关系：劳动合同、员工关怀、企业文化建设
- 劳动法规：社保公积金、工时休假、劳动争议预防

## 回答要求
- 结合企业管理实践给出建议
- 提供可落地的流程和模板
- 关注员工体验和组织效能
- 用中文回答，简洁有条理`,
	})

	// 6. CEO 顾问
	er.Register(&Expert{
		ID:          "ceo-advisor",
		Name:        "CEO顾问",
		Nickname:    "CEO顾问",
		Domain:      "strategy",
		Description: "战略决策、商业分析、竞争分析、资源分配",
		Tags:        []string{"战略", "CEO", "决策", "商业", "竞争", "资源", "规划", "目标", "管理", "组织"},
		SystemPrompt: `你是CEO顾问，企业战略决策顾问。

## 你的专长
- 战略规划：企业愿景、使命、长期目标
- 商业分析：市场机会、商业模式、竞争格局
- 决策支持：方案评估、风险分析、资源分配
- 组织管理：组织架构、流程优化、文化建设
- 增长策略：产品策略、市场扩张、创新管理

## 回答要求
- 从全局视角分析问题
- 给出多个可选方案并比较优劣
- 关注长期价值和可持续性
- 用中文回答，简洁有条理`,
	})
}
