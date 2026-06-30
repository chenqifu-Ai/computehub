package pure

import (
	"strings"
	"testing"
)

func TestNewPipeline(t *testing.T) {
	p := NewPurePipeline()
	if len(p.filters) != 0 {
		t.Errorf("Expected 0 filters, got %d", len(p.filters))
	}
}

func TestAddFilter(t *testing.T) {
	p := NewPurePipeline()
	p.AddFilter(&SyntaxFilter{})

	if len(p.filters) != 1 {
		t.Errorf("Expected 1 filter, got %d", len(p.filters))
	}
}

func TestSyntaxFilterValidInput(t *testing.T) {
	f := &SyntaxFilter{}
	res := f.Filter("  hello world  ")

	if !res.Passed {
		t.Fatalf("Expected valid input to pass, failed with: %s", res.Reason)
	}
	cleaned, ok := res.Cleaned.(string)
	if !ok {
		t.Fatal("Cleaned should be a string")
	}
	if cleaned != "hello world" {
		t.Errorf("Expected trimmed 'hello world', got '%s'", cleaned)
	}
}

func TestSyntaxFilterEmptyInput(t *testing.T) {
	f := &SyntaxFilter{}
	res := f.Filter("   ")

	if res.Passed {
		t.Fatal("Expected empty input to fail")
	}
	if !strings.Contains(res.Reason, "empty") {
		t.Errorf("Expected 'empty' in reason, got '%s'", res.Reason)
	}
}

func TestSyntaxFilterNonString(t *testing.T) {
	f := &SyntaxFilter{}
	res := f.Filter(123)

	if res.Passed {
		t.Fatal("Expected non-string input to fail")
	}
}

func TestSemanticFilterAllowed(t *testing.T) {
	f := &SemanticFilter{
		AllowedActions: []string{"PING", "EXEC", "STATUS"},
	}

	res := f.Filter("EXEC nvidia-smi")
	if !res.Passed {
		t.Fatalf("Expected EXEC to be allowed, failed: %s", res.Reason)
	}
}

func TestSemanticFilterBlocked(t *testing.T) {
	f := &SemanticFilter{
		AllowedActions: []string{"PING", "STATUS"},
	}

	res := f.Filter("EXEC rm -rf /")
	if res.Passed {
		t.Fatal("Expected EXEC to be blocked")
	}
}

func TestSemanticFilterCaseInsensitive(t *testing.T) {
	f := &SemanticFilter{
		AllowedActions: []string{"PING"},
	}

	res := f.Filter("ping localhost")
	if !res.Passed {
		t.Fatalf("Expected case-insensitive 'ping' match, failed: %s", res.Reason)
	}
}

func TestBoundaryFilterAllowSafe(t *testing.T) {
	f := &BoundaryFilter{
		Blacklist: []string{"/etc/passwd", "/root/.ssh"},
	}

	res := f.Filter("EXEC echo /home/user/file.txt")
	if !res.Passed {
		t.Fatalf("Expected safe path to pass, failed: %s", res.Reason)
	}
}

func TestBoundaryFilterBlockBlacklisted(t *testing.T) {
	f := &BoundaryFilter{
		Blacklist: []string{"/etc/passwd", "/root/.ssh"},
	}

	res := f.Filter("EXEC cat /etc/passwd")
	if res.Passed {
		t.Fatal("Expected blacklisted path to be blocked")
	}
	if !strings.Contains(res.Reason, "/etc/passwd") {
		t.Errorf("Expected reason to mention /etc/passwd, got '%s'", res.Reason)
	}
}

func TestBoundaryFilterMultipleBlacklisted(t *testing.T) {
	f := &BoundaryFilter{
		Blacklist: []string{"/etc/passwd", "/root/.ssh", "/var/log"},
	}

	tests := []struct {
		input string
		allow bool
	}{
		{"EXEC ls /etc/passwd", false},
		{"EXEC ls /root/.ssh/id_rsa", false},
		{"EXEC cat /var/log/syslog", false},
		{"EXEC echo safe", true},
		{"EXEC ls /tmp/test", true},
	}

	for _, tt := range tests {
		res := f.Filter(tt.input)
		if res.Passed != tt.allow {
			t.Errorf("Input '%s': expected allow=%v, got Passed=%v (reason: %s)", tt.input, tt.allow, res.Passed, res.Reason)
		}
	}
}

func TestContextFilter(t *testing.T) {
	f := &ContextFilter{
		DeviceFingerprint: "OPC-GATEWAY-API",
	}

	res := f.Filter("PING")
	if !res.Passed {
		t.Fatalf("ContextFilter should always pass, failed: %s", res.Reason)
	}

	enriched, ok := res.Cleaned.(string)
	if !ok {
		t.Fatal("Cleaned should be a string")
	}
	if !strings.HasPrefix(enriched, "[OPC-GATEWAY-API]") {
		t.Errorf("Expected device fingerprint prefix, got '%s'", enriched)
	}
}

func TestFullPipelineProcess(t *testing.T) {
	p := NewPurePipeline()
	p.AddFilter(&SyntaxFilter{})
	p.AddFilter(&SemanticFilter{AllowedActions: []string{"PING", "STATUS"}})
	p.AddFilter(&BoundaryFilter{Blacklist: []string{"/etc/passwd"}})
	p.AddFilter(&ContextFilter{DeviceFingerprint: "TEST-API"})

	// Valid input
	result, err := p.Process("  PING localhost  ")
	if err != nil {
		t.Fatalf("Expected valid input to pass pipeline, got error: %v", err)
	}

	cleaned := result.(string)
	if !strings.HasPrefix(cleaned, "[TEST-API]") {
		t.Errorf("Expected context prefix, got '%s'", cleaned)
	}
	if !strings.Contains(cleaned, "PING") {
		t.Errorf("Expected 'PING' in output, got '%s'", cleaned)
	}
}

func TestFullPipelineBlockSemantic(t *testing.T) {
	p := NewPurePipeline()
	p.AddFilter(&SyntaxFilter{})
	p.AddFilter(&SemanticFilter{AllowedActions: []string{"PING", "STATUS"}})
	p.AddFilter(&BoundaryFilter{Blacklist: []string{"/etc/passwd"}})
	p.AddFilter(&ContextFilter{DeviceFingerprint: "TEST"})

	_, err := p.Process("EXEC echo hello")
	if err == nil {
		t.Fatal("Expected EXEC to be blocked by SemanticFilter")
	}
	if !strings.Contains(err.Error(), "SemanticFilter") {
		t.Errorf("Expected SemanticFilter rejection, got: %v", err)
	}
}

func TestFullPipelineBlockBoundary(t *testing.T) {
	p := NewPurePipeline()
	p.AddFilter(&SyntaxFilter{})
	p.AddFilter(&SemanticFilter{AllowedActions: []string{"PING", "EXEC", "STATUS"}})
	p.AddFilter(&BoundaryFilter{Blacklist: []string{"/etc/passwd"}})
	p.AddFilter(&ContextFilter{DeviceFingerprint: "TEST"})

	_, err := p.Process("EXEC cat /etc/passwd")
	if err == nil {
		t.Fatal("Expected boundary violation to be blocked")
	}
	if !strings.Contains(err.Error(), "BoundaryFilter") {
		t.Errorf("Expected BoundaryFilter rejection, got: %v", err)
	}
}

func TestFullPipelineEmptyInput(t *testing.T) {
	p := NewPurePipeline()
	p.AddFilter(&SyntaxFilter{})
	p.AddFilter(&SemanticFilter{AllowedActions: []string{"PING"}})
	p.AddFilter(&BoundaryFilter{Blacklist: []string{"/etc"}})
	p.AddFilter(&ContextFilter{DeviceFingerprint: "TEST"})

	_, err := p.Process("")
	if err == nil {
		t.Fatal("Expected empty input to be blocked")
	}
}

func TestEmptyPipeline(t *testing.T) {
	p := NewPurePipeline()
	result, err := p.Process("hello world")
	if err != nil {
		t.Fatalf("Expected empty pipeline to pass through, got error: %v", err)
	}
	if result.(string) != "hello world" {
		t.Errorf("Expected unchanged 'hello world', got '%v'", result)
	}
}

func TestPipelineLatencyRecorded(t *testing.T) {
	p := NewPurePipeline()
	p.AddFilter(&SyntaxFilter{})

	_, err := p.Process("PING")
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if p.LastLatency <= 0 {
		t.Error("LastLatency should be positive after processing")
	}
}

func TestSyntaxFilterName(t *testing.T) {
	f := &SyntaxFilter{}
	if f.Name() != "SyntaxFilter" {
		t.Errorf("Expected 'SyntaxFilter', got '%s'", f.Name())
	}
}

func TestSemanticFilterName(t *testing.T) {
	f := &SemanticFilter{}
	if f.Name() != "SemanticFilter" {
		t.Errorf("Expected 'SemanticFilter', got '%s'", f.Name())
	}
}

func TestBoundaryFilterName(t *testing.T) {
	f := &BoundaryFilter{}
	if f.Name() != "BoundaryFilter" {
		t.Errorf("Expected 'BoundaryFilter', got '%s'", f.Name())
	}
}

func TestContextFilterName(t *testing.T) {
	f := &ContextFilter{}
	if f.Name() != "ContextFilter" {
		t.Errorf("Expected 'ContextFilter', got '%s'", f.Name())
	}
}
