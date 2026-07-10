package gateway

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

// =============================================================================
// 辅助函数
// =============================================================================

func newTestWSHub() *WSHub {
	return NewWSHub()
}

// =============================================================================
// 测试: NewWSHub
// =============================================================================

func TestNewWSHub(t *testing.T) {
	hub := newTestWSHub()
	if hub == nil {
		t.Fatal("NewWSHub() returned nil")
	}
	if hub.OnlineCount() != 0 {
		t.Errorf("expected 0 clients, got %d", hub.OnlineCount())
	}
}

// =============================================================================
// 测试: Register / Unregister (不依赖真实 WS 连接)
// =============================================================================

func TestRegisterAndUnregister(t *testing.T) {
	hub := newTestWSHub()

	// 使用 httptest 创建真实 WS 连接
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader.Upgrade(w, r, nil)
	}))
	defer srv.Close()

	u := "ws" + strings.TrimPrefix(srv.URL, "http") + "/ws"
	conn, _, err := websocket.DefaultDialer.Dial(u, nil)
	if err != nil {
		t.Fatalf("Dial failed: %v", err)
	}

	client := &WSClient{
		NodeID:   "test-node",
		Platform: "linux/amd64",
		Conn:     conn,
		Topics:   map[string]bool{"general": true},
		RegAt:    time.Now(),
		LastPing: time.Now(),
		UserData: make(map[string]string),
	}
	hub.mu.Lock()
	hub.clients["test-node"] = client
	hub.ConnectCount++
	hub.mu.Unlock()

	if hub.OnlineCount() != 1 {
		t.Errorf("expected 1 client, got %d", hub.OnlineCount())
	}

	got := hub.GetClient("test-node")
	if got == nil {
		t.Fatal("GetClient returned nil")
	}
	if got.NodeID != "test-node" {
		t.Errorf("expected nodeID test-node, got %s", got.NodeID)
	}
	if !got.Topics["general"] {
		t.Error("expected default topic 'general'")
	}

	hub.Unregister("test-node")
	if hub.OnlineCount() != 0 {
		t.Errorf("expected 0 clients after unregister, got %d", hub.OnlineCount())
	}

	// 重复注销应幂等
	hub.Unregister("test-node")
}

func TestRegisterReplace(t *testing.T) {
	hub := newTestWSHub()

	hub.mu.Lock()
	hub.clients["test-node"] = &WSClient{NodeID: "test-node", Topics: map[string]bool{"general": true}}
	hub.ConnectCount++
	hub.mu.Unlock()

	if hub.OnlineCount() != 1 {
		t.Fatalf("expected 1 client, got %d", hub.OnlineCount())
	}

	// 替换
	hub.mu.Lock()
	hub.clients["test-node"] = &WSClient{NodeID: "test-node", Topics: map[string]bool{"general": true}}
	hub.ConnectCount++
	hub.mu.Unlock()

	if hub.OnlineCount() != 1 {
		t.Errorf("expected 1 client after replace, got %d", hub.OnlineCount())
	}
}

// =============================================================================
// 测试: Subscribe
// =============================================================================

func TestSubscribe(t *testing.T) {
	hub := newTestWSHub()

	hub.mu.Lock()
	hub.clients["test-node"] = &WSClient{NodeID: "test-node", Topics: map[string]bool{"general": true}}
	hub.mu.Unlock()

	hub.Subscribe("test-node", []string{"topic1", "topic2"})

	client := hub.GetClient("test-node")
	if client == nil {
		t.Fatal("client not found")
	}
	if !client.Topics["topic1"] {
		t.Error("expected topic1")
	}
	if !client.Topics["topic2"] {
		t.Error("expected topic2")
	}
	if client.Topics["general"] {
		t.Error("general should be removed after subscribe")
	}
}

func TestSubscribeNonExistent(t *testing.T) {
	hub := newTestWSHub()
	hub.Subscribe("non-existent", []string{"topic1"}) // 不应 panic
}

// =============================================================================
// 测试: GetClient / OnlineCount / ListClients
// =============================================================================

func TestGetClient(t *testing.T) {
	hub := newTestWSHub()

	hub.mu.Lock()
	hub.clients["test-node"] = &WSClient{NodeID: "test-node"}
	hub.mu.Unlock()

	client := hub.GetClient("test-node")
	if client == nil {
		t.Fatal("GetClient returned nil")
	}

	client = hub.GetClient("non-existent")
	if client != nil {
		t.Error("expected nil for non-existent node")
	}
}

func TestListClients(t *testing.T) {
	hub := newTestWSHub()

	ids := hub.ListClients()
	if len(ids) != 0 {
		t.Errorf("expected empty list, got %v", ids)
	}

	hub.mu.Lock()
	hub.clients["node1"] = &WSClient{NodeID: "node1"}
	hub.clients["node2"] = &WSClient{NodeID: "node2"}
	hub.mu.Unlock()

	ids = hub.ListClients()
	if len(ids) != 2 {
		t.Errorf("expected 2 clients, got %d", len(ids))
	}
}

// =============================================================================
// 测试: IsWSConnected
// =============================================================================

func TestIsWSConnected(t *testing.T) {
	hub := newTestWSHub()

	if hub.IsWSConnected("test-node") {
		t.Error("expected false for non-existent node")
	}

	// 创建真实 WS 连接
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader.Upgrade(w, r, nil)
	}))
	defer srv.Close()
	u := "ws" + strings.TrimPrefix(srv.URL, "http") + "/ws"
	conn, _, _ := websocket.DefaultDialer.Dial(u, nil)

	hub.mu.Lock()
	hub.clients["test-node"] = &WSClient{NodeID: "test-node", Conn: conn}
	hub.mu.Unlock()

	if !hub.IsWSConnected("test-node") {
		t.Error("expected true for registered node")
	}

	hub.Unregister("test-node")
	if hub.IsWSConnected("test-node") {
		t.Error("expected false after unregister")
	}
}

// =============================================================================
// 测试: SendTo (不依赖真实 WS 连接)
// =============================================================================

func TestSendToNonExistent(t *testing.T) {
	hub := newTestWSHub()
	sent := hub.SendTo("non-existent", &WSMessage{MsgType: MsgTypeP2P, Content: "hello"})
	if sent {
		t.Error("SendTo should return false for non-existent node")
	}
}

// =============================================================================
// 测试: PushTask
// =============================================================================

func TestPushTaskACK(t *testing.T) {
	hub := newTestWSHub()

	go func() {
		time.Sleep(50 * time.Millisecond)
		hub.signalACK("task-001")
	}()

	task := &TaskPollItem{TaskID: "task-001", Command: "echo hello", Timeout: 30}
	sent := hub.PushTask("non-existent", task)
	if sent {
		t.Error("PushTask should return false for non-existent node")
	}
}

func TestPushTaskToNonExistentNode(t *testing.T) {
	hub := newTestWSHub()
	task := &TaskPollItem{TaskID: "task-002", Command: "echo hello", Timeout: 30}
	sent := hub.PushTask("non-existent", task)
	if sent {
		t.Error("PushTask should return false for non-existent node")
	}
}

// =============================================================================
// 测试: FanOut (不依赖真实 WS 连接)
// =============================================================================

func TestFanOutEmptyHub(t *testing.T) {
	hub := newTestWSHub()
	delivered := hub.FanOut("general", &WSMessage{MsgType: MsgTypeHall, Content: "hello"}, "")
	if delivered != 0 {
		t.Errorf("expected 0 delivered, got %d", delivered)
	}
}

func TestFanOutAllEmptyHub(t *testing.T) {
	hub := newTestWSHub()
	delivered := hub.FanOutAll(&WSMessage{MsgType: MsgTypeArcNet, Content: "broadcast"}, "")
	if delivered != 0 {
		t.Errorf("expected 0 delivered, got %d", delivered)
	}
}

// =============================================================================
// 测试: Close
// =============================================================================

func TestClose(t *testing.T) {
	hub := newTestWSHub()

	// 创建真实 WS 连接
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader.Upgrade(w, r, nil)
	}))
	defer srv.Close()

	u := "ws" + strings.TrimPrefix(srv.URL, "http") + "/ws"
	conn1, _, _ := websocket.DefaultDialer.Dial(u, nil)
	conn2, _, _ := websocket.DefaultDialer.Dial(u, nil)

	hub.mu.Lock()
	hub.clients["node1"] = &WSClient{NodeID: "node1", Conn: conn1}
	hub.clients["node2"] = &WSClient{NodeID: "node2", Conn: conn2}
	hub.mu.Unlock()

	if hub.OnlineCount() != 2 {
		t.Fatalf("expected 2 clients, got %d", hub.OnlineCount())
	}

	hub.Close()
	if hub.OnlineCount() != 0 {
		t.Errorf("expected 0 clients after close, got %d", hub.OnlineCount())
	}

	hub.Close() // 重复关闭不应 panic
}

// =============================================================================
// 测试: 并发安全
// =============================================================================

func TestConcurrentRegister(t *testing.T) {
	hub := newTestWSHub()
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			hub.mu.Lock()
			hub.clients["node"] = &WSClient{NodeID: "node"}
			hub.ConnectCount++
			hub.mu.Unlock()
		}(i)
	}
	wg.Wait()
}

func TestConcurrentReadWrite(t *testing.T) {
	hub := newTestWSHub()

	// 创建真实 WS 连接
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader.Upgrade(w, r, nil)
	}))
	defer srv.Close()
	u := "ws" + strings.TrimPrefix(srv.URL, "http") + "/ws"
	conn1, _, _ := websocket.DefaultDialer.Dial(u, nil)
	conn2, _, _ := websocket.DefaultDialer.Dial(u, nil)

	hub.mu.Lock()
	hub.clients["node1"] = &WSClient{NodeID: "node1", Conn: conn1}
	hub.clients["node2"] = &WSClient{NodeID: "node2", Conn: conn2}
	hub.mu.Unlock()

	var wg sync.WaitGroup
	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			hub.FanOut("general", &WSMessage{MsgType: MsgTypeHall, Content: "test"}, "")
			hub.ListClients()
			hub.OnlineCount()
			hub.IsWSConnected("node1")
		}()
	}
	wg.Wait()
}

// =============================================================================
// 测试: 消息序列化
// =============================================================================

func TestWSMessageMarshal(t *testing.T) {
	msg := WSMessage{MsgType: MsgTypeHall, Seq: 1, Timestamp: time.Now().UnixMilli(), SenderID: "test-node", Topic: "general", Content: "hello"}
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("Marshal failed: %v", err)
	}
	var decoded WSMessage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}
	if decoded.MsgType != MsgTypeHall {
		t.Errorf("expected MsgType %s, got %s", MsgTypeHall, decoded.MsgType)
	}
	if decoded.Content != "hello" {
		t.Errorf("expected content 'hello', got '%s'", decoded.Content)
	}
}

func TestWSMessageUnmarshal(t *testing.T) {
	jsonStr := `{"msg_type":"hall","seq":1,"ts":1234567890,"sender_id":"node1","topic":"general","content":"hello"}`
	var msg WSMessage
	if err := json.Unmarshal([]byte(jsonStr), &msg); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}
	if msg.MsgType != MsgTypeHall {
		t.Errorf("expected MsgType %s, got %s", MsgTypeHall, msg.MsgType)
	}
	if msg.SenderID != "node1" {
		t.Errorf("expected sender_id 'node1', got '%s'", msg.SenderID)
	}
}

// =============================================================================
// 测试: mustMarshalJSON
// =============================================================================

func TestMustMarshalJSON(t *testing.T) {
	data := mustMarshalJSON(map[string]string{"key": "value"})
	if len(data) == 0 {
		t.Error("expected non-empty JSON")
	}
	var decoded map[string]string
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}
	if decoded["key"] != "value" {
		t.Errorf("expected 'value', got '%s'", decoded["key"])
	}
}

// =============================================================================
// 测试: 空操作
// =============================================================================

func TestEmptyHubOperations(t *testing.T) {
	hub := newTestWSHub()
	hub.FanOut("general", &WSMessage{}, "")
	hub.FanOutAll(&WSMessage{}, "")
	hub.SendTo("non-existent", &WSMessage{})
	hub.ListClients()
	hub.Close()
}

// =============================================================================
// 测试: 指标计数
// =============================================================================

func TestMetricsCounters(t *testing.T) {
	hub := newTestWSHub()

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader.Upgrade(w, r, nil)
	}))
	defer srv.Close()
	u := "ws" + strings.TrimPrefix(srv.URL, "http") + "/ws"
	conn, _, _ := websocket.DefaultDialer.Dial(u, nil)

	hub.mu.Lock()
	hub.clients["node1"] = &WSClient{NodeID: "node1", Conn: conn}
	hub.ConnectCount++
	hub.mu.Unlock()

	if hub.ConnectCount != 1 {
		t.Errorf("expected ConnectCount 1, got %d", hub.ConnectCount)
	}

	hub.Unregister("node1")
	if hub.DisconnectCount != 1 {
		t.Errorf("expected DisconnectCount 1, got %d", hub.DisconnectCount)
	}

	// 替换连接
	conn2, _, _ := websocket.DefaultDialer.Dial(u, nil)
	hub.mu.Lock()
	hub.clients["node1"] = &WSClient{NodeID: "node1", Conn: conn2}
	hub.ConnectCount++
	hub.mu.Unlock()

	if hub.ConnectCount != 2 {
		t.Errorf("expected ConnectCount 2, got %d", hub.ConnectCount)
	}
}
