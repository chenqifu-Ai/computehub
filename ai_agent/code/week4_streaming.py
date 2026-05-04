#!/usr/bin/env python3
"""
Week 4 开发：gRPC 通道 + 流式数据传输
执行者：小智 AI 助手
时间：2026-04-22 16:05
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# === 配置 ===
GO_ORCHESTRATION = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go")
STREAMING_DIR = GO_ORCHESTRATION / "internal" / "streaming"

# === 颜色输出 ===
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": Colors.BLUE, "SUCCESS": Colors.GREEN, "WARNING": Colors.YELLOW, "ERROR": Colors.RED}
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def create_streaming_module():
    log("=" * 60, "INFO")
    log("Week 4: 流式数据传输模块", "INFO")
    log("=" * 60, "INFO")
    
    # 1. 创建目录
    log("步骤 1: 创建流式传输目录", "INFO")
    STREAMING_DIR.mkdir(parents=True, exist_ok=True)
    log(f"  ✅ 创建 {STREAMING_DIR}", "SUCCESS")
    
    # 2. 创建流式传输核心（纯 Go 标准库）
    log("步骤 2: 创建流式传输核心", "INFO")
    streaming_go = '''package streaming

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

// StreamType 流类型
type StreamType string

const (
	StreamTypeLogs    StreamType = "logs"    // 日志流
	StreamTypeMetrics StreamType = "metrics" // 指标流
	StreamTypeEvents  StreamType = "events"  // 事件流
	StreamTypeTasks   StreamType = "tasks"   // 任务流
)

// StreamMessage 流消息
type StreamMessage struct {
	Type      StreamType    `json:"type"`
	Timestamp time.Time     `json:"timestamp"`
	Sequence  int64         `json:"sequence"`
	Data      interface{}   `json:"data"`
}

// StreamConfig 流配置
type StreamConfig struct {
	BufferSize     int           `json:"buffer_size"`      // 缓冲区大小
	FlushInterval  time.Duration `json:"flush_interval"`   // 刷新间隔
	MaxConnections int           `json:"max_connections"`  // 最大连接数
	KeepAlive      time.Duration `json:"keep_alive"`       // 保活时间
}

// DefaultConfig 默认配置
func DefaultConfig() *StreamConfig {
	return &StreamConfig{
		BufferSize:     100,
		FlushInterval:  100 * time.Millisecond,
		MaxConnections: 1000,
		KeepAlive:      30 * time.Second,
	}
}

// StreamServer 流式服务器
type StreamServer struct {
	mu          sync.RWMutex
	config      *StreamConfig
	clients     map[string]*StreamClient
	broadcast   chan *StreamMessage
	subscribers map[StreamType]map[string]*StreamClient
	sequence    int64
}

// StreamClient 流客户端
type StreamClient struct {
	ID         string
	Type       StreamType
	Conn       io.Writer
	Done       chan struct{}
	Messages   chan *StreamMessage
	LastActive time.Time
}

// NewStreamServer 创建流式服务器
func NewStreamServer(config *StreamConfig) *StreamServer {
	if config == nil {
		config = DefaultConfig()
	}
	return &StreamServer{
		config:      config,
		clients:     make(map[string]*StreamClient),
		broadcast:   make(chan *StreamMessage, config.BufferSize),
		subscribers: make(map[StreamType]map[string]*StreamClient),
	}
}

// HandleHTTP 处理 HTTP 流请求（SSE - Server-Sent Events）
func (s *StreamServer) HandleHTTP(w http.ResponseWriter, r *http.Request) {
	// 设置 SSE 头
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("X-Accel-Buffering", "no")

	// 获取流类型
	streamType := StreamType(r.URL.Query().Get("type"))
	if streamType == "" {
		streamType = StreamTypeEvents
	}

	// 创建客户端
	clientID := fmt.Sprintf("client-%d", time.Now().UnixNano())
	client := &StreamClient{
		ID:         clientID,
		Type:       streamType,
		Conn:       w.(io.Writer),
		Done:       make(chan struct{}),
		Messages:   make(chan *StreamMessage, s.config.BufferSize),
		LastActive: time.Now(),
	}

	// 注册客户端
	s.RegisterClient(client)
	defer s.UnregisterClient(client)

	// 发送连接成功消息
	fmt.Fprintf(w, "data: %s\\n\\n", s.encodeMessage(&StreamMessage{
		Type:      "system",
		Timestamp: time.Now(),
		Data:      map[string]string{"status": "connected", "client_id": clientID},
	}))
	w.(http.Flusher).Flush()

	// 保持连接
	flusher := w.(http.Flusher)
	for {
		select {
		case msg, ok := <-client.Messages:
			if !ok {
				return
			}
			fmt.Fprintf(w, "data: %s\\n\\n", s.encodeMessage(msg))
			flusher.Flush()
		case <-r.Context().Done():
			return
		case <-time.After(s.config.KeepAlive):
			// 发送心跳
			fmt.Fprintf(w, ": heartbeat\\n\\n")
			flusher.Flush()
		}
	}
}

// RegisterClient 注册客户端
func (s *StreamServer) RegisterClient(client *StreamClient) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.clients[client.ID] = client

	if _, exists := s.subscribers[client.Type]; !exists {
		s.subscribers[client.Type] = make(map[string]*StreamClient)
	}
	s.subscribers[client.Type][client.ID] = client
}

// UnregisterClient 注销客户端
func (s *StreamServer) UnregisterClient(client *StreamClient) {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.clients, client.ID)
	if subscribers, exists := s.subscribers[client.Type]; exists {
		delete(subscribers, client.ID)
	}
	close(client.Done)
}

// Publish 发布消息
func (s *StreamServer) Publish(streamType StreamType, data interface{}) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	s.sequence++
	msg := &StreamMessage{
		Type:      streamType,
		Timestamp: time.Now(),
		Sequence:  s.sequence,
		Data:      data,
	}

	// 广播
	s.broadcast <- msg

	// 发送给特定类型的订阅者
	if subscribers, exists := s.subscribers[streamType]; exists {
		for _, client := range subscribers {
			select {
			case client.Messages <- msg:
			default:
				// 缓冲区满，跳过
			}
		}
	}
}

// Broadcast 广播消息到所有客户端
func (s *StreamServer) Broadcast(data interface{}) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	s.sequence++
	msg := &StreamMessage{
		Type:      "broadcast",
		Timestamp: time.Now(),
		Sequence:  s.sequence,
		Data:      data,
	}

	for _, client := range s.clients {
		select {
		case client.Messages <- msg:
		default:
			// 缓冲区满，跳过
		}
	}
}

// encodeMessage 编码消息为 SSE 格式
func (s *StreamServer) encodeMessage(msg *StreamMessage) string {
	jsonData, _ := json.Marshal(msg)
	return string(jsonData)
}

// GetStats 获取服务器统计
func (s *StreamServer) GetStats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	typeStats := make(map[string]int)
	for streamType, subscribers := range s.subscribers {
		typeStats[string(streamType)] = len(subscribers)
	}

	return map[string]interface{}{
		"total_clients":  len(s.clients),
		"subscribers":    typeStats,
		"sequence":       s.sequence,
		"buffer_size":    s.config.BufferSize,
		"max_connections": s.config.MaxConnections,
	}
}

// StreamLogger 日志流助手
type StreamLogger struct {
	server *StreamServer
}

// NewStreamLogger 创建日志流
func (s *StreamServer) NewStreamLogger() *StreamLogger {
	return &StreamLogger{server: s}
}

// Info 发送信息日志
func (l *StreamLogger) Info(message string, data ...interface{}) {
	l.server.Publish(StreamTypeLogs, map[string]interface{}{
		"level":   "info",
		"message": message,
		"data":    data,
	})
}

// Error 发送错误日志
func (l *StreamLogger) Error(message string, data ...interface{}) {
	l.server.Publish(StreamTypeLogs, map[string]interface{}{
		"level":   "error",
		"message": message,
		"data":    data,
	})
}

// Warn 发送警告日志
func (l *StreamLogger) Warn(message string, data ...interface{}) {
	l.server.Publish(StreamTypeLogs, map[string]interface{}{
		"level":   "warn",
		"message": message,
		"data":    data,
	})
}

// StreamMetrics 指标流助手
type StreamMetrics struct {
	server *StreamServer
}

// NewStreamMetrics 创建指标流
func (s *StreamServer) NewStreamMetrics() *StreamMetrics {
	return &StreamMetrics{server: s}
}

// Record 记录指标
func (m *StreamMetrics) Record(name string, value float64, tags ...string) {
	m.server.Publish(StreamTypeMetrics, map[string]interface{}{
		"name":  name,
		"value": value,
		"tags":  tags,
	})
}

// StreamEvents 事件流助手
type StreamEvents struct {
	server *StreamServer
}

// NewStreamEvents 创建事件流
func (s *StreamServer) NewStreamEvents() *StreamEvents {
	return &StreamEvents{server: s}
}

// Emit 发送事件
func (e *StreamEvents) Emit(event string, data interface{}) {
	e.server.Publish(StreamTypeEvents, map[string]interface{}{
		"event": event,
		"data":  data,
	})
}

// TaskStream 任务流助手
type TaskStream struct {
	server *StreamServer
}

// NewTaskStream 创建任务流
func (s *StreamServer) NewTaskStream() *TaskStream {
	return &TaskStream{server: s}
}

// TaskUpdate 任务更新
func (t *TaskStream) TaskUpdate(taskID string, status string, progress float64) {
	t.server.Publish(StreamTypeTasks, map[string]interface{}{
		"task_id":  taskID,
		"status":   status,
		"progress": progress,
	})
}

// TaskComplete 任务完成
func (t *TaskStream) TaskComplete(taskID string, result interface{}) {
	t.server.Publish(StreamTypeTasks, map[string]interface{}{
		"task_id":  taskID,
		"status":   "completed",
		"progress": 100.0,
		"result":   result,
	})
}

// TaskFailed 任务失败
func (t *TaskStream) TaskFailed(taskID string, error string) {
	t.server.Publish(StreamTypeTasks, map[string]interface{}{
		"task_id":  taskID,
		"status":   "failed",
		"progress": 0.0,
		"error":    error,
	})
}

// WebSocket 支持（可选，需要 gorilla/websocket 外部库）
// 这里用纯标准库实现简单的轮询替代方案

// PollHandler 轮询处理器
func (s *StreamServer) PollHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	clientID := r.URL.Query().Get("client_id")
	lastSeq := r.URL.Query().Get("last_seq")

	if clientID == "" {
		http.Error(w, "client_id required", http.StatusBadRequest)
		return
	}

	s.mu.RLock()
	client, exists := s.clients[clientID]
	s.mu.RUnlock()

	if !exists {
		http.Error(w, "client not found", http.StatusNotFound)
		return
	}

	// 获取最新消息
	var messages []*StreamMessage
	select {
	case msg := <-client.Messages:
		messages = append(messages, msg)
	default:
		// 无新消息
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"messages": messages,
		"last_seq": s.sequence,
	})
}
'''
    (STREAMING_DIR / "streaming.go").write_text(streaming_go, encoding='utf-8')
    log("  ✅ 创建 internal/streaming/streaming.go", "SUCCESS")
    
    # 3. 更新 handlers 添加流式 API
    log("步骤 3: 更新 handlers 添加流式 API", "INFO")
    handlers_path = GO_ORCHESTRATION / "internal" / "handlers" / "handlers.go"
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    # 添加导入
    if '"github.com/computehub/opc/orchestration/internal/streaming"' not in handlers_content:
        handlers_content = handlers_content.replace(
            '"github.com/computehub/opc/orchestration/internal/statemachine"',
            '"github.com/computehub/opc/orchestration/internal/statemachine"\n\t"github.com/computehub/opc/orchestration/internal/streaming"'
        )
    
    # 添加 streamServer 字段
    handlers_content = handlers_content.replace(
        'statemachine *statemachine.StateMachine',
        'statemachine  *statemachine.StateMachine\n\tstreamServer  *streaming.StreamServer'
    )
    
    # 更新 NewHandler
    handlers_content = handlers_content.replace(
        'statemachine: statemachine.NewStateMachine(statemachine.DefaultConfig()),',
        'statemachine:  statemachine.NewStateMachine(statemachine.DefaultConfig()),\n\t\tstreamServer:  streaming.NewStreamServer(streaming.DefaultConfig()),'
    )
    
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新 internal/handlers/handlers.go (添加流式服务器)", "SUCCESS")
    
    # 4. 添加流式 API 端点
    log("步骤 4: 添加流式 API 端点", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    stream_apis = '''
// StreamLogs SSE 日志流
func (h *Handler) StreamLogs(w http.ResponseWriter, r *http.Request) {
	h.streamServer.HandleHTTP(w, r)
}

// StreamMetrics SSE 指标流
func (h *Handler) StreamMetrics(w http.ResponseWriter, r *http.Request) {
	h.streamServer.HandleHTTP(w, r)
}

// StreamEvents SSE 事件流
func (h *Handler) StreamEvents(w http.ResponseWriter, r *http.Request) {
	h.streamServer.HandleHTTP(w, r)
}

// StreamTasks SSE 任务流
func (h *Handler) StreamTasks(w http.ResponseWriter, r *http.Request) {
	h.streamServer.HandleHTTP(w, r)
}

// GetStreamStats 获取流式服务器状态
func (h *Handler) GetStreamStats(w http.ResponseWriter, r *http.Request) {
	stats := h.streamServer.GetStats()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// EmitLog 发送日志（测试用）
func (h *Handler) EmitLog(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Level   string      `json:"level"`
		Message string      `json:"message"`
		Data    interface{} `json:"data"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	logger := h.streamServer.NewStreamLogger()
	switch req.Level {
	case "error":
		logger.Error(req.Message, req.Data)
	case "warn":
		logger.Warn(req.Message, req.Data)
	default:
		logger.Info(req.Message, req.Data)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// EmitEvent 发送事件（测试用）
func (h *Handler) EmitEvent(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Event string      `json:"event"`
		Data  interface{} `json:"data"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	events := h.streamServer.NewStreamEvents()
	events.Emit(req.Event, req.Data)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}
'''
    
    handlers_content = handlers_content.rstrip() + '\n' + stream_apis
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 添加流式 API 端点", "SUCCESS")
    
    # 5. 更新路由注册
    log("步骤 5: 更新路由注册", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    old_mux = '''mux.HandleFunc("GET /api/tasks/stats", h.GetTaskStats)

	return mux
}'''
    
    new_mux = '''mux.HandleFunc("GET /api/tasks/stats", h.GetTaskStats)

	// 流式传输端点
	mux.HandleFunc("GET /api/stream/logs", h.StreamLogs)
	mux.HandleFunc("GET /api/stream/metrics", h.StreamMetrics)
	mux.HandleFunc("GET /api/stream/events", h.StreamEvents)
	mux.HandleFunc("GET /api/stream/tasks", h.StreamTasks)
	mux.HandleFunc("GET /api/stream/stats", h.GetStreamStats)
	mux.HandleFunc("POST /api/stream/log", h.EmitLog)
	mux.HandleFunc("POST /api/stream/event", h.EmitEvent)

	return mux
}'''
    
    handlers_content = handlers_content.replace(old_mux, new_mux)
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新路由注册", "SUCCESS")
    
    # 6. 创建测试脚本
    log("步骤 6: 创建测试脚本", "INFO")
    test_streaming_py = '''#!/usr/bin/env python3
"""测试流式数据传输"""

import requests
import time
import threading

BASE_URL = "http://localhost:8080"

def test_stream_stats():
    """查看流式服务器状态"""
    print("\\n=== 流式服务器状态 ===")
    
    resp = requests.get(f"{BASE_URL}/api/stream/stats")
    
    if resp.status_code == 200:
        status = resp.json()
        print(f"  总客户端：{status.get('total_clients', 0)}")
        print(f"  序列号：{status.get('sequence', 0)}")
        print(f"  缓冲区：{status.get('buffer_size', 0)}")

def test_emit_log():
    """发送测试日志"""
    print("\\n=== 发送测试日志 ===")
    
    payload = {
        "level": "info",
        "message": "测试日志消息",
        "data": {"test": True, "timestamp": time.time()}
    }
    
    resp = requests.post(f"{BASE_URL}/api/stream/log", json=payload)
    
    if resp.status_code == 200:
        print("  ✅ 日志发送成功")
    else:
        print(f"  ❌ 日志发送失败：{resp.text}")

def test_emit_event():
    """发送测试事件"""
    print("\\n=== 发送测试事件 ===")
    
    payload = {
        "event": "task_started",
        "data": {"task_id": "test-001", "name": "测试任务"}
    }
    
    resp = requests.post(f"{BASE_URL}/api/stream/event", json=payload)
    
    if resp.status_code == 200:
        print("  ✅ 事件发送成功")
    else:
        print(f"  ❌ 事件发送失败：{resp.text}")

def test_sse_stream():
    """测试 SSE 流（非阻塞）"""
    print("\\n=== 测试 SSE 流（5 秒）===")
    
    def listen_stream():
        try:
            resp = requests.get(f"{BASE_URL}/api/stream/events", stream=True, timeout=10)
            for line in resp.iter_lines():
                if line:
                    print(f"  📡 收到：{line.decode()}")
        except Exception as e:
            print(f"  流结束：{e}")
    
    # 后台监听
    thread = threading.Thread(target=listen_stream, daemon=True)
    thread.start()
    
    # 发送几个事件
    time.sleep(1)
    for i in range(3):
        test_emit_event()
        time.sleep(0.5)
    
    time.sleep(2)

if __name__ == "__main__":
    print("=" * 60)
    print("流式数据传输测试")
    print("=" * 60)
    
    try:
        # 查看状态
        test_stream_stats()
        
        # 发送测试日志
        test_emit_log()
        
        # 发送测试事件
        test_emit_event()
        
        # 测试 SSE 流
        test_sse_stream()
        
        # 再次查看状态
        test_stream_stats()
        
        print("\\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\\n❌ 测试失败：{e}")
'''
    (GO_ORCHESTRATION / "test_streaming.py").write_text(test_streaming_py, encoding='utf-8')
    log("  ✅ 创建 test_streaming.py", "SUCCESS")
    
    log("", "INFO")
    log("=" * 60, "INFO")
    log("流式数据传输模块创建完成！", "SUCCESS")
    log(f"目录：{GO_ORCHESTRATION}", "SUCCESS")
    log("=" * 60, "INFO")
    
    return True

if __name__ == "__main__":
    success = create_streaming_module()
    sys.exit(0 if success else 1)
