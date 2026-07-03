// Package gateway — TriggerEngine (银河计划 Phase 1B)
// YAML 驱动的事件触发引擎 — 感知 → 判断 → 反应
//
// 架构:
//   Layer 1: Collector   — 事件采集（系统指标 / Hall 消息 / Webhook）
//   Layer 2: Matcher     — YAML 规则匹配 + 权重评分
//   Layer 3: Responder   — 动作执行（日志/告警/广播/执行命令）
//
// SPEC-TRIGGER-001 v1.0

package gateway

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// ══════════════════════════════════════════════════════════════════════
// 数据结构
// ══════════════════════════════════════════════════════════════════════

// TriggerRule YAML 驱动的一条触发规则
type TriggerRule struct {
	ID          string            `yaml:"id" json:"id"`
	Name        string            `yaml:"name" json:"name"`
	Description string            `yaml:"description,omitempty" json:"description,omitempty"`
	Enabled     bool              `yaml:"enabled" json:"enabled"`
	EventType   string            `yaml:"event_type" json:"event_type"` // system / hall / webhook / cron
	Condition   TriggerCondition  `yaml:"condition" json:"condition"`
	Weight      int               `yaml:"weight" json:"weight"`           // 0-100，触发阈值
	Debounce    time.Duration     `yaml:"debounce" json:"debounce"`       // 防抖间隔
	Actions     []TriggerAction   `yaml:"actions" json:"actions"`
	CreatedAt   time.Time         `yaml:"created_at" json:"created_at"`
	UpdatedAt   time.Time         `yaml:"updated_at" json:"updated_at"`
	HitCount    int64             `yaml:"hit_count" json:"hit_count"`
	LastHit     time.Time         `yaml:"last_hit" json:"last_hit"`
}

// TriggerCondition 条件定义
type TriggerCondition struct {
	Field    string  `yaml:"field" json:"field"`       // e.g. cpu_percent, mem_percent, disk_percent, message_type
	Operator string  `yaml:"operator" json:"operator"` // gt / lt / eq / contains / regex
	Value    float64 `yaml:"value,omitempty" json:"value,omitempty"`
	StrValue string  `yaml:"str_value,omitempty" json:"str_value,omitempty"`
}

// TriggerAction 动作
type TriggerAction struct {
	Type    string `yaml:"type" json:"type"` // log / alert / broadcast / exec / webhook
	Target  string `yaml:"target,omitempty" json:"target,omitempty"`
	Message string `yaml:"message,omitempty" json:"message,omitempty"`
}

// TriggerEvent 采集到的事件
type TriggerEvent struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"` // system / hall / webhook
	Source    string                 `json:"source"`
	Fields    map[string]interface{} `json:"fields"`
	Raw       string                 `json:"raw,omitempty"`
	Timestamp time.Time              `json:"timestamp"`
	TraceID   string                 `json:"trace_id,omitempty"`
}

// TriggerResult 规则匹配结果
type TriggerResult struct {
	RuleID     string   `json:"rule_id"`
	EventID    string   `json:"event_id"`
	Matched    bool     `json:"matched"`
	Score      int      `json:"score"`
	Action     string   `json:"action"`
	Message    string   `json:"message"`
	Timestamp  time.Time `json:"timestamp"`
}

// TriggerEngine 触发引擎
type TriggerEngine struct {
	mu          sync.RWMutex
	rules       map[string]*TriggerRule   // id → rule
	recentHits  map[string]time.Time      // rule_id → last hit time (debounce)
	eventLog    []*TriggerResult          // 最近事件日志（环形缓冲）
	resultLog   []*TriggerResult          // 最近触发结果
	maxLogSize  int
	rulesPath   string
	isRunning   bool
	stopCh      chan struct{}
	eventCount  int64
	triggerCount int64
}

// NewTriggerEngine 创建触发引擎
func NewTriggerEngine(rulesPath string) *TriggerEngine {
	return &TriggerEngine{
		rules:       make(map[string]*TriggerRule),
		recentHits:  make(map[string]time.Time),
		eventLog:    make([]*TriggerResult, 0, 500),
		resultLog:   make([]*TriggerResult, 0, 100),
		maxLogSize:  500,
		rulesPath:   rulesPath,
		stopCh:      make(chan struct{}),
	}
}

// ══════════════════════════════════════════════════════════════════════
// 规则管理
// ══════════════════════════════════════════════════════════════════════

// LoadRules 从 YAML 文件加载规则
func (te *TriggerEngine) LoadRules() error {
	data, err := os.ReadFile(te.rulesPath)
	if err != nil {
		if os.IsNotExist(err) {
			te.ensureDefaultRules()
			return te.SaveRules()
		}
		return fmt.Errorf("读取规则文件失败: %w", err)
	}

	var rules []*TriggerRule
	if err := json.Unmarshal(data, &rules); err != nil {
		return fmt.Errorf("解析规则 JSON 失败: %w", err)
	}

	te.mu.Lock()
	defer te.mu.Unlock()
	
	// 重建索引
	te.rules = make(map[string]*TriggerRule)
	for _, rule := range rules {
		if rule.ID == "" {
			rule.ID = fmt.Sprintf("tr-%d", time.Now().UnixNano())
		}
		te.rules[rule.ID] = rule
	}
	
	// 如果没有规则，添加默认
	if len(te.rules) == 0 {
		te.ensureDefaultRules()
	}
	
	return nil
}

// SaveRules 保存规则到 JSON 文件
func (te *TriggerEngine) SaveRules() error {
	te.mu.RLock()
	rules := make([]*TriggerRule, 0, len(te.rules))
	for _, r := range te.rules {
		rules = append(rules, r)
	}
	te.mu.RUnlock()

	// 按 ID 排序输出
	sort.Slice(rules, func(i, j int) bool {
		return rules[i].ID < rules[j].ID
	})

	data, err := json.MarshalIndent(rules, "", "  ")
	if err != nil {
		return fmt.Errorf("序列化规则 JSON 失败: %w", err)
	}

	dir := filepath.Dir(te.rulesPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("创建规则目录失败: %w", err)
	}

	return os.WriteFile(te.rulesPath, data, 0644)
}

// ensureDefaultRules 确保有默认规则
func (te *TriggerEngine) ensureDefaultRules() {
	now := time.Now()
	defaultRules := []*TriggerRule{
		{
			ID:          "high-cpu",
			Name:        "CPU 高负载告警",
			Description: "CPU 使用率超过 80% 时触发告警",
			Enabled:     true,
			EventType:   "system",
			Condition:   TriggerCondition{Field: "cpu_percent", Operator: "gt", Value: 80},
			Weight:      85,
			Debounce:    300 * time.Second,
			Actions:     []TriggerAction{{Type: "log", Message: "⚠️ CPU 高负载: {value}%"}},
			CreatedAt:   now,
			UpdatedAt:   now,
		},
		{
			ID:          "high-mem",
			Name:        "内存高负载告警",
			Description: "内存使用率超过 85% 时触发告警",
			Enabled:     true,
			EventType:   "system",
			Condition:   TriggerCondition{Field: "mem_percent", Operator: "gt", Value: 85},
			Weight:      85,
			Debounce:    300 * time.Second,
			Actions:     []TriggerAction{{Type: "log", Message: "⚠️ 内存高负载: {value}%"}},
			CreatedAt:   now,
			UpdatedAt:   now,
		},
		{
			ID:          "high-disk",
			Name:        "磁盘空间告警",
			Description: "磁盘使用率超过 90% 时触发告警",
			Enabled:     true,
			EventType:   "system",
			Condition:   TriggerCondition{Field: "disk_percent", Operator: "gt", Value: 90},
			Weight:      90,
			Debounce:    600 * time.Second,
			Actions:     []TriggerAction{{Type: "alert", Message: "🔴 磁盘空间不足: {value}%"}},
			CreatedAt:   now,
			UpdatedAt:   now,
		},
		{
			ID:          "hall-urgent",
			Name:        "Hall 紧急消息",
			Description: "Hall 消息包含 @urgent / @all / @trigger 时触发",
			Enabled:     true,
			EventType:   "hall",
			Condition:   TriggerCondition{Field: "message_content", Operator: "contains", StrValue: "@trigger"},
			Weight:      100,
			Debounce:    0,
			Actions:     []TriggerAction{{Type: "broadcast", Message: "🚀 触发引擎检测到消息: {value}"}},
			CreatedAt:   now,
			UpdatedAt:   now,
		},
		{
			ID:          "system-load-warning",
			Name:        "系统负载警告",
			Description: "系统 1 分钟负载超过 CPU 核心数时触发",
			Enabled:     true,
			EventType:   "system",
			Condition:   TriggerCondition{Field: "load_1m", Operator: "gt", Value: 0},
			Weight:      75,
			Debounce:    300 * time.Second,
			Actions:     []TriggerAction{{Type: "log", Message: "⚡ 系统负载偏高: {load_1m} (核心数: {cpu_cores})"}},
			CreatedAt:   now,
			UpdatedAt:   now,
		},
		{
			ID:          "hall-message-archive",
			Name:        "Hall 消息自动归档",
			Description: "技术讨论自动提取知识点写入知识库",
			Enabled:     false,
			EventType:   "hall",
			Condition:   TriggerCondition{Field: "message_type", Operator: "eq", StrValue: "technical"},
			Weight:      50,
			Debounce:    60 * time.Second,
			Actions:     []TriggerAction{{Type: "log", Message: "📝 技术讨论归档: {value}"}},
			CreatedAt:   now,
			UpdatedAt:   now,
		},
	}
	for _, r := range defaultRules {
		te.rules[r.ID] = r
	}
}

// ══════════════════════════════════════════════════════════════════════
// 规则匹配引擎（Layer 2）
// ══════════════════════════════════════════════════════════════════════

// Evaluate 对事件进行规则匹配
func (te *TriggerEngine) Evaluate(event *TriggerEvent) []*TriggerResult {
	te.mu.RLock()
	defer te.mu.RUnlock()

	te.eventCount++
	var results []*TriggerResult

	for _, rule := range te.rules {
		if !rule.Enabled {
			continue
		}
		if rule.EventType != event.Type {
			continue
		}

		// 防抖检查
		if rule.Debounce > 0 {
			if lastHit, ok := te.recentHits[rule.ID]; ok {
				if time.Since(lastHit) < rule.Debounce {
					continue
				}
			}
		}

		// 条件匹配
		score := te.matchCondition(rule.Condition, event.Fields)
		if score >= rule.Weight {
			te.triggerCount++
			te.recentHits[rule.ID] = time.Now()
			rule.HitCount++
			rule.LastHit = time.Now()

			// 执行动作
			for _, action := range rule.Actions {
				result := &TriggerResult{
					RuleID:    rule.ID,
					EventID:   event.ID,
					Matched:   true,
					Score:     score,
					Action:    action.Type,
					Message:   te.renderMessage(action.Message, event.Fields),
					Timestamp: time.Now(),
				}
				results = append(results, result)
				te.appendResult(result)
			}
		}
	}

	return results
}

// matchCondition 匹配条件，返回匹配度分数（0-100）
func (te *TriggerEngine) matchCondition(cond TriggerCondition, fields map[string]interface{}) int {
	rawVal, ok := fields[cond.Field]
	if !ok {
		return 0
	}

	switch cond.Operator {
	case "gt":
		fval, ok := toFloat64(rawVal)
		if !ok {
			return 0
		}
		if fval > cond.Value {
			// 超出的越多分数越高
			ratio := (fval - cond.Value) / cond.Value * 100
			if ratio > 100 {
				ratio = 100
			}
			return int(60 + ratio*0.4)
		}
		return 0

	case "lt":
		fval, ok := toFloat64(rawVal)
		if !ok {
			return 0
		}
		if fval < cond.Value {
			ratio := (cond.Value - fval) / cond.Value * 100
			if ratio > 100 {
				ratio = 100
			}
			return int(60 + ratio*0.4)
		}
		return 0

	case "eq":
		switch v := rawVal.(type) {
		case float64:
			if v == cond.Value {
				return 100
			}
		case string:
			if v == cond.StrValue {
				return 100
			}
		case bool:
			if v == (cond.Value != 0) {
				return 100
			}
		}
		return 0

	case "contains":
		sval, ok := rawVal.(string)
		if !ok {
			return 0
		}
		if strings.Contains(strings.ToLower(sval), strings.ToLower(cond.StrValue)) {
			return 100
		}
		return 0

	case "regex":
		// MVP 不做完全正则，只做简单前缀/后缀匹配
		sval, ok := rawVal.(string)
		if !ok {
			return 0
		}
		pat := cond.StrValue
		if strings.HasPrefix(pat, "^") && strings.HasSuffix(pat, "$") {
			pat = strings.TrimPrefix(pat, "^")
			pat = strings.TrimSuffix(pat, "$")
			if sval == pat {
				return 100
			}
		} else if strings.HasPrefix(pat, "^") {
			pat = strings.TrimPrefix(pat, "^")
			if strings.HasPrefix(sval, pat) {
				return 100
			}
		} else if strings.HasSuffix(pat, "$") {
			pat = strings.TrimSuffix(pat, "$")
			if strings.HasSuffix(sval, pat) {
				return 100
			}
		} else if strings.Contains(sval, pat) {
			return 100
		}
		return 0
	}

	return 0
}

// renderMessage 渲染消息模板（替换 {value} 等变量）
func (te *TriggerEngine) renderMessage(tmpl string, fields map[string]interface{}) string {
	msg := tmpl
	if val, ok := fields["value"]; ok {
		msg = strings.ReplaceAll(msg, "{value}", fmt.Sprintf("%v", val))
	}
	for k, v := range fields {
		placeholder := "{" + k + "}"
		if strings.Contains(msg, placeholder) {
			msg = strings.ReplaceAll(msg, placeholder, fmt.Sprintf("%v", v))
		}
	}
	return msg
}

// appendResult 追加结果到日志（环形缓冲）
func (te *TriggerEngine) appendResult(r *TriggerResult) {
	te.eventLog = append(te.eventLog, r)
	if len(te.eventLog) > te.maxLogSize {
		te.eventLog = te.eventLog[len(te.eventLog)-te.maxLogSize:]
	}
	// 触发结果单独记录
	te.resultLog = append(te.resultLog, r)
	if len(te.resultLog) > 100 {
		te.resultLog = te.resultLog[len(te.resultLog)-100:]
	}
}

// ══════════════════════════════════════════════════════════════════════
// 事件采集（Layer 1）
// ══════════════════════════════════════════════════════════════════════

// IngestEvent 接收外部事件进行规则匹配
func (te *TriggerEngine) IngestEvent(event *TriggerEvent) []*TriggerResult {
	if event.ID == "" {
		event.ID = fmt.Sprintf("evt-%d-%d", time.Now().UnixNano(), te.eventCount)
	}
	if event.Timestamp.IsZero() {
		event.Timestamp = time.Now()
	}
	return te.Evaluate(event)
}

// IngestSystemEvent 采集系统指标事件
func (te *TriggerEngine) IngestSystemEvent(cpuPct, memPct, diskPct, load1m float64, cpuCores int) []*TriggerResult {
	event := &TriggerEvent{
		Type:   "system",
		Source: "local",
		Fields: map[string]interface{}{
			"cpu_percent":  cpuPct,
			"mem_percent":  memPct,
			"disk_percent": diskPct,
			"load_1m":      load1m,
			"cpu_cores":    float64(cpuCores),
			"value":        load1m,
		},
	}
	return te.IngestEvent(event)
}

// IngestHallEvent 采集 Hall 消息事件
func (te *TriggerEngine) IngestHallEvent(content, msgType string) []*TriggerResult {
	event := &TriggerEvent{
		Type:   "hall",
		Source: "hall",
		Fields: map[string]interface{}{
			"message_content": content,
			"message_type":    msgType,
			"value":           content,
		},
	}
	return te.IngestEvent(event)
}

// IngestWebhookEvent 采集 Webhook 事件
func (te *TriggerEngine) IngestWebhookEvent(source string, payload map[string]interface{}) []*TriggerResult {
	event := &TriggerEvent{
		Type:   "webhook",
		Source: source,
		Fields: payload,
	}
	return te.IngestEvent(event)
}

// ══════════════════════════════════════════════════════════════════════
// 统计查询
// ══════════════════════════════════════════════════════════════════════

// GetStats 获取引擎统计
func (te *TriggerEngine) GetStats() map[string]interface{} {
	te.mu.RLock()
	defer te.mu.RUnlock()

	rulesByType := make(map[string]int)
	enabledCount := 0
	for _, r := range te.rules {
		rulesByType[r.EventType]++
		if r.Enabled {
			enabledCount++
		}
	}

	return map[string]interface{}{
		"total_rules":     len(te.rules),
		"enabled_rules":   enabledCount,
		"event_count":     te.eventCount,
		"trigger_count":   te.triggerCount,
		"rules_by_type":   rulesByType,
		"recent_triggers": te.resultLog,
	}
}

// GetRules 获取所有规则
func (te *TriggerEngine) GetRules() []*TriggerRule {
	te.mu.RLock()
	defer te.mu.RUnlock()
	rules := make([]*TriggerRule, 0, len(te.rules))
	for _, r := range te.rules {
		rules = append(rules, r)
	}
	sort.Slice(rules, func(i, j int) bool {
		return rules[i].ID < rules[j].ID
	})
	return rules
}

// GetRule 获取单条规则
func (te *TriggerEngine) GetRule(id string) *TriggerRule {
	te.mu.RLock()
	defer te.mu.RUnlock()
	return te.rules[id]
}

// AddRule 添加规则
func (te *TriggerEngine) AddRule(rule *TriggerRule) error {
	te.mu.Lock()
	defer te.mu.Unlock()

	if rule.ID == "" {
		rule.ID = fmt.Sprintf("tr-%d", time.Now().UnixNano())
	}
	now := time.Now()
	rule.CreatedAt = now
	rule.UpdatedAt = now
	te.rules[rule.ID] = rule
	return te.saveRulesLocked()
}

// UpdateRule 更新规则
func (te *TriggerEngine) UpdateRule(rule *TriggerRule) error {
	te.mu.Lock()
	defer te.mu.Unlock()

	existing, ok := te.rules[rule.ID]
	if !ok {
		return fmt.Errorf("规则 %s 不存在", rule.ID)
	}
	rule.CreatedAt = existing.CreatedAt
	rule.HitCount = existing.HitCount
	rule.LastHit = existing.LastHit
	rule.UpdatedAt = time.Now()
	te.rules[rule.ID] = rule
	return te.saveRulesLocked()
}

// DeleteRule 删除规则
func (te *TriggerEngine) DeleteRule(id string) error {
	te.mu.Lock()
	defer te.mu.Unlock()

	if _, ok := te.rules[id]; !ok {
		return fmt.Errorf("规则 %s 不存在", id)
	}
	delete(te.rules, id)
	delete(te.recentHits, id)
	return te.saveRulesLocked()
}

// ToggleRule 启用/禁用规则
func (te *TriggerEngine) ToggleRule(id string) error {
	te.mu.Lock()
	defer te.mu.Unlock()

	rule, ok := te.rules[id]
	if !ok {
		return fmt.Errorf("规则 %s 不存在", id)
	}
	rule.Enabled = !rule.Enabled
	rule.UpdatedAt = time.Now()
	return te.saveRulesLocked()
}

func (te *TriggerEngine) saveRulesLocked() error {
	rules := make([]*TriggerRule, 0, len(te.rules))
	for _, r := range te.rules {
		rules = append(rules, r)
	}
	sort.Slice(rules, func(i, j int) bool {
		return rules[i].ID < rules[j].ID
	})
	data, err := json.MarshalIndent(rules, "", "  ")
	if err != nil {
		return err
	}
	dir := filepath.Dir(te.rulesPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	return os.WriteFile(te.rulesPath, data, 0644)
}

// ══════════════════════════════════════════════════════════════════════
// HTTP Handlers（Layer 3 API）
// ══════════════════════════════════════════════════════════════════════

// handleTriggerList 获取规则列表
// GET /api/v1/trigger/rules
func (g *OpcGateway) handleTriggerList(w http.ResponseWriter, r *http.Request) {
	if g.TriggerEngine == nil {
		g.sendJSON(w, map[string]interface{}{"success": true, "data": []*TriggerRule{}})
		return
	}
	rules := g.TriggerEngine.GetRules()
	g.sendJSON(w, map[string]interface{}{"success": true, "data": rules})
}

// handleTriggerGet 获取单条规则
// GET /api/v1/trigger/rules/{id}
func (g *OpcGateway) handleTriggerGet(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	if id == "" {
		http.Error(w, `{"error":"id is required"}`, http.StatusBadRequest)
		return
	}
	if g.TriggerEngine == nil {
		http.Error(w, `{"error":"TriggerEngine not initialized"}`, http.StatusInternalServerError)
		return
	}
	rule := g.TriggerEngine.GetRule(id)
	if rule == nil {
		http.Error(w, `{"error":"rule not found"}`, http.StatusNotFound)
		return
	}
	g.sendJSON(w, map[string]interface{}{"success": true, "data": rule})
}

// handleTriggerAdd 添加规则
// POST /api/v1/trigger/rules
func (g *OpcGateway) handleTriggerAdd(w http.ResponseWriter, r *http.Request) {
	if g.TriggerEngine == nil {
		http.Error(w, `{"error":"TriggerEngine not initialized"}`, http.StatusInternalServerError)
		return
	}
	var rule TriggerRule
	if err := json.NewDecoder(r.Body).Decode(&rule); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}
	if err := g.TriggerEngine.AddRule(&rule); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}
	g.sendJSON(w, map[string]interface{}{"success": true, "data": rule})
}

// handleTriggerUpdate 更新规则
// PUT /api/v1/trigger/rules
func (g *OpcGateway) handleTriggerUpdate(w http.ResponseWriter, r *http.Request) {
	if g.TriggerEngine == nil {
		http.Error(w, `{"error":"TriggerEngine not initialized"}`, http.StatusInternalServerError)
		return
	}
	var rule TriggerRule
	if err := json.NewDecoder(r.Body).Decode(&rule); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}
	if err := g.TriggerEngine.UpdateRule(&rule); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}
	g.sendJSON(w, map[string]interface{}{"success": true, "data": rule})
}

// handleTriggerDelete 删除规则
// DELETE /api/v1/trigger/rules?id=xxx
func (g *OpcGateway) handleTriggerDelete(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	if id == "" {
		http.Error(w, `{"error":"id is required"}`, http.StatusBadRequest)
		return
	}
	if g.TriggerEngine == nil {
		http.Error(w, `{"error":"TriggerEngine not initialized"}`, http.StatusInternalServerError)
		return
	}
	if err := g.TriggerEngine.DeleteRule(id); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}
	g.sendJSON(w, map[string]interface{}{"success": true})
}

// handleTriggerToggle 启用/禁用规则
// POST /api/v1/trigger/rules/toggle?id=xxx
func (g *OpcGateway) handleTriggerToggle(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	if id == "" {
		http.Error(w, `{"error":"id is required"}`, http.StatusBadRequest)
		return
	}
	if g.TriggerEngine == nil {
		http.Error(w, `{"error":"TriggerEngine not initialized"}`, http.StatusInternalServerError)
		return
	}
	if err := g.TriggerEngine.ToggleRule(id); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}
	g.sendJSON(w, map[string]interface{}{"success": true})
}

// handleTriggerEvent 手动提交事件
// POST /api/v1/trigger/event
func (g *OpcGateway) handleTriggerEvent(w http.ResponseWriter, r *http.Request) {
	if g.TriggerEngine == nil {
		http.Error(w, `{"error":"TriggerEngine not initialized"}`, http.StatusInternalServerError)
		return
	}
	var event TriggerEvent
	if err := json.NewDecoder(r.Body).Decode(&event); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}
	results := g.TriggerEngine.IngestEvent(&event)
	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    results,
		"matched": len(results),
	})
}

// handleTriggerStats 引擎统计
// GET /api/v1/trigger/stats
func (g *OpcGateway) handleTriggerStats(w http.ResponseWriter, r *http.Request) {
	if g.TriggerEngine == nil {
		g.sendJSON(w, map[string]interface{}{"success": true, "data": map[string]interface{}{
			"total_rules": 0, "enabled_rules": 0, "event_count": 0, "trigger_count": 0,
		}})
		return
	}
	stats := g.TriggerEngine.GetStats()
	g.sendJSON(w, map[string]interface{}{"success": true, "data": stats})
}

// handleTriggerPage 触发引擎管理页面
// GET /trigger
func (g *OpcGateway) handleTriggerPage(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(triggerPageHTML)
}

// ══════════════════════════════════════════════════════════════════════
// 系统采集协程
// ══════════════════════════════════════════════════════════════════════

// StartSystemCollector 启动系统指标采集协程
func (te *TriggerEngine) StartSystemCollector(interval time.Duration, cpuCores int) {
	if te.isRunning {
		return
	}
	te.isRunning = true
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		// 启动时立即采集一次
		te.collectAndEvaluate(cpuCores)

		for {
			select {
			case <-ticker.C:
				te.collectAndEvaluate(cpuCores)
			case <-te.stopCh:
				te.isRunning = false
				return
			}
		}
	}()
}

// Stop 停止采集
func (te *TriggerEngine) Stop() {
	if te.isRunning {
		close(te.stopCh)
		te.stopCh = make(chan struct{})
	}
}

func (te *TriggerEngine) collectAndEvaluate(cpuCores int) {
	// 采集系统指标（轻量级，不阻塞）
	cpuPct := readCPUPercent()
	memPct := readMemPercent()
	diskPct := readDiskPercent()
	load1m := readLoad1m()

	results := te.IngestSystemEvent(cpuPct, memPct, diskPct, load1m, cpuCores)
	if len(results) > 0 {
		for _, r := range results {
			logWithTimestamp("[Trigger] 📢 %s (rule=%s score=%d)", r.Message, r.RuleID, r.Score)
		}
	}
}

// ══════════════════════════════════════════════════════════════════════
// 辅助函数
// ══════════════════════════════════════════════════════════════════════

func toFloat64(v interface{}) (float64, bool) {
	switch val := v.(type) {
	case float64:
		return val, true
	case float32:
		return float64(val), true
	case int:
		return float64(val), true
	case int64:
		return float64(val), true
	case string:
		// 简单解析
		var f float64
		if _, err := fmt.Sscanf(val, "%f", &f); err == nil {
			return f, true
		}
		return 0, false
	default:
		return 0, false
	}
}

// ══════════════════════════════════════════════════════════════════════
// Web UI
// ══════════════════════════════════════════════════════════════════════

var triggerPageHTML = []byte(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ TriggerEngine 触发引擎</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
h1{color:#58a6ff;margin-bottom:20px}
h2{color:#8b949e;margin:20px 0 10px;font-size:16px;text-transform:uppercase;letter-spacing:1px}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.stat-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;text-align:center}
.stat-value{font-size:28px;font-weight:600;color:#58a6ff}
.stat-label{font-size:12px;color:#8b949e;margin-top:4px}
.rules-table{width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;overflow:hidden}
.rules-table th{background:#21262d;padding:10px 12px;text-align:left;font-size:12px;color:#8b949e;text-transform:uppercase}
.rules-table td{padding:10px 12px;border-top:1px solid #30363d;font-size:13px}
.status-badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.status-on{background:#1b3d2e;color:#3fb950}
.status-off{background:#3d1b1b;color:#f85149}
.actions button{padding:4px 10px;border:1px solid #30363d;border-radius:6px;cursor:pointer;font-size:12px}
.btn-toggle{background:#238636;color:#fff;border-color:#238636}
.btn-toggle:hover{background:#2ea043}
.btn-toggle.off{background:#da3633;border-color:#da3633}
.btn-delete{background:transparent;color:#f85149;border-color:#f85149;margin-left:4px}
.btn-add{background:#238636;color:#fff;border:1px solid #238636;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:14px;margin-bottom:16px}
.btn-add:hover{background:#2ea043}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;justify-content:center;align-items:center}
.modal-content{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;width:90%;max-width:600px;max-height:80vh;overflow-y:auto}
.modal h2{margin-bottom:16px;color:#58a6ff}
.form-group{margin-bottom:12px}
.form-group label{display:block;font-size:12px;color:#8b949e;margin-bottom:4px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:8px 10px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:13px}
.form-group textarea{resize:vertical;min-height:60px}
.form-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}
.form-actions button{padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px}
.btn-save{background:#238636;color:#fff;border:1px solid #238636}
.btn-cancel{background:transparent;color:#8b949e;border:1px solid #30363d}
.log-area{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px;margin-top:16px;max-height:300px;overflow-y:auto;font-family:'SF Mono',monospace;font-size:12px}
.log-entry{padding:4px 0;border-bottom:1px solid #21262d}
.log-time{color:#8b949e;margin-right:8px}
.log-score{color:#d29922}
.log-msg{color:#c9d1d9}
.test-btn{margin-left:8px;padding:4px 10px;background:#1f6feb;color:#fff;border:1px solid #1f6feb;border-radius:6px;cursor:pointer;font-size:12px}
@media(max-width:768px){.rules-table{font-size:12px}th,td{padding:6px 8px}}
</style>
</head>
<body>
<h1>⚡ TriggerEngine 触发引擎</h1>

<div class="stats-grid" id="statsGrid">
  <div class="stat-card"><div class="stat-value" id="totalRules">0</div><div class="stat-label">规则总数</div></div>
  <div class="stat-card"><div class="stat-value" id="enabledRules">0</div><div class="stat-label">启用规则</div></div>
  <div class="stat-card"><div class="stat-value" id="eventCount">0</div><div class="stat-label">事件总数</div></div>
  <div class="stat-card"><div class="stat-value" id="triggerCount">0</div><div class="stat-label">触发次数</div></div>
</div>

<button class="btn-add" onclick="showAddModal()">＋ 添加规则</button>

<table class="rules-table">
<thead><tr><th>名称</th><th>类型</th><th>条件</th><th>权重</th><th>防抖</th><th>状态</th><th>触发</th><th>操作</th></tr></thead>
<tbody id="rulesBody"></tbody>
</table>

<h2>📋 最近触发日志</h2>
<div class="log-area" id="triggerLog"></div>

<div id="addModal" class="modal"><div class="modal-content" id="modalContent"></div></div>

<script>
const API_BASE = '/api/v1/trigger';
let rules = [];

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  return res.json();
}

async function loadStats() {
  const d = await fetchJSON(API_BASE + '/stats');
  if (!d.success) return;
  const s = d.data;
  document.getElementById('totalRules').textContent = s.total_rules || 0;
  document.getElementById('enabledRules').textContent = s.enabled_rules || 0;
  document.getElementById('eventCount').textContent = s.event_count || 0;
  document.getElementById('triggerCount').textContent = s.trigger_count || 0;
  if (s.recent_triggers && s.recent_triggers.length > 0) {
    const logDiv = document.getElementById('triggerLog');
    logDiv.innerHTML = s.recent_triggers.slice(-20).reverse().map(r =>
      '<div class="log-entry"><span class="log-time">' + new Date(r.timestamp).toLocaleString() +
      '</span><span class="log-score">[' + r.score + ']</span> ' +
      '<span class="log-msg">' + esc(r.message) + '</span></div>'
    ).join('');
  }
}

async function loadRules() {
  const d = await fetchJSON(API_BASE + '/rules');
  if (!d.success) return;
  rules = d.data;
  const tbody = document.getElementById('rulesBody');
  tbody.innerHTML = rules.map(r =>
    '<tr>' +
      '<td><strong>' + esc(r.name) + '</strong>' + (r.description ? '<br><small>' + esc(r.description) + '</small>' : '') + '</td>' +
      '<td>' + esc(r.event_type) + '</td>' +
      '<td>' + esc(r.condition.field) + ' ' + esc(r.condition.operator) + ' ' + (r.condition.value ? r.condition.value : esc(r.condition.str_value || '')) + '</td>' +
      '<td>' + r.weight + '</td>' +
      '<td>' + (r.debounce / 1e9) + 's</td>' +
      '<td><span class="status-badge ' + (r.enabled ? 'status-on' : 'status-off') + '">' + (r.enabled ? '启用' : '禁用') + '</span></td>' +
      '<td>' + (r.hit_count || 0) + '</td>' +
      '<td class="actions">' +
        '<button class="btn-toggle ' + (r.enabled ? '' : 'off') + '" onclick="toggleRule(\'' + r.id + '\')">' + (r.enabled ? '禁用' : '启用') + '</button>' +
        '<button class="test-btn" onclick="testRule(\'' + r.id + '\')">测试</button>' +
        '<button class="btn-delete" onclick="deleteRule(\'' + r.id + '\')">删除</button>' +
      '</td>' +
    '</tr>'
  ).join('');
}

function esc(s) { if (!s) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function toggleRule(id) {
  await fetchJSON(API_BASE + '/rules/toggle?id=' + id, {method:'POST'});
  await loadRules();
  await loadStats();
}

async function deleteRule(id) {
  if (!confirm('确定删除规则 "' + rules.find(r=>r.id===id)?.name + '" ？')) return;
  await fetchJSON(API_BASE + '/rules?id=' + id, {method:'DELETE'});
  await loadRules();
  await loadStats();
}

async function testRule(id) {
  const rule = rules.find(r => r.id === id);
  if (!rule) return;
  const event = {
    type: rule.event_type,
    source: 'test',
    fields: {
      cpu_percent: 95,
      mem_percent: 90,
      disk_percent: 95,
      load_1m: 8,
      cpu_cores: 4,
      message_content: '@trigger test message',
      message_type: 'technical',
      value: 'test'
    }
  };
  const d = await fetchJSON(API_BASE + '/event', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(event)
  });
  if (d.success) {
    alert('触发结果: ' + d.matched + ' 条匹配\n' + (d.data || []).map(r => '• ' + r.message).join('\n'));
    await loadStats();
  }
}

function showAddModal() {
  const modal = document.getElementById('addModal');
  modal.style.display = 'flex';
  var h = '<h2>＋ 添加规则</h2>';
  h += '<div class="form-group"><label>名称</label><input id="fn_name"></div>';
  h += '<div class="form-group"><label>描述</label><textarea id="fn_desc"></textarea></div>';
  h += '<div class="form-group"><label>事件类型</label><select id="fn_type">';
  h += '<option value="system">system (系统指标)</option>';
  h += '<option value="hall">hall (Hall 消息)</option>';
  h += '<option value="webhook">webhook (外部信号)</option>';
  h += '</select></div>';
  h += '<div class="form-group"><label>条件·字段</label><input id="fn_field" placeholder="cpu_percent / mem_percent / message_content"></div>';
  h += '<div class="form-group"><label>条件·运算符</label><select id="fn_op">';
  h += '<option value="gt">gt 大于</option><option value="lt">lt 小于</option>';
  h += '<option value="eq">eq 等于</option><option value="contains">contains 包含</option>';
  h += '</select></div>';
  h += '<div class="form-group"><label>条件·值</label><input id="fn_val" placeholder="80 (数值) 或 @trigger (字符串)"></div>';
  h += '<div class="form-group"><label>权重 (0-100)</label><input id="fn_weight" type="number" value="80" min="0" max="100"></div>';
  h += '<div class="form-group"><label>防抖 (秒)</label><input id="fn_debounce" type="number" value="300"></div>';
  h += '<div class="form-group"><label>动作类型</label><select id="fn_action_type">';
  h += '<option value="log">log 日志</option><option value="alert">alert 告警</option>';
  h += '<option value="broadcast">broadcast 广播</option><option value="exec">exec 执行命令</option>';
  h += '</select></div>';
  h += '<div class="form-group"><label>动作消息 (可用 {value})</label><input id="fn_action_msg" placeholder="⚠️ 告警: {value}%"></div>';
  h += '<div class="form-actions"><button class="btn-save" onclick="submitAdd()">保存</button>';
  h += '<button class="btn-cancel" onclick="hideModal()">取消</button></div>';
  document.getElementById('modalContent').innerHTML = h;
}

function hideModal() { document.getElementById('addModal').style.display = 'none'; }

async function submitAdd() {
  const val = document.getElementById('fn_val').value;
  const numVal = parseFloat(val);
  const condition = {
    field: document.getElementById('fn_field').value,
    operator: document.getElementById('fn_op').value
  };
  if (!isNaN(numVal)) {
    condition.value = numVal;
    condition.str_value = '';
  } else {
    condition.value = 0;
    condition.str_value = val;
  }

  const rule = {
    name: document.getElementById('fn_name').value,
    description: document.getElementById('fn_desc').value,
    event_type: document.getElementById('fn_type').value,
    enabled: true,
    weight: parseInt(document.getElementById('fn_weight').value) || 80,
    debounce: (parseInt(document.getElementById('fn_debounce').value) || 300) * 1e9,
    condition: condition,
    actions: [{
      type: document.getElementById('fn_action_type').value,
      message: document.getElementById('fn_action_msg').value
    }]
  };

  const d = await fetchJSON(API_BASE + '/rules', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(rule)
  });
  if (d.success) {
    hideModal();
    await loadRules();
    await loadStats();
  } else {
    alert('添加失败: ' + (d.error || 'unknown'));
  }
}

document.addEventListener('click', function(e) {
  if (e.target === document.getElementById('addModal')) hideModal();
});

async function init() {
  await loadStats();
  await loadRules();
}
init();
</script>
</body>
</html>`)