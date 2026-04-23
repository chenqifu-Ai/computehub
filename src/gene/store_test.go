// Package gene_test - 基因系统单元测试
package gene

import (
	"path/filepath"
	"testing"
	"time"
)

func setupTestStore(t *testing.T) (*Store, string) {
	t.Helper()
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "genes.json")
	store := NewStore(path)
	return store, path
}

func TestNewStore(t *testing.T) {
	store, _ := setupTestStore(t)
	if store == nil {
		t.Fatal("Store should not be nil")
	}
	if store.Genes == nil {
		t.Fatal("Genes map should be initialized")
	}
}

func TestEvolve_CreateGene(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("test_pattern", "correct_path", "test failure reason", "manual")

	genes := store.List()
	if len(genes) != 1 {
		t.Errorf("Expected 1 gene, got %d", len(genes))
	}

	gene := store.Genes["test_pattern"]
	if gene.Pattern != "test_pattern" {
		t.Errorf("Expected pattern 'test_pattern', got '%s'", gene.Pattern)
	}
	if gene.CorrectPath != "correct_path" {
		t.Errorf("Expected correct_path 'correct_path', got '%s'", gene.CorrectPath)
	}
	if gene.Confidence != 1.0 {
		t.Errorf("Expected confidence 1.0, got %f", gene.Confidence)
	}
}

func TestEvolve_UpdateGene(t *testing.T) {
	store, _ := setupTestStore(t)

	// Create first gene
	store.Evolve("test_pattern", "path_v1", "reason1", "manual")
	gene1 := store.Genes["test_pattern"]
	if gene1.Confidence != 1.0 {
		t.Error("First evolution should set confidence to 1.0")
	}

	// Evolve again - should update
	store.Evolve("test_pattern", "path_v2", "reason2", "auto_learn")
	gene2 := store.Genes["test_pattern"]
	if gene2.CorrectPath != "path_v2" {
		t.Errorf("Expected updated path 'path_v2', got '%s'", gene2.CorrectPath)
	}
	if gene2.Confidence != 1.0 {
		t.Error("Second evolution should reset confidence to 1.0")
	}
}

func TestRecall_Success(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("test_pattern", "correct_path", "test failure", "manual")
	store.UpdateConfidence("test_pattern", 0.95) // High confidence

	correctPath, found := store.Recall("test_pattern")
	if !found {
		t.Fatal("Should find gene with high confidence")
	}
	if correctPath != "correct_path" {
		t.Errorf("Expected 'correct_path', got '%s'", correctPath)
	}
}

func TestRecall_LowConfidence(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("test_pattern", "correct_path", "test failure", "manual")
	store.UpdateConfidence("test_pattern", 0.5) // Below threshold

	_, found := store.Recall("test_pattern")
	if found {
		t.Fatal("Should not find gene with confidence < 0.8")
	}
}

func TestRecall_NotFound(t *testing.T) {
	store, _ := setupTestStore(t)

	_, found := store.Recall("nonexistent")
	if found {
		t.Fatal("Should not find non-existent gene")
	}
}

func TestRecall_UsageStats(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("test_pattern", "correct_path", "test failure", "manual")
	store.UpdateConfidence("test_pattern", 0.9)

	// Recall twice
	store.Recall("test_pattern")
	store.Recall("test_pattern")

	gene := store.Genes["test_pattern"]
	if gene.UsageCount != 2 {
		t.Errorf("Expected usage_count 2, got %d", gene.UsageCount)
	}
}

func TestAddGene(t *testing.T) {
	store, _ := setupTestStore(t)

	store.AddGene("manual_pattern", "manual_path", "manual reason")
	count := store.Count()
	if count != 1 {
		t.Errorf("Expected 1 gene, got %d", count)
	}
}

func TestRemoveGene(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("to_remove", "path", "reason", "manual")
	if store.Count() != 1 {
		t.Fatal("Should have 1 gene before remove")
	}

	store.RemoveGene("to_remove")
	if store.Count() != 0 {
		t.Error("Should have 0 genes after remove")
	}
}

func TestUpdateConfidence(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("test_pattern", "path", "reason", "manual")

	store.UpdateConfidence("test_pattern", 0.3)
	gene := store.Genes["test_pattern"]
	if gene.Confidence != 0.3 {
		t.Error("Confidence should be updated to 0.3")
	}
}

func TestDecayConfidence(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("test_pattern", "path", "reason", "manual")
	gene := store.Genes["test_pattern"]
	originalConfidence := gene.Confidence

	// Set LastVerified to 1 year ago to trigger decay
	gene.LastVerified = gene.CreatedAt.Add(-24 * 365 * 24 * time.Hour)
	store.Genes["test_pattern"] = gene

	store.DecayConfidence(24*30*time.Hour, 0.9)
	gene = store.Genes["test_pattern"]
	if gene.Confidence >= originalConfidence {
		t.Error("Confidence should have decayed")
	}
}

func TestStats(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("high_conf", "path1", "reason1", "manual")
	store.UpdateConfidence("high_conf", 0.95)

	store.Evolve("medium_conf", "path2", "reason2", "auto")
	store.UpdateConfidence("medium_conf", 0.85)

	store.Evolve("low_conf", "path3", "reason3", "manual")
	store.UpdateConfidence("low_conf", 0.5)

	stats := store.Stats()
	if stats["total"] != 3 {
		t.Errorf("Expected 3 total genes, got %v", stats["total"])
	}
	if stats["high_confidence"] != 1 {
		t.Errorf("Expected 1 high confidence gene, got %v", stats["high_confidence"])
	}
}

func TestSaveAndLoad(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("persist_test", "persist_path", "persist reason", "manual")

	// Force save
	store.save()

	// Create new store from same file
	store2 := NewStore(store.filePath)
	store2.load()

	if store2.Count() != 1 {
		t.Errorf("Expected 1 gene after reload, got %d", store2.Count())
	}

	gene := store2.Genes["persist_test"]
	if gene.Pattern != "persist_test" {
		t.Errorf("Expected pattern 'persist_test', got '%s'", gene.Pattern)
	}
}

func TestPredefinedGenes(t *testing.T) {
	genes := PredefinedGenes()
	if len(genes) != 3 {
		t.Errorf("Expected 3 predefined genes, got %d", len(genes))
	}

	expectedPatterns := []string{"docker_unavailable", "insufficient_memory", "cuda_not_found"}
	for _, pattern := range expectedPatterns {
		if _, ok := genes[pattern]; !ok {
			t.Errorf("Missing predefined gene: %s", pattern)
		}
	}
}

func TestLoadPredefined(t *testing.T) {
	store, _ := setupTestStore(t)

	store.LoadPredefined()
	if store.Count() != 3 {
		t.Errorf("Expected 3 genes after loading predefined, got %d", store.Count())
	}
}

func TestExportImport(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("export_test", "export_path", "export reason", "manual")
	store.UpdateConfidence("export_test", 0.9)

	exported, err := store.Export()
	if err != nil {
		t.Fatalf("Export should succeed: %v", err)
	}

	// Create new store and import
	store2 := &Store{
		filePath: store.filePath,
		Genes:    make(map[string]Gene),
	}
	err = store2.Import(exported)
	if err != nil {
		t.Fatalf("Import should succeed: %v", err)
	}

	if store2.Count() != 1 {
		t.Errorf("Expected 1 gene after import, got %d", store2.Count())
	}
}

func TestListReturnsAll(t *testing.T) {
	store, _ := setupTestStore(t)

	store.Evolve("gene_a", "path_a", "reason_a", "manual")
	store.Evolve("gene_b", "path_b", "reason_b", "manual")
	store.Evolve("gene_c", "path_c", "reason_c", "manual")

	list := store.List()
	if len(list) != 3 {
		t.Errorf("Expected 3 genes in list, got %d", len(list))
	}
}

func TestCount(t *testing.T) {
	store, _ := setupTestStore(t)

	if store.Count() != 0 {
		t.Error("Empty store should have count 0")
	}

	store.Evolve("a", "pa", "ra", "manual")
	store.Evolve("b", "pb", "rb", "manual")

	if store.Count() != 2 {
		t.Errorf("Expected count 2, got %d", store.Count())
	}
}
