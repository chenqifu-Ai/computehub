// Package gene implements the evolution and learning system.
// It records task failures and successes, learning from mistakes
// to create "genes" that automatically fix common failure patterns.
//
// Principle: One failure, permanent fix.
package gene

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

// ─── 基因结构 ───

// Gene represents a learned pattern from task execution.
// Each gene maps a failure pattern to a verified correct solution.
type Gene struct {
	Pattern       string    `json:"pattern"`       // Trigger pattern (e.g., "CUDA out of memory")
	CorrectPath   string    `json:"correct_path"`  // Verified successful action
	FailureReason string    `json:"failure_reason"` // Why the original path failed
	CreatedAt     time.Time `json:"created_at"`
	LastVerified  time.Time `json:"last_verified"`
	Confidence    float64   `json:"confidence"` // 0.0 to 1.0
	UsageCount    int       `json:"usage_count"`
	LastUsed      time.Time `json:"last_used,omitempty"`
	Source        string    `json:"source"` // "manual", "auto_learn", "import"
}

// ─── 基因存储 ───

// Store is the physical persistence layer for system genes.
type Store struct {
	mu       sync.RWMutex
	filePath string
	Genes    map[string]Gene `json:"genes"`
	loaded   bool
}

// NewStore creates a new gene store and loads from disk.
func NewStore(path string) *Store {
	s := &Store{
		filePath: path,
		Genes:    make(map[string]Gene),
	}
	s.load()
	return s
}

// ─── 持久化 ───

// load reads genes from disk.
func (s *Store) load() {
	s.mu.Lock()
	defer s.mu.Unlock()

	data, err := os.ReadFile(s.filePath)
	if err != nil {
		// File may not exist yet - that's fine
		return
	}

	if err := json.Unmarshal(data, s); err != nil {
		return
	}
	s.loaded = true
}

// save writes genes to disk atomically.
func (s *Store) save() error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}

	// Write to temp file first, then rename (atomic)
	tmpFile := s.filePath + ".tmp"
	if err := os.WriteFile(tmpFile, data, 0644); err != nil {
		return err
	}
	return os.Rename(tmpFile, s.filePath)
}

// ─── 进化核心 ───

// Evolve creates a new gene from a failure and its fix.
func (s *Store) Evolve(pattern, correctPath, failureReason, source string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Update or create gene
	if gene, exists := s.Genes[pattern]; exists {
		gene.Confidence = 1.0 // Reset confidence on evolution
		gene.LastVerified = time.Now()
		gene.UsageCount = 0
		gene.CorrectPath = correctPath
		gene.FailureReason = failureReason
		s.Genes[pattern] = gene
	} else {
		s.Genes[pattern] = Gene{
			Pattern:       pattern,
			CorrectPath:   correctPath,
			FailureReason: failureReason,
			CreatedAt:     time.Now(),
			LastVerified:  time.Now(),
			Confidence:    1.0,
			Source:        source,
		}
	}

	s.save()
}

// Recall looks up a gene for the given pattern.
// Returns the correct path and true if found with sufficient confidence.
func (s *Store) Recall(pattern string) (string, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	gene, exists := s.Genes[pattern]
	if !exists {
		return "", false
	}

	if gene.Confidence < 0.8 {
		return "", false
	}

	// Update usage stats
	gene.UsageCount++
	gene.LastUsed = time.Now()
	s.Genes[pattern] = gene

	return gene.CorrectPath, true
}

// ─── 管理操作 ───

// AddGene manually adds a gene.
func (s *Store) AddGene(pattern, correctPath, failureReason string) {
	s.Evolve(pattern, correctPath, failureReason, "manual")
}

// RemoveGene deletes a gene by pattern.
func (s *Store) RemoveGene(pattern string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.Genes, pattern)
	s.save()
}

// UpdateConfidence adjusts a gene's confidence score.
func (s *Store) UpdateConfidence(pattern string, confidence float64) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if gene, exists := s.Genes[pattern]; exists {
		gene.Confidence = confidence
		s.Genes[pattern] = gene
		s.save()
	}
}

// DecayConfidence applies confidence decay to unused genes.
func (s *Store) DecayConfidence(maxAge time.Duration, decayFactor float64) {
	s.mu.Lock()
	defer s.mu.Unlock()

	now := time.Now()
	changed := false

	for pattern, gene := range s.Genes {
		age := now.Sub(gene.LastVerified)
		if age > maxAge && gene.Confidence > 0 {
			gene.Confidence = gene.Confidence * decayFactor
			s.Genes[pattern] = gene
			changed = true
		}
	}

	if changed {
		s.save()
	}
}

// List returns all genes.
func (s *Store) List() []Gene {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]Gene, 0, len(s.Genes))
	for _, gene := range s.Genes {
		result = append(result, gene)
	}
	return result
}

// Count returns total gene count.
func (s *Store) Count() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.Genes)
}

// Stats returns gene store statistics.
func (s *Store) Stats() map[string]any {
	s.mu.RLock()
	defer s.mu.RUnlock()

	totalConfidence := 0.0
	highConf := 0
	mediumConf := 0
	lowConf := 0

	for _, gene := range s.Genes {
		totalConfidence += gene.Confidence
		switch {
		case gene.Confidence >= 0.9:
			highConf++
		case gene.Confidence >= 0.8:
			mediumConf++
		default:
			lowConf++
		}
	}

	return map[string]any{
		"total":          len(s.Genes),
		"high_confidence": highConf,
		"medium_confidence": mediumConf,
		"low_confidence": lowConf,
		"avg_confidence": func() float64 {
			if len(s.Genes) == 0 {
				return 0
			}
			return totalConfidence / float64(len(s.Genes))
		}(),
		"total_usages": func() int {
			total := 0
			for _, g := range s.Genes {
				total += g.UsageCount
			}
			return total
		}(),
	}
}

// ─── 预置基因 ───

// PredefinedGenes returns common default genes for ComputeHub.
func PredefinedGenes() map[string]Gene {
	return map[string]Gene{
		"docker_unavailable": {
			Pattern:       "docker_unavailable",
			CorrectPath:   "fallback_to_direct_execute",
			FailureReason: "Docker daemon not running or unavailable",
			CreatedAt:     time.Now(),
			LastVerified:  time.Now(),
			Confidence:    0.7,
			Source:        "predefined",
		},
		"insufficient_memory": {
			Pattern:       "insufficient_memory",
			CorrectPath:   "reduce_batch_size",
			FailureReason: "OOM error during task execution",
			CreatedAt:     time.Now(),
			LastVerified:  time.Now(),
			Confidence:    0.8,
			Source:        "predefined",
		},
		"cuda_not_found": {
			Pattern:       "cuda_not_found",
			CorrectPath:   "use_cpu_fallback",
			FailureReason: "CUDA not available on assigned node",
			CreatedAt:     time.Now(),
			LastVerified:  time.Now(),
			Confidence:    0.85,
			Source:        "predefined",
		},
	}
}

// LoadPredefined loads predefined genes into the store.
func (s *Store) LoadPredefined() {
	s.mu.Lock()
	defer s.mu.Unlock()

	for pattern, gene := range PredefinedGenes() {
		if _, exists := s.Genes[pattern]; !exists {
			s.Genes[pattern] = gene
		}
	}
	s.save()
}

// ─── 序列化 ───

// Export outputs genes as JSON bytes.
func (s *Store) Export() ([]byte, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return json.MarshalIndent(s.Genes, "", "  ")
}

// Import loads genes from JSON bytes.
func (s *Store) Import(data []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	var genes map[string]Gene
	if err := json.Unmarshal(data, &genes); err != nil {
		return err
	}

	for pattern, gene := range genes {
		s.Genes[pattern] = gene
	}
	return s.save()
}
