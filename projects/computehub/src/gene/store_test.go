package gene

import (
	"os"
	"path/filepath"
	"testing"
)

func TestNewGeneStore(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	if gs.filePath != tmpFile {
		t.Errorf("Expected path %s, got %s", tmpFile, gs.filePath)
	}
	if len(gs.Genes) != 0 {
		t.Errorf("Expected 0 genes, got %d", len(gs.Genes))
	}
}

func TestEvolveAndRecall(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	gs.Evolve("EXEC rm -rf /", "EXEC echo 'safety check'", "dangerous command")

	path, found := gs.Recall("EXEC rm -rf /")
	if !found {
		t.Fatal("Expected gene to be found")
	}
	if path != "EXEC echo 'safety check'" {
		t.Errorf("Expected corrected path, got '%s'", path)
	}
}

func TestRecallNonExistent(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	_, found := gs.Recall("NON_EXISTENT_PATTERN")
	if found {
		t.Fatal("Should not find non-existent gene")
	}
}

func TestEvolveOverwriteExisting(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	gs.Evolve("pattern1", "fix1", "reason1")
	gs.Evolve("pattern1", "fix2", "reason2")

	path, _ := gs.Recall("pattern1")
	if path != "fix2" {
		t.Errorf("Expected overwritten path 'fix2', got '%s'", path)
	}
}

func TestMultipleGenes(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	patterns := []struct {
		pattern string
		fix     string
		reason  string
	}{
		{"CMD_RM", "CMDL_SAFE_RM", "rm without safety"},
		{"CMD_SUDO", "CMD_NOSUDO", "sudo not allowed"},
		{"CMD_DD", "CMD_DD_SAFE", "dd without bs/if"},
	}

	for _, p := range patterns {
		gs.Evolve(p.pattern, p.fix, p.reason)
	}

	if len(gs.Genes) != 3 {
		t.Errorf("Expected 3 genes, got %d", len(gs.Genes))
	}

	for _, p := range patterns {
		path, found := gs.Recall(p.pattern)
		if !found {
			t.Errorf("Pattern '%s' not found", p.pattern)
		}
		if path != p.fix {
			t.Errorf("Pattern '%s': expected fix '%s', got '%s'", p.pattern, p.fix, path)
		}
	}
}

func TestPersistenceSaveAndLoad(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")

	// Create and save
	gs := NewGeneStore(tmpFile)
	gs.Evolve("pattern1", "fix1", "reason1")
	gs.Evolve("pattern2", "fix2", "reason2")

	// Force save
	gs.mu.Lock()
	err := gs.save()
	gs.mu.Unlock()
	if err != nil {
		t.Fatalf("Failed to save: %v", err)
	}

	// Load from new store
	gs2 := NewGeneStore(tmpFile)
	if len(gs2.Genes) != 2 {
		t.Errorf("Expected 2 genes after reload, got %d", len(gs2.Genes))
	}

	path, found := gs2.Recall("pattern1")
	if !found {
		t.Fatal("Pattern 'pattern1' not found after reload")
	}
	if path != "fix1" {
		t.Errorf("Expected 'fix1', got '%s'", path)
	}
}

func TestPersistenceNoFile(t *testing.T) {
	gs := NewGeneStore("/tmp/non_existent_dir_xyzzy/genes.json")
	// Should not panic, just start empty
	if len(gs.Genes) != 0 {
		t.Errorf("Expected empty store, got %d genes", len(gs.Genes))
	}
}

func TestRecallLowConfidence(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	// Manually add a gene with low confidence
	gs.mu.Lock()
	gs.Genes["low_conf_pattern"] = Gene{
		Pattern:    "low_conf_pattern",
		CorrectPath: "safe_command",
		Confidence: 0.5,
	}
	gs.mu.Unlock()

	_, found := gs.Recall("low_conf_pattern")
	if found {
		t.Fatal("Should not recall gene with confidence <= 0.8")
	}
}

func TestRecallBoundaryConfidence(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	// Exactly at boundary (0.8)
	gs.mu.Lock()
	gs.Genes["boundary_pattern"] = Gene{
		Pattern:    "boundary_pattern",
		CorrectPath: "safe_path",
		Confidence: 0.8,
	}
	gs.mu.Unlock()

	_, found := gs.Recall("boundary_pattern")
	if found {
		t.Fatal("Should not recall gene with confidence exactly 0.8 (not > 0.8)")
	}

	// Above boundary
	gs.mu.Lock()
	gs.Genes["above_pattern"] = Gene{
		Pattern:    "above_pattern",
		CorrectPath: "safe_path",
		Confidence: 0.81,
	}
	gs.mu.Unlock()

	path, found := gs.Recall("above_pattern")
	if !found {
		t.Fatal("Should recall gene with confidence 0.81 (> 0.8)")
	}
	if path != "safe_path" {
		t.Errorf("Expected 'safe_path', got '%s'", path)
	}
}

func TestConcurrentEvolve(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	done := make(chan bool, 20)
	for i := 0; i < 20; i++ {
		go func(n int) {
			gs.Evolve(
				"pattern_%d", "fix_%d", "reason",
			)
			done <- true
		}(i)
	}

	for i := 0; i < 20; i++ {
		<-done
	}
}

func TestEvolveAndRecallConcurrent(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "genes.json")
	gs := NewGeneStore(tmpFile)

	done := make(chan bool, 50)
	for i := 0; i < 50; i++ {
		go func(n int) {
			pattern := "concurrent_%d"
			gs.Evolve(pattern, "fix", "test")
			gs.Recall(pattern)
			done <- true
		}(i)
	}

	for i := 0; i < 50; i++ {
		<-done
	}
}

func BenchmarkEvolve(b *testing.B) {
	tmpFile, _ := os.CreateTemp("", "benchmark_genes.json")
	defer os.Remove(tmpFile.Name())

	gs := NewGeneStore(tmpFile.Name())
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		gs.Evolve("bench_pattern", "bench_fix", "bench_reason")
	}
}

func BenchmarkRecall(b *testing.B) {
	tmpFile, _ := os.CreateTemp("", "benchmark_genes.json")
	defer os.Remove(tmpFile.Name())

	gs := NewGeneStore(tmpFile.Name())
	gs.Evolve("bench_pattern", "bench_fix", "bench_reason")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		gs.Recall("bench_pattern")
	}
}
