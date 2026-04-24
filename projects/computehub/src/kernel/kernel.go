package kernel

import (
	"fmt"
	"sync"
	"time"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// State represents the physical state of the system at a given timestamp
type State struct {
	Timestamp int64
	Payload   map[string]interface{}
}

// OpcKernel is the deterministic scheduler kernel
type OpcKernel struct {
	Mu            sync.RWMutex
	stateMirror   []State
	maxStates     int
	LinearQueue   chan Command
	LastLatency   time.Duration
}

// Command represents a linearized system instruction
type Command struct {
	ID        string
	Action    string
	Payload   interface{}
	Response  chan Response
}

type Response struct {
	Success bool
	Data    interface{}
	Error   error
}

// NewKernel initializes a new deterministic kernel
func NewKernel(bufferSize int, maxStateHistory int) *OpcKernel {
	return &OpcKernel{
		stateMirror: make([]State, 0),
		maxStates:   maxStateHistory,
		LinearQueue: make(chan Command, bufferSize),
	}
}

// Start begins the linearized command processing loop
func (k *OpcKernel) Start() {
	go func() {
		for cmd := range k.LinearQueue {
			k.processCommand(cmd)
		}
	}()
}

// processCommand executes commands linearly to eliminate race conditions
func (k *OpcKernel) processCommand(cmd Command) {
	start := time.Now()
	
	// 1. Snapshot current state before execution
	k.snapshotState()

	// 2. Physical Execution (Deterministic path)
	logWithTimestamp("[Kernel] Processing Command %s: %s", cmd.ID, cmd.Action)
	
	// Simplified execution logic for v0.1 Alpha
	var resp Response
	switch cmd.Action {
	case "PING":
		resp = Response{Success: true, Data: "PONG"}
	case "STATUS":
		resp = Response{Success: true, Data: "System Healthy | Kernel: Deterministic | Memory: Stable"}
	default:
		resp = Response{Success: false, Error: fmt.Errorf("unknown action: %s", cmd.Action)}
	}

	duration := time.Since(start)
	k.Mu.Lock()
	k.LastLatency = duration
	k.Mu.Unlock()
	logWithTimestamp("[Kernel] Command %s completed in %v", cmd.ID, duration)
	
	cmd.Response <- resp
}

// snapshotState saves the current physical state to the mirror for rollback
func (k *OpcKernel) snapshotState() {
	k.Mu.Lock()
	defer k.Mu.Unlock()

	state := State{
		Timestamp: time.Now().UnixNano(),
		Payload:   make(map[string]interface{}),
	}
	
	k.stateMirror = append(k.stateMirror, state)
	if len(k.stateMirror) > k.maxStates {
		k.stateMirror = k.stateMirror[1:]
	}
}

// Dispatch sends a command to the linear queue
func (k *OpcKernel) Dispatch(id, action string, payload interface{}) chan Response {
	respChan := make(chan Response, 1)
	k.LinearQueue <- Command{
		ID:       id,
		Action:   action,
		Payload:  payload,
		Response: respChan,
	}
	return respChan
}
