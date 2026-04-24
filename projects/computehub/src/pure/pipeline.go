package pure

import (
	"fmt"
	"strings"
	"time"
)

// FilterResult represents the outcome of a filter stage
type FilterResult struct {
	Passed  bool
	Reason  string
	Cleaned interface{}
}

// PureFilter defines the interface for a filter stage
type PureFilter interface {
	Filter(input interface{}) FilterResult
	Name() string
}

// PurePipeline manages the sequence of filters
type PurePipeline struct {
	filters     []PureFilter
	LastLatency time.Duration
}

func NewPurePipeline() *PurePipeline {
	return &PurePipeline{
		filters: make([]PureFilter, 0),
	}
}

func (p *PurePipeline) AddFilter(f PureFilter) {
	p.filters = append(p.filters, f)
}

// Process runs the input through the multi-stage purification pipeline
func (p *PurePipeline) Process(input interface{}) (interface{}, error) {
	start := time.Now()
	current := input
	for _, filter := range p.filters {
		res := filter.Filter(current)
		if !res.Passed {
			p.LastLatency = time.Since(start)
			return nil, fmt.Errorf("[%s] purification failed: %s", filter.Name(), res.Reason)
		}
		current = res.Cleaned
	}
	p.LastLatency = time.Since(start)
	return current, nil
}

// --- Filter Implementations ---

// SyntaxFilter: Stage 1 - Basic format and character validation
type SyntaxFilter struct{}
func (f *SyntaxFilter) Name() string { return "SyntaxFilter" }
func (f *SyntaxFilter) Filter(input interface{}) FilterResult {
	s, ok := input.(string)
	if !ok {
		return FilterResult{Passed: false, Reason: "input must be a string"}
	}
	if len(strings.TrimSpace(s)) == 0 {
		return FilterResult{Passed: false, Reason: "empty input"}
	}
	// Basic sanitization: trim spaces
	return FilterResult{Passed: true, Cleaned: strings.TrimSpace(s)}
}

// SemanticFilter: Stage 2 - Intent and policy validation
type SemanticFilter struct {
	AllowedActions []string
}
func (f *SemanticFilter) Name() string { return "SemanticFilter" }
func (f *SemanticFilter) Filter(input interface{}) FilterResult {
	s := input.(string)
	// Simple keyword-based intent check for v0.1
	for _, action := range f.AllowedActions {
		if strings.Contains(strings.ToUpper(s), strings.ToUpper(action)) {
			return FilterResult{Passed: true, Cleaned: s}
		}
	}
	return FilterResult{Passed: false, Reason: "action not permitted by semantic policy"}
}

// BoundaryFilter: Stage 3 - Path anchoring and security isolation
type BoundaryFilter struct {
	Blacklist []string
}
func (f *BoundaryFilter) Name() string { return "BoundaryFilter" }
func (f *BoundaryFilter) Filter(input interface{}) FilterResult {
	s := input.(string)
	for _, b := range f.Blacklist {
		if strings.Contains(s, b) {
			return FilterResult{Passed: false, Reason: fmt.Sprintf("security violation: path %s is forbidden", b)}
		}
	}
	return FilterResult{Passed: true, Cleaned: s}
}

// ContextFilter: Stage 4 - Physical context injection
type ContextFilter struct {
	DeviceFingerprint string
}
func (f *ContextFilter) Name() string { return "ContextFilter" }
func (f *ContextFilter) Filter(input interface{}) FilterResult {
	s := input.(string)
	// Injecting physical context into the instruction
	enriched := fmt.Sprintf("[%s] %s", f.DeviceFingerprint, s)
	return FilterResult{Passed: true, Cleaned: enriched}
}
