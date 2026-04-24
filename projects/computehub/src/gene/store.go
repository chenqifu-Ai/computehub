package gene

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// Gene represents a learned pattern from a failed or successful execution
type Gene struct {
	Pattern       string    `json:"pattern"`       // The trigger pattern (e.g., a command or error)
	CorrectPath   string    `json:"correct_path"`   // The verified successful command
	FailureReason string    `json:"failure_reason"` // Why the previous path failed
	LastVerified  time.Time `json:"last_verified"`
	Confidence    float64   `json:"confidence"`    // 0.0 to 1.0
}

// GeneStore is the physical persistence layer for system genes
type GeneStore struct {
	mu       sync.RWMutex
	filePath string
	Genes    map[string]Gene `json:"genes"`
}

func NewGeneStore(path string) *GeneStore {
	store := &GeneStore{
		filePath: path,
		Genes:    make(map[string]Gene),
	}
	store.load()
	return store
}

// Load genes from physical disk
func (s *GeneStore) load() {
	s.mu.Lock()
	defer s.mu.Unlock()

	data, err := os.ReadFile(s.filePath)
	if err != nil {
		return // File might not exist yet
	}

	json.Unmarshal(data, s)
}

// Save genes to physical disk
func (s *GeneStore) save() error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.filePath, data, 0644)
}

// Evolve records a failure and a subsequent success to create a gene
func (s *GeneStore) Evolve(pattern, correctPath, reason string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.Genes[pattern] = Gene{
		Pattern:       pattern,
		CorrectPath:   correctPath,
		FailureReason: reason,
		LastVerified:  time.Now(),
		Confidence:    1.0,
	}
	s.save()
	logWithTimestamp("[GeneStore] 🧬 Evolution complete: Pattern [%s] -> CorrectPath [%s]", pattern, correctPath)
}

// Recall checks if a gene exists for the given pattern to bypass failure
func (s *GeneStore) Recall(pattern string) (string, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	gene, exists := s.Genes[pattern]
	if exists && gene.Confidence > 0.8 {
		return gene.CorrectPath, true
	}
	return "", false
}
