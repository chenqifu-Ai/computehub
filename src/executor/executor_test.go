package executor

import (
	"fmt"
	"os"
	"strings"
	"testing"
)

func TestNewExecutor(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	if ex.SandboxPath != "/tmp/opc-sandbox" {
		t.Errorf("Expected sandbox /tmp/opc-sandbox, got %s", ex.SandboxPath)
	}
}

func TestExecuteSimpleCommand(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	res := ex.Execute("echo 'hello world'")

	if res.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", res.ExitCode)
	}
	if !strings.Contains(res.Stdout, "hello world") {
		t.Errorf("Expected output 'hello world', got '%s'", res.Stdout)
	}
	if res.Duration <= 0 {
		t.Error("Duration should be positive")
	}
}

func TestExecuteFailureCommand(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	res := ex.Execute("exit 42")

	if res.ExitCode != 42 {
		t.Errorf("Expected exit code 42, got %d", res.ExitCode)
	}
}

func TestExecuteNonExistentCommand(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	res := ex.Execute("this_command_does_not_exist_xyzzy")

	if res.ExitCode == 0 {
		t.Error("Expected non-zero exit code for non-existent command")
	}
}

func TestVerifyAndLearnSuccess(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")

	validator := func(res ExecutionResult) bool {
		return res.ExitCode == 0
	}

	res, verified := ex.VerifyAndLearn("echo 'success'", validator)
	if !verified {
		t.Error("Expected verification to pass")
	}
	if !res.IsVerified {
		t.Error("Result should be marked verified")
	}
	if res.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", res.ExitCode)
	}
}

func TestVerifyAndLearnFailure(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")

	validator := func(res ExecutionResult) bool {
		return res.ExitCode == 0
	}

	res, verified := ex.VerifyAndLearn("exit 1", validator)
	if verified {
		t.Error("Expected verification to fail")
	}
	if res.IsVerified {
		t.Error("Result should not be marked verified")
	}
}

func TestFileExistsValidator(t *testing.T) {
	tmpFile := "/tmp/opc-test-file-exists"
	os.WriteFile(tmpFile, []byte("test"), 0644)
	defer os.Remove(tmpFile)

	validator := FileExistsValidator(tmpFile)
	res := ExecutionResult{}
	if !validator(res) {
		t.Error("FileExistsValidator should return true for existing file")
	}

	notExistValidator := FileExistsValidator("/tmp/non_existent_file_xyzzy")
	if notExistValidator(res) {
		t.Error("FileExistsValidator should return false for non-existent file")
	}
}

func TestExecuteEmptyCommand(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	res := ex.Execute("")

	if res.ExitCode != 0 {
		t.Error("Empty command may or may not fail, but should not panic")
	}
}

func TestExecuteLongCommand(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	cmd := fmt.Sprintf("echo '%s'", strings.Repeat("a", 10000))
	res := ex.Execute(cmd)

	if res.ExitCode != 0 {
		t.Errorf("Expected exit code 0 for long command, got %d", res.ExitCode)
	}
	if len(res.Stdout) < 10000 {
		t.Errorf("Expected long output, got %d chars", len(res.Stdout))
	}
}

func TestCustomValidator(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")

	// Validator that checks output contains specific string
	containsHello := func(res ExecutionResult) bool {
		return strings.Contains(res.Stdout, "hello")
	}

	_, verified := ex.VerifyAndLearn("echo 'hello world'", containsHello)
	if !verified {
		t.Error("Expected validator to pass for 'hello world'")
	}

	_, verified = ex.VerifyAndLearn("echo 'goodbye world'", containsHello)
	if verified {
		t.Error("Expected validator to fail for 'goodbye world'")
	}
}

func TestConcurrentExecution(t *testing.T) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	done := make(chan bool, 10)

	for i := 0; i < 10; i++ {
		go func(n int) {
			res := ex.Execute(fmt.Sprintf("echo 'concurrent-%d'", n))
			if res.ExitCode != 0 {
				t.Errorf("Concurrent execution %d failed with code %d", n, res.ExitCode)
			}
			done <- true
		}(i)
	}

	for i := 0; i < 10; i++ {
		<-done
	}
}

func BenchmarkExecute(b *testing.B) {
	ex := NewOpcExecutor("/tmp/opc-sandbox")
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ex.Execute("echo 'benchmark'")
	}
}
