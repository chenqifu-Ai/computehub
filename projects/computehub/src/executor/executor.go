package executor

import (
	"fmt"
	"os/exec"
	"time"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// ExecutionResult represents the physical outcome of a code execution
type ExecutionResult struct {
	Stdout     string
	Stderr     string
	ExitCode   int
	Duration   time.Duration
	IsVerified bool
}

// PhysicalValidator defines how to verify the result of an execution
type PhysicalValidator func(result ExecutionResult) bool

// OpcExecutor handles the physical execution and verification loop
type OpcExecutor struct {
	SandboxPath string
}

func NewOpcExecutor(sandboxPath string) *OpcExecutor {
	return &OpcExecutor{
		SandboxPath: sandboxPath,
	}
}

// Execute runs a shell command and returns the physical result
func (e *OpcExecutor) Execute(command string) ExecutionResult {
	start := time.Now()
	
	// In a real production system, this would run in a restricted container/cgroup
	cmd := exec.Command("sh", "-c", command)
	output, err := cmd.CombinedOutput()
	
	duration := time.Since(start)
	exitCode := 0
	if err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode = exitError.ExitCode()
		} else {
			exitCode = 1
		}
	}

	return ExecutionResult{
		Stdout:   string(output),
		Stderr:   "", // CombinedOutput merges both
		ExitCode: exitCode,
		Duration: duration,
	}
}

// VerifyAndLearn implements the "Execute -> Verify -> Learn" loop
func (e *OpcExecutor) VerifyAndLearn(command string, validator PhysicalValidator) (ExecutionResult, bool) {
	// 1. Physical Execution
	result := e.Execute(command)
	
	// 2. Physical Verification
	verified := validator(result)
	result.IsVerified = verified
	
	if !verified {
		logWithTimestamp("[Executor] 🔴 Verification failed for command: %s", command)
		// In a full implementation, this would trigger a 'Gene Update' to the SOP
	} else {
		logWithTimestamp("[Executor] 🟢 Verification passed in %v", result.Duration)
	}
	
	return result, verified
}

// CommonValidators provide standard verification logic
func FileExistsValidator(filePath string) PhysicalValidator {
	return func(res ExecutionResult) bool {
		// Verify if the file actually exists on disk
		cmd := exec.Command("ls", filePath)
		return cmd.Run() == nil
	}
}
