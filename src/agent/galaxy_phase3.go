// Package agent — 银河计划 Phase 3: 自主进化
//
// 四大功能:
// 1. 自主学习优化 — 任务后反思 + 知识蒸馏 + 自我改进
// 2. 创新探索机制 — 好奇心驱动 + 跨域实验 + 知识发现
// 3. 多领域扩展 — 跨专家协作 + 多域任务分解 + 知识迁移
// 4. 自组织生态 — 动态角色分配 + 同行评审 + 自动委派
//
// SPEC-GALAXY-003 v1.0

package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/composer"
)

// ══════════════════════════════════════════════════════════════════════
//  1. 自主学习优化 — SelfLearningEngine
// ══════════════════════════════════════════════════════════════════════

// SelfLearningEngine 自主学习引擎
// 每次任务执行后自动反思、提取知识、优化行为
type SelfLearningEngine struct {
	agent   *Agent
	memory  Memory
	llm     *composer.LLMClient
	mu      sync.RWMutex

	// 学习统计
	totalTasks     int
	successTasks   int
	knowledgeCount int
	lastReflect    time.Time

	// 反思间隔（每 N 次任务反思一次）
	reflectInterval int
}

// NewSelfLearningEngine 创建自主学习引擎
func NewSelfLearningEngine(agent *Agent, memory Memory, llm *composer.LLMClient) *SelfLearningEngine {
	return &SelfLearningEngine{
		agent:           agent,
		memory:          memory,
		llm:             llm,
		reflectInterval: 5, // 每 5 次任务反思一次
	}
}

// SaveKnowledge 保存知识并同步到 Gateway（包装 agent.SaveKnowledge）。
func (sle *SelfLearningEngine) SaveKnowledge(topic, content string) error {
	if sle.agent != nil {
		return sle.agent.SaveKnowledge(topic, content)
	}
	return sle.memory.SaveKnowledge(topic, content)
}

// OnTaskCompleted 任务完成回调 — 自动学习
func (sle *SelfLearningEngine) OnTaskCompleted(task string, plan []PlanStep, result string, success bool, logFn func(source, action, detail string, llmCalled, success bool)) {
	sle.mu.Lock()
	sle.totalTasks++
	if success {
		sle.successTasks++
	}
	shouldReflect := sle.totalTasks%sle.reflectInterval == 0
	sle.mu.Unlock()

	// Step 1: 提取经验（立即，不调 LLM）
	sle.extractLesson(task, plan, result, success)
	if logFn != nil {
		detail := fmt.Sprintf("任务: %s → %s", truncateString(task, 80), map[bool]string{true: "✅ 成功", false: "❌ 失败"}[success])
		logFn("self_learning", "extract_lesson", detail, false, success)
	}

	// Step 2: 知识蒸馏（成功任务，调 LLM）
	if success && len(result) > 50 {
		sle.distillKnowledge(task, result, logFn)
	}

	// Step 3: 定期反思（每 N 次任务，调 LLM）
	if shouldReflect {
		sle.reflect(logFn)
	}
}

// extractLesson 从单次任务中提取经验教训
func (sle *SelfLearningEngine) extractLesson(task string, plan []PlanStep, result string, success bool) {
	if sle.memory == nil {
		return
	}

	// 构建经验总结
	var learned string
	if success {
		// 成功经验：提取关键步骤和技巧
		keySteps := make([]string, 0)
		for _, step := range plan {
			if step.Status == "success" && step.Result != "" {
				summary := step.Result
				if len(summary) > 200 {
					summary = summary[:200] + "..."
				}
				keySteps = append(keySteps, fmt.Sprintf("[%s] %s", step.Command, summary))
			}
		}
		if len(keySteps) > 0 {
			learned = "成功关键: " + strings.Join(keySteps, "; ")
		} else {
			learned = "任务成功完成"
		}
	} else {
		// 失败经验：提取失败原因和改进建议
		failSteps := make([]string, 0)
		for _, step := range plan {
			if step.Status == "failed" {
				failSteps = append(failSteps, fmt.Sprintf("步骤%d(%s)失败: %s", step.ID, step.Command, step.Result))
			}
		}
		if len(failSteps) > 0 {
			learned = "失败原因: " + strings.Join(failSteps, "; ")
		} else {
			learned = "任务执行失败"
		}
	}

	// 保存到记忆
	taskSummary := task
	if len(taskSummary) > 200 {
		taskSummary = taskSummary[:200] + "..."
	}
	resultSummary := result
	if len(resultSummary) > 500 {
		resultSummary = resultSummary[:500] + "..."
	}

	sle.memory.SaveEpisode(taskSummary, resultSummary, success, learned)
}

// distillKnowledge 知识蒸馏 — 从成功经验中提取可复用的知识
func (sle *SelfLearningEngine) distillKnowledge(task, result string, logFn func(source, action, detail string, llmCalled, success bool)) {
	if sle.llm == nil || sle.memory == nil {
		return
	}

	// 获取 Phase 3 管理器 — 检查 observe 模式
	pm := sle.getPhase3Manager()
	if pm != nil && !pm.shouldUseLLM() {
		if logFn != nil {
			logFn("self_learning", "distill_knowledge", fmt.Sprintf("[observe 模式跳过] 任务: %s", truncateString(task, 60)), false, true)
		}
		return
	}

	// 用 LLM 提取可复用的知识
	prompt := fmt.Sprintf(`你是一个知识蒸馏引擎。从以下任务执行结果中，提取可复用的知识。

任务: %s
结果: %s

请提取:
1. 核心知识点（1-3条，每条一句话）
2. 适用场景（什么情况下可以用这个知识）
3. 注意事项（容易踩的坑）

输出格式:
## 知识点
- ...

## 适用场景
- ...

## 注意事项
- ...`, task, result)

	_, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	knowledge, err := sle.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是知识蒸馏引擎，从执行结果中提取可复用的知识。"},
		{Role: "user", Content: prompt},
	}, 1024)
	if err != nil || len(knowledge) < 20 {
		if logFn != nil {
			logFn("self_learning", "distill_knowledge", fmt.Sprintf("LLM 返回为空或出错: %v", err), true, false)
		}
		return
	}

	// 提取主题作为知识标题
	topic := task
	if len(topic) > 60 {
		topic = topic[:60] + "..."
	}

	sle.SaveKnowledge(topic, knowledge)

	sle.mu.Lock()
	sle.knowledgeCount++
	sle.mu.Unlock()

	if logFn != nil {
		logFn("self_learning", "distill_knowledge", fmt.Sprintf("已提取知识: %s", truncateString(topic, 60)), true, true)
	}
}

// reflect 定期反思 — 回顾近期表现，优化行为策略
func (sle *SelfLearningEngine) reflect(logFn func(source, action, detail string, llmCalled, success bool)) {
	if sle.llm == nil || sle.memory == nil {
		return
	}

	// 获取 Phase 3 管理器 — 检查 observe 模式
	pm := sle.getPhase3Manager()
	if pm != nil && !pm.shouldUseLLM() {
		if logFn != nil {
			logFn("self_learning", "reflect", "[observe 模式跳过] 自我反思", false, true)
		}
		return
	}

	sle.mu.Lock()
	sle.lastReflect = time.Now()
	total := sle.totalTasks
	success := sle.successTasks
	knowledge := sle.knowledgeCount
	sle.mu.Unlock()

	// 获取近期经验
	recent, err := sle.memory.ListRecentEpisodes(10)
	if err != nil || len(recent) == 0 {
		return
	}

	// 构建反思报告
	var episodes []string
	for _, ep := range recent {
		icon := "✅"
		if !ep.Success {
			icon = "❌"
		}
		episodes = append(episodes, fmt.Sprintf("%s %s: %s", icon, ep.Date, ep.Task))
	}

	prompt := fmt.Sprintf(`你是一个自我反思引擎。回顾近期表现，进行自我改进分析。

## 近期统计
- 总任务数: %d
- 成功率: %.0f%%
- 已提取知识: %d 条

## 近期任务
%s

请分析:
1. 哪些类型的任务做得好？为什么？
2. 哪些类型的任务容易失败？如何改进？
3. 有什么模式或规律值得注意？
4. 下一步应该重点提升什么能力？

输出格式:
## 优势分析
- ...

## 改进方向
- ...

## 行动计划
- ...`, total, float64(success)/float64(total)*100, knowledge, strings.Join(episodes, "\n"))

	_, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if logFn != nil {
		logFn("self_learning", "reflect", fmt.Sprintf("第 %d 次反思 (成功率 %.0f%%)", total, float64(success)/float64(total)*100), true, true)
	}

	reflection, err := sle.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是自我反思引擎，帮助 AI Agent 持续改进。"},
		{Role: "user", Content: prompt},
	}, 1024)
	if err != nil || len(reflection) < 20 {
		if logFn != nil {
			logFn("self_learning", "reflect", fmt.Sprintf("LLM 返回为空或出错: %v", err), true, false)
		}
		return
	}

	// 保存反思到知识库
	sle.SaveKnowledge(fmt.Sprintf("自我反思 #%d", total), reflection)
}

// getPhase3Manager 向上查找所属的 GalaxyPhase3Manager
func (sle *SelfLearningEngine) getPhase3Manager() *GalaxyPhase3Manager {
	// SelfLearningEngine 不直接持有 pm 引用，从 agent 反向查找
	// 这里先通过 agent 的 Phase3 字段获取
	if sle.agent != nil && sle.agent.Phase3 != nil {
		return sle.agent.Phase3
	}
	return nil
}

// GetStats 获取学习统计
func (sle *SelfLearningEngine) GetStats() map[string]interface{} {
	sle.mu.RLock()
	defer sle.mu.RUnlock()

	return map[string]interface{}{
		"total_tasks":      sle.totalTasks,
		"success_rate":     fmt.Sprintf("%.1f%%", float64(sle.successTasks)/float64(sle.totalTasks)*100),
		"knowledge_count":  sle.knowledgeCount,
		"last_reflect":     sle.lastReflect.Format(time.RFC3339),
		"reflect_interval": sle.reflectInterval,
	}
}

// ══════════════════════════════════════════════════════════════════════
//  2. 创新探索机制 — InnovationEngine
// ══════════════════════════════════════════════════════════════════════

// InnovationEngine 创新探索引擎
// 好奇心驱动：发现知识盲区 → 设计实验 → 执行验证 → 记录发现
type InnovationEngine struct {
	agent   *Agent
	memory  Memory
	llm     *composer.LLMClient
	mu      sync.RWMutex

	// 探索状态
	explorationCount int
	discoveryCount   int
	lastExplore      time.Time

	// 探索间隔（每 N 次任务后探索一次）
	exploreInterval int

	// 已探索过的领域（避免重复）
	exploredTopics map[string]time.Time
}

// NewInnovationEngine 创建创新探索引擎
func NewInnovationEngine(agent *Agent, memory Memory, llm *composer.LLMClient) *InnovationEngine {
	return &InnovationEngine{
		agent:           agent,
		memory:          memory,
		llm:             llm,
		exploreInterval: 10, // 每 10 次任务探索一次
		exploredTopics:  make(map[string]time.Time),
	}
}

// OnTaskCompleted 任务完成回调 — 触发探索
func (ie *InnovationEngine) OnTaskCompleted(task string, success bool, logFn func(source, action, detail string, llmCalled, success bool)) {
	ie.mu.Lock()
	ie.explorationCount++
	shouldExplore := ie.explorationCount%ie.exploreInterval == 0
	ie.mu.Unlock()

	if shouldExplore {
		ie.explore(logFn)
	}
}

// explore 执行一次探索
func (ie *InnovationEngine) explore(logFn func(source, action, detail string, llmCalled, success bool)) {
	if ie.llm == nil || ie.memory == nil {
		return
	}

	// 检查 observe 模式
	pm := ie.getPhase3Manager()
	if pm != nil && !pm.shouldUseLLM() {
		if logFn != nil {
			logFn("innovation", "explore", "[observe 模式跳过] 探索", false, true)
		}
		return
	}

	ie.mu.Lock()
	ie.lastExplore = time.Now()
	ie.mu.Unlock()

	// Step 1: 发现知识盲区
	gap := ie.findKnowledgeGap()
	if gap == "" {
		return
	}

	if logFn != nil {
		logFn("innovation", "explore", fmt.Sprintf("发现知识盲区: %s", truncateString(gap, 60)), false, true)
	}

	// Step 2: 设计探索实验
	experiment := ie.designExperiment(gap)
	if experiment == "" {
		return
	}

	// Step 3: 执行实验（通过 Agent 的 Think 能力）
	_, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	result, err := ie.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是一个探索实验引擎。执行以下探索任务，记录发现。"},
		{Role: "user", Content: experiment},
	}, 2048)
	if err != nil || len(result) < 20 {
		if logFn != nil {
			logFn("innovation", "explore", fmt.Sprintf("LLM 探索实验失败: %v", err), true, false)
		}
		return
	}

	// Step 4: 记录发现
	discovery := fmt.Sprintf("## 探索主题\n%s\n\n## 实验设计\n%s\n\n## 发现\n%s", gap, experiment, result)
	if ie.agent != nil {
		ie.agent.SaveKnowledge(fmt.Sprintf("探索发现: %s", gap), discovery)
	} else {
		ie.memory.SaveKnowledge(fmt.Sprintf("探索发现: %s", gap), discovery)
	}

	ie.mu.Lock()
	ie.discoveryCount++
	ie.exploredTopics[gap] = time.Now()
	ie.mu.Unlock()

	if logFn != nil {
		logFn("innovation", "explore", fmt.Sprintf("探索完成: %s → 发现新知识", truncateString(gap, 60)), true, true)
	}
}

// getPhase3Manager 向上查找所属的 GalaxyPhase3Manager
func (ie *InnovationEngine) getPhase3Manager() *GalaxyPhase3Manager {
	if ie.agent != nil && ie.agent.Phase3 != nil {
		return ie.agent.Phase3
	}
	return nil
}

// findKnowledgeGap 发现知识盲区
func (ie *InnovationEngine) findKnowledgeGap() string {
	if ie.llm == nil {
		return ""
	}

	// 获取已有知识主题
	knowledge, err := ie.memory.SearchKnowledge("", 20)
	if err != nil {
		return ""
	}

	var topics []string
	for _, k := range knowledge {
		topics = append(topics, k.Topic)
	}

	// 获取已探索过的领域
	ie.mu.RLock()
	explored := make([]string, 0, len(ie.exploredTopics))
	for t := range ie.exploredTopics {
		explored = append(explored, t)
	}
	ie.mu.RUnlock()

	prompt := fmt.Sprintf(`你是一个知识发现引擎。分析以下已有知识，找出知识盲区。

## 已有知识
%s

## 已探索过的领域
%s

请找出 1-2 个尚未探索但有价值的知识领域。要求:
1. 与现有知识相关但不重复
2. 有实际应用价值
3. 可以通过实验验证

输出格式（只输出领域名称，每行一个）:
- 领域1
- 领域2`, strings.Join(topics, "\n"), strings.Join(explored, "\n"))

	_, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	result, err := ie.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是知识发现引擎，找出有价值的知识盲区。"},
		{Role: "user", Content: prompt},
	}, 512)
	if err != nil {
		return ""
	}

	// 提取第一个领域
	for _, line := range strings.Split(result, "\n") {
		line = strings.TrimSpace(line)
		line = strings.TrimPrefix(line, "- ")
		line = strings.TrimPrefix(line, "* ")
		if line != "" && !strings.HasPrefix(line, "##") && !strings.HasPrefix(line, "输出") {
			return line
		}
	}

	return ""
}

// designExperiment 设计探索实验
func (ie *InnovationEngine) designExperiment(gap string) string {
	if ie.llm == nil {
		return ""
	}

	prompt := fmt.Sprintf(`为以下知识领域设计一个探索实验:

领域: %s

实验要求:
1. 可以通过 LLM 思考完成（不需要外部工具）
2. 有明确的输入和输出
3. 可以验证假设
4. 时间控制在 30 秒以内

请输出实验方案（包含: 假设、方法、预期结果）`, gap)

	_, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	result, err := ie.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是实验设计引擎，设计可执行的探索实验。"},
		{Role: "user", Content: prompt},
	}, 1024)
	if err != nil {
		return ""
	}

	return result
}

// GetStats 获取探索统计
func (ie *InnovationEngine) GetStats() map[string]interface{} {
	ie.mu.RLock()
	defer ie.mu.RUnlock()

	return map[string]interface{}{
		"exploration_count": ie.explorationCount,
		"discovery_count":   ie.discoveryCount,
		"explored_topics":   len(ie.exploredTopics),
		"last_explore":      ie.lastExplore.Format(time.RFC3339),
		"explore_interval":  ie.exploreInterval,
	}
}

// ══════════════════════════════════════════════════════════════════════
//  3. 多领域扩展 — CrossDomainEngine
// ══════════════════════════════════════════════════════════════════════

// CrossDomainEngine 跨领域协作引擎
// 让多个专家协同解决复杂问题
type CrossDomainEngine struct {
	registry *ExpertRegistry
	llm      *composer.LLMClient
	mu       sync.RWMutex

	// 协作记录
	collaborations []*CollaborationRecord
	maxRecords     int
}

// CollaborationRecord 协作记录
type CollaborationRecord struct {
	ID          string    `json:"id"`
	Task        string    `json:"task"`
	Experts     []string  `json:"experts"`     // 参与的专家 ID
	Result      string    `json:"result"`
	Duration    string    `json:"duration"`
	CompletedAt time.Time `json:"completed_at"`
}

// NewCrossDomainEngine 创建跨领域协作引擎
func NewCrossDomainEngine(registry *ExpertRegistry, llm *composer.LLMClient) *CrossDomainEngine {
	return &CrossDomainEngine{
		registry:   registry,
		llm:        llm,
		maxRecords: 100,
	}
}

// DecomposeTask 分解多领域任务 — 将复杂任务拆解为多个专家子任务
func (cde *CrossDomainEngine) DecomposeTask(task string) ([]ExpertTask, error) {
	if cde.llm == nil {
		return nil, fmt.Errorf("LLM not available")
	}

	experts := cde.registry.List()
	var expertDescs []string
	for _, e := range experts {
		expertDescs = append(expertDescs, fmt.Sprintf("- %s (%s): %s", e.Name, e.ID, e.Description))
	}

	prompt := fmt.Sprintf(`你是一个任务分解引擎。将以下复杂任务分解为多个子任务，分配给最合适的专家。

## 可用专家
%s

## 任务
%s

请分析:
1. 这个任务涉及哪些领域？
2. 每个领域应该由哪位专家负责？
3. 子任务之间的依赖关系是什么？
4. 最终如何整合各专家的结果？

输出 JSON 格式:
{
  "subtasks": [
    {
      "expert_id": "专家ID",
      "task": "子任务描述",
      "depends_on": ["依赖的子任务ID"]
    }
  ],
  "integration_plan": "如何整合各专家结果"
}`, strings.Join(expertDescs, "\n"), task)

	_, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := cde.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是任务分解引擎，将复杂任务分配给最合适的专家。"},
		{Role: "user", Content: prompt},
	}, 2048)
	if err != nil {
		return nil, fmt.Errorf("decompose failed: %w", err)
	}

	// 解析 JSON
	jsonStr := extractJSON(result)
	if jsonStr == "" {
		return nil, fmt.Errorf("no valid JSON in response")
	}

	var parsed struct {
		Subtasks []struct {
			ExpertID  string   `json:"expert_id"`
			Task      string   `json:"task"`
			DependsOn []string `json:"depends_on"`
		} `json:"subtasks"`
		IntegrationPlan string `json:"integration_plan"`
	}
	if err := json.Unmarshal([]byte(jsonStr), &parsed); err != nil {
		return nil, fmt.Errorf("parse subtasks failed: %w", err)
	}

	var tasks []ExpertTask
	for i, st := range parsed.Subtasks {
		tasks = append(tasks, ExpertTask{
			ID:        fmt.Sprintf("sub-%d", i+1),
			ExpertID:  st.ExpertID,
			Task:      st.Task,
			DependsOn: st.DependsOn,
		})
	}

	return tasks, nil
}

// ExecuteCollaboration 执行多专家协作
func (cde *CrossDomainEngine) ExecuteCollaboration(task string, tasks []ExpertTask) (*CollaborationRecord, error) {
	startTime := time.Now()
	record := &CollaborationRecord{
		ID:   fmt.Sprintf("collab-%d", time.Now().UnixNano()),
		Task: task,
	}

	// 按依赖顺序执行
	completed := make(map[string]string) // taskID -> result
	var results []string

	for _, t := range tasks {
		expert := cde.registry.Get(t.ExpertID)
		if expert == nil {
			results = append(results, fmt.Sprintf("[%s] 专家 %s 未找到", t.ID, t.ExpertID))
			continue
		}

		// 检查依赖是否完成
		allDepsMet := true
		for _, dep := range t.DependsOn {
			if _, ok := completed[dep]; !ok {
				allDepsMet = false
				break
			}
		}
		if !allDepsMet {
			results = append(results, fmt.Sprintf("[%s] 依赖未满足，跳过", t.ID))
			continue
		}

		// 构建上下文（包含依赖结果）
		contextTask := t.Task
		if len(t.DependsOn) > 0 {
			var depResults []string
			for _, dep := range t.DependsOn {
				if r, ok := completed[dep]; ok {
					depResults = append(depResults, fmt.Sprintf("前置任务 %s 的结果:\n%s", dep, r))
				}
			}
			if len(depResults) > 0 {
				contextTask = fmt.Sprintf("%s\n\n前置上下文:\n%s", t.Task, strings.Join(depResults, "\n\n"))
			}
		}

		// 专家执行
		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		defer cancel()

		result, err := expert.Think(ctx, contextTask, "collab-"+t.ID)
		if err != nil {
			results = append(results, fmt.Sprintf("[%s] %s 执行失败: %v", t.ID, expert.Name, err))
			continue
		}

		completed[t.ID] = result
		record.Experts = append(record.Experts, expert.ID)
		results = append(results, fmt.Sprintf("## %s (%s)\n%s", expert.Name, t.ID, result))
	}

	// 整合结果
	record.Result = strings.Join(results, "\n\n---\n\n")
	record.Duration = time.Since(startTime).Round(time.Second).String()
	record.CompletedAt = time.Now()

	// 保存记录
	cde.mu.Lock()
	cde.collaborations = append(cde.collaborations, record)
	if len(cde.collaborations) > cde.maxRecords {
		cde.collaborations = cde.collaborations[len(cde.collaborations)-cde.maxRecords:]
	}
	cde.mu.Unlock()

	return record, nil
}

// GetStats 获取协作统计
func (cde *CrossDomainEngine) GetStats() map[string]interface{} {
	cde.mu.RLock()
	defer cde.mu.RUnlock()

	expertUsage := make(map[string]int)
	for _, rec := range cde.collaborations {
		for _, e := range rec.Experts {
			expertUsage[e]++
		}
	}

	return map[string]interface{}{
		"total_collaborations": len(cde.collaborations),
		"expert_usage":         expertUsage,
	}
}

// ExpertTask 专家子任务
type ExpertTask struct {
	ID        string   `json:"id"`
	ExpertID  string   `json:"expert_id"`
	Task      string   `json:"task"`
	DependsOn []string `json:"depends_on,omitempty"`
}

// ══════════════════════════════════════════════════════════════════════
//  4. 自组织生态 — SelfOrgEngine
// ══════════════════════════════════════════════════════════════════════

// SelfOrgEngine 自组织生态引擎
// 动态角色分配 + 同行评审 + 自动委派
type SelfOrgEngine struct {
	registry *ExpertRegistry
	llm      *composer.LLMClient
	mu       sync.RWMutex

	// 角色分配
	roles map[string]*RoleAssignment

	// 评审记录
	reviews []*PeerReview

	// 委派规则
	delegationRules []DelegationRule
}

// RoleAssignment 角色分配
type RoleAssignment struct {
	ExpertID  string    `json:"expert_id"`
	Role      string    `json:"role"`      // "lead" | "reviewer" | "contributor" | "observer"
	TaskID    string    `json:"task_id"`
	AssignedAt time.Time `json:"assigned_at"`
	Active    bool      `json:"active"`
}

// PeerReview 同行评审
type PeerReview struct {
	ID          string    `json:"id"`
	TaskID      string    `json:"task_id"`
	ReviewerID  string    `json:"reviewer_id"`
	AuthorID    string    `json:"author_id"`
	Content     string    `json:"content"`
	Score       int       `json:"score"` // 1-5
	Comments    string    `json:"comments"`
	ReviewedAt  time.Time `json:"reviewed_at"`
}

// DelegationRule 委派规则
type DelegationRule struct {
	ID          string   `json:"id"`
	Condition   string   `json:"condition"`   // 触发条件描述
	TargetRole  string   `json:"target_role"` // 委派给什么角色
	Priority    int      `json:"priority"`    // 优先级
	Description string   `json:"description"`
}

// NewSelfOrgEngine 创建自组织生态引擎
func NewSelfOrgEngine(registry *ExpertRegistry, llm *composer.LLMClient) *SelfOrgEngine {
	return &SelfOrgEngine{
		registry: registry,
		llm:      llm,
		roles:    make(map[string]*RoleAssignment),
		reviews:  make([]*PeerReview, 0, 100),
		delegationRules: []DelegationRule{
			{
				ID:          "rule-1",
				Condition:   "任务涉及多个领域",
				TargetRole:  "lead",
				Priority:    1,
				Description: "多领域任务需要指定主导专家",
			},
			{
				ID:          "rule-2",
				Condition:   "任务结果需要质量验证",
				TargetRole:  "reviewer",
				Priority:    2,
				Description: "重要任务需要同行评审",
			},
			{
				ID:          "rule-3",
				Condition:   "专家负载过高",
				TargetRole:  "contributor",
				Priority:    3,
				Description: "负载均衡：委派给负载较低的专家",
			},
		},
	}
}

// AssignRoles 为任务动态分配角色
func (soe *SelfOrgEngine) AssignRoles(task string, experts []string) ([]RoleAssignment, error) {
	if soe.llm == nil {
		return nil, fmt.Errorf("LLM not available")
	}

	var expertInfo []string
	for _, id := range experts {
		if e := soe.registry.Get(id); e != nil {
			expertInfo = append(expertInfo, fmt.Sprintf("- %s (%s): %s", e.Name, e.ID, e.Description))
		}
	}

	prompt := fmt.Sprintf(`你是一个角色分配引擎。为以下任务和专家团队分配角色。

## 任务
%s

## 可用专家
%s

## 角色说明
- lead: 主导专家，负责整体方案和最终决策
- reviewer: 评审专家，负责质量审核
- contributor: 贡献专家，负责具体执行
- observer: 观察专家，学习但不直接参与

请为每个专家分配最合适的角色，并说明理由。

输出 JSON 格式:
{
  "assignments": [
    {
      "expert_id": "专家ID",
      "role": "lead|reviewer|contributor|observer",
      "reason": "分配理由"
    }
  ]
}`, task, strings.Join(expertInfo, "\n"))

	_, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	result, err := soe.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是角色分配引擎，为专家团队分配最优角色。"},
		{Role: "user", Content: prompt},
	}, 1024)
	if err != nil {
		return nil, fmt.Errorf("role assignment failed: %w", err)
	}

	jsonStr := extractJSON(result)
	if jsonStr == "" {
		return nil, fmt.Errorf("no valid JSON in response")
	}

	var parsed struct {
		Assignments []struct {
			ExpertID string `json:"expert_id"`
			Role     string `json:"role"`
			Reason   string `json:"reason"`
		} `json:"assignments"`
	}
	if err := json.Unmarshal([]byte(jsonStr), &parsed); err != nil {
		return nil, fmt.Errorf("parse assignments failed: %w", err)
	}

	soe.mu.Lock()
	var assignments []RoleAssignment
	for _, a := range parsed.Assignments {
		ra := RoleAssignment{
			ExpertID:   a.ExpertID,
			Role:       a.Role,
			TaskID:     task,
			AssignedAt: time.Now(),
			Active:     true,
		}
		soe.roles[a.ExpertID] = &ra
		assignments = append(assignments, ra)
	}
	soe.mu.Unlock()

	return assignments, nil
}

// PeerReview 执行同行评审
func (soe *SelfOrgEngine) PeerReview(taskID, authorID, content string) (*PeerReview, error) {
	if soe.llm == nil {
		return nil, fmt.Errorf("LLM not available")
	}

	// 找一位不在作者列表中的专家做评审
	reviewer := soe.findReviewer(authorID)
	if reviewer == nil {
		return nil, fmt.Errorf("no reviewer available")
	}

	prompt := fmt.Sprintf(`你是一个同行评审引擎。评审以下工作成果。

## 作者
%s

## 工作内容
%s

请从以下维度评审:
1. 准确性（1-5分）
2. 完整性（1-5分）
3. 实用性（1-5分）
4. 创新性（1-5分）
5. 总体评分（1-5分）

输出 JSON 格式:
{
  "score": 总体评分,
  "accuracy": 准确性评分,
  "completeness": 完整性评分,
  "practicality": 实用性评分,
  "innovation": 创新性评分,
  "strengths": ["优点1", "优点2"],
  "improvements": ["改进建议1", "改进建议2"],
  "summary": "评审总结"
}`, authorID, content)

	_, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	result, err := soe.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是同行评审引擎，提供建设性的评审意见。"},
		{Role: "user", Content: prompt},
	}, 1024)
	if err != nil {
		return nil, fmt.Errorf("review failed: %w", err)
	}

	jsonStr := extractJSON(result)
	if jsonStr == "" {
		return nil, fmt.Errorf("no valid JSON in response")
	}

	var parsed struct {
		Score        int      `json:"score"`
		Accuracy     int      `json:"accuracy"`
		Completeness int      `json:"completeness"`
		Practicality int      `json:"practicality"`
		Innovation   int      `json:"innovation"`
		Strengths    []string `json:"strengths"`
		Improvements []string `json:"improvements"`
		Summary      string   `json:"summary"`
	}
	if err := json.Unmarshal([]byte(jsonStr), &parsed); err != nil {
		return nil, fmt.Errorf("parse review failed: %w", err)
	}

	review := &PeerReview{
		ID:         fmt.Sprintf("review-%d", time.Now().UnixNano()),
		TaskID:     taskID,
		ReviewerID: reviewer.ID,
		AuthorID:   authorID,
		Content:    content,
		Score:      parsed.Score,
		Comments:   fmt.Sprintf("准确性:%d 完整性:%d 实用性:%d 创新性:%d\n优点: %s\n改进: %s\n总结: %s",
			parsed.Accuracy, parsed.Completeness, parsed.Practicality, parsed.Innovation,
			strings.Join(parsed.Strengths, "; "),
			strings.Join(parsed.Improvements, "; "),
			parsed.Summary),
		ReviewedAt: time.Now(),
	}

	soe.mu.Lock()
	soe.reviews = append(soe.reviews, review)
	if len(soe.reviews) > 100 {
		soe.reviews = soe.reviews[len(soe.reviews)-100:]
	}
	soe.mu.Unlock()

	return review, nil
}

// AutoDelegate 自动委派 — 根据规则将任务委派给最合适的专家
func (soe *SelfOrgEngine) AutoDelegate(task string) (string, error) {
	if soe.llm == nil {
		return "", fmt.Errorf("LLM not available")
	}

	experts := soe.registry.List()
	var expertDescs []string
	for _, e := range experts {
		expertDescs = append(expertDescs, fmt.Sprintf("- %s (%s): %s [标签: %s]",
			e.Name, e.ID, e.Description, strings.Join(e.Tags, ", ")))
	}

	prompt := fmt.Sprintf(`你是一个任务委派引擎。将以下任务委派给最合适的专家。

## 可用专家
%s

## 任务
%s

请分析任务内容，选择最合适的 1-2 位专家，并说明理由。

输出 JSON 格式:
{
  "primary_expert": {
    "expert_id": "主专家ID",
    "reason": "选择理由"
  },
  "secondary_expert": {
    "expert_id": "备选专家ID",
    "reason": "选择理由"
  },
  "delegation_plan": "委派方案说明"
}`, strings.Join(expertDescs, "\n"), task)

	_, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	result, err := soe.llm.Chat([]composer.ChatMessage{
		{Role: "system", Content: "你是任务委派引擎，将任务委派给最合适的专家。"},
		{Role: "user", Content: prompt},
	}, 1024)
	if err != nil {
		return "", fmt.Errorf("delegation failed: %w", err)
	}

	jsonStr := extractJSON(result)
	if jsonStr == "" {
		return "", fmt.Errorf("no valid JSON in response")
	}

	return jsonStr, nil
}

// findReviewer 找一位不在作者列表中的专家做评审
func (soe *SelfOrgEngine) findReviewer(authorID string) *Expert {
	experts := soe.registry.List()
	// 随机选一个不是作者的专家
	var candidates []*Expert
	for _, e := range experts {
		if e.ID != authorID {
			candidates = append(candidates, e)
		}
	}
	if len(candidates) == 0 {
		return nil
	}
	return candidates[rand.Intn(len(candidates))]
}

// GetStats 获取自组织统计
func (soe *SelfOrgEngine) GetStats() map[string]interface{} {
	soe.mu.RLock()
	defer soe.mu.RUnlock()

	roleCount := make(map[string]int)
	for _, ra := range soe.roles {
		if ra.Active {
			roleCount[ra.Role]++
		}
	}

	avgScore := 0.0
	if len(soe.reviews) > 0 {
		total := 0
		for _, r := range soe.reviews {
			total += r.Score
		}
		avgScore = float64(total) / float64(len(soe.reviews))
	}

	return map[string]interface{}{
		"active_roles":      roleCount,
		"total_reviews":     len(soe.reviews),
		"average_score":     fmt.Sprintf("%.1f", avgScore),
		"delegation_rules":  len(soe.delegationRules),
	}
}

// ══════════════════════════════════════════════════════════════════════
//  Phase 3 统一管理器 — GalaxyPhase3Manager
// ══════════════════════════════════════════════════════════════════════

// GalaxyPhase3Manager 银河计划 Phase 3 统一管理器
// Phase3Mode 控制 Phase 3 引擎的运行模式
type Phase3Mode string

const (
	Phase3ModeObserve Phase3Mode = "observe" // 仅记录日志，不调用 LLM
	Phase3ModeActive  Phase3Mode = "active"  // 正常执行（含 LLM 调用）
)

// Phase3Event 一条 Phase 3 操作日志
type Phase3Event struct {
	Time      string `json:"time"`
	Source    string `json:"source"`    // self_learning / innovation / cross_domain / self_org
	Action    string `json:"action"`    // extract_lesson / distill_knowledge / reflect / explore / decompose / review / delegate
	Detail    string `json:"detail"`    // 具体描述（截断到 200 字）
	LLMCalled bool   `json:"llm_called"` // 是否调用了 LLM
	Success   bool   `json:"success"`
}

type GalaxyPhase3Manager struct {
	SelfLearning *SelfLearningEngine
	Innovation   *InnovationEngine
	CrossDomain  *CrossDomainEngine
	SelfOrg      *SelfOrgEngine
	mu           sync.RWMutex

	// 运行模式
	mode Phase3Mode

	// 日志缓冲（环形，最多 200 条）
	eventLog   []Phase3Event
	maxLogSize int

	// 事件同步回调 — 由 workercmd 注入，推送到 Gateway
	eventSyncFn func(event Phase3Event)
}


// truncateString 截断字符串到指定长度（用于日志显示）
func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

// NewGalaxyPhase3Manager 创建 Phase 3 管理器
func NewGalaxyPhase3Manager(agent *Agent, registry *ExpertRegistry, memory Memory, llm *composer.LLMClient) *GalaxyPhase3Manager {
	return &GalaxyPhase3Manager{
		SelfLearning: NewSelfLearningEngine(agent, memory, llm),
		Innovation:   NewInnovationEngine(agent, memory, llm),
		CrossDomain:  NewCrossDomainEngine(registry, llm),
		SelfOrg:      NewSelfOrgEngine(registry, llm),
		mode:         Phase3ModeActive,
		eventLog:     make([]Phase3Event, 0, 200),
		maxLogSize:   200,
	}
}

// SetMode 设置运行模式
//   - observe: 仅记录日志，不调用 LLM
//   - active:  正常执行
func (pm *GalaxyPhase3Manager) SetMode(m Phase3Mode) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	pm.mode = m
}

// GetMode 获取当前运行模式
func (pm *GalaxyPhase3Manager) GetMode() Phase3Mode {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	return pm.mode
}

// SetReflectInterval 设置反思间隔（每 N 次任务）
func (pm *GalaxyPhase3Manager) SetReflectInterval(n int) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	if pm.SelfLearning != nil {
		pm.SelfLearning.reflectInterval = n
	}
}

// SetExploreInterval 设置探索间隔（每 N 次任务）
func (pm *GalaxyPhase3Manager) SetExploreInterval(n int) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	if pm.Innovation != nil {
		pm.Innovation.exploreInterval = n
	}
}

// SetEventSyncFn 设置事件同步回调
func (pm *GalaxyPhase3Manager) SetEventSyncFn(fn func(event Phase3Event)) {
	pm.mu.Lock()
	defer pm.mu.Unlock()
	pm.eventSyncFn = fn
}

// logEvent 记录一条操作日志
func (pm *GalaxyPhase3Manager) logEvent(source, action, detail string, llmCalled, success bool) {
	evt := Phase3Event{
		Time:      time.Now().Format("15:04:05"),
		Source:    source,
		Action:    action,
		Detail:    truncateString(detail, 200),
		LLMCalled: llmCalled,
		Success:   success,
	}
	pm.mu.Lock()
	pm.eventLog = append(pm.eventLog, evt)
	if len(pm.eventLog) > pm.maxLogSize {
		pm.eventLog = pm.eventLog[len(pm.eventLog)-pm.maxLogSize:]
	}
	fn := pm.eventSyncFn
	pm.mu.Unlock()

	// 异步推送到 Gateway
	if fn != nil {
		go fn(evt)
	}
}

// GetEventLog 获取日志缓冲区
func (pm *GalaxyPhase3Manager) GetEventLog() []Phase3Event {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	out := make([]Phase3Event, len(pm.eventLog))
	copy(out, pm.eventLog)
	return out
}

// shouldUseLLM 检查是否允许调用 LLM（observe 模式下禁止）
func (pm *GalaxyPhase3Manager) shouldUseLLM() bool {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	return pm.mode == Phase3ModeActive
}

// OnTaskCompleted 任务完成回调 — 触发所有 Phase 3 引擎
func (pm *GalaxyPhase3Manager) OnTaskCompleted(task string, plan []PlanStep, result string, success bool) {
	// 日志回调闭包
	logFn := func(source, action, detail string, llmCalled, success bool) {
		pm.logEvent(source, action, detail, llmCalled, success)
	}

	// 1. 自主学习
	pm.SelfLearning.OnTaskCompleted(task, plan, result, success, logFn)

	// 2. 创新探索（每 N 次触发一次）
	pm.Innovation.OnTaskCompleted(task, success, logFn)
}

// GetStats 获取 Phase 3 整体统计
func (pm *GalaxyPhase3Manager) GetStats() map[string]interface{} {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	return map[string]interface{}{
		"self_learning": pm.SelfLearning.GetStats(),
		"innovation":    pm.Innovation.GetStats(),
		"cross_domain":  pm.CrossDomain.GetStats(),
		"self_org":      pm.SelfOrg.GetStats(),
	}
}

// GetSummary 获取 Phase 3 可读摘要
func (pm *GalaxyPhase3Manager) GetSummary() string {
	sl := pm.SelfLearning.GetStats()
	ie := pm.Innovation.GetStats()
	cd := pm.CrossDomain.GetStats()
	so := pm.SelfOrg.GetStats()

	return fmt.Sprintf(`🌌 银河计划 Phase 3: 自主进化

## 1. 自主学习优化
- 总任务数: %v
- 成功率: %v
- 已提取知识: %v 条
- 最后反思: %v

## 2. 创新探索
- 探索次数: %v
- 发现数量: %v
- 已探索领域: %v

## 3. 多领域协作
- 协作次数: %v
- 专家使用: %v

## 4. 自组织生态
- 活跃角色: %v
- 评审次数: %v
- 平均评分: %v`,
		sl["total_tasks"], sl["success_rate"], sl["knowledge_count"], sl["last_reflect"],
		ie["exploration_count"], ie["discovery_count"], ie["explored_topics"],
		cd["total_collaborations"], cd["expert_usage"],
		so["active_roles"], so["total_reviews"], so["average_score"])
}
