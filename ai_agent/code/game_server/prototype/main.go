package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// Player 玩家结构体
type Player struct {
	ID       string          `json:"id"`
	Name     string          `json:"name"`
	Class    string          `json:"class"`  // 职业: mechanic, assassin, guardian, demolisher
	Health   int             `json:"health"`
	Mana     int             `json:"mana"`
	Conn     *websocket.Conn `json:"-"`
	RoomID   string          `json:"room_id"`
}

// GameRoom 游戏房间
type GameRoom struct {
	ID        string    `json:"id"`
	Players   []*Player `json:"players"`
	CreatedAt time.Time `json:"created_at"`
	IsPlaying bool      `json:"is_playing"`
}

// GameServer 游戏服务器
type GameServer struct {
	Rooms   map[string]*GameRoom
	Players map[string]*Player
	mu      sync.RWMutex
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

// NewGameServer 创建新的游戏服务器
func NewGameServer() *GameServer {
	return &GameServer{
		Rooms:   make(map[string]*GameRoom),
		Players: make(map[string]*Player),
	}
}

// handleWebSocket WebSocket连接处理
func (gs *GameServer) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	// 处理玩家消息
	for {
		var msg map[string]interface{}
		err := conn.ReadJSON(&msg)
		if err != nil {
			log.Printf("Read error: %v", err)
			break
		}

		gs.handleMessage(conn, msg)
	}
}

// handleMessage 处理玩家消息
func (gs *GameServer) handleMessage(conn *websocket.Conn, msg map[string]interface{}) {
	gs.mu.Lock()
	defer gs.mu.Unlock()

	msgType, ok := msg["type"].(string)
	if !ok {
		return
	}

	switch msgType {
	case "join":
		gs.handleJoin(conn, msg)
	case "leave":
		gs.handleLeave(msg)
	case "action":
		gs.handleAction(msg)
	case "chat":
		gs.handleChat(msg)
	}
}

// handleJoin 处理玩家加入
func (gs *GameServer) handleJoin(conn *websocket.Conn, msg map[string]interface{}) {
	playerID, _ := msg["player_id"].(string)
	playerName, _ := msg["player_name"].(string)
	playerClass, _ := msg["player_class"].(string)

	player := &Player{
		ID:     playerID,
		Name:   playerName,
		Class:  playerClass,
		Health: 100,
		Mana:   50,
		Conn:   conn,
	}

	gs.Players[playerID] = player

	// 寻找或创建房间
	room := gs.findOrCreateRoom(player)
	player.RoomID = room.ID

	// 通知玩家加入成功
	conn.WriteJSON(map[string]interface{}{
		"type": "joined",
		"room": room,
	})

	// 通知房间内其他玩家
	gs.broadcastToRoom(room.ID, map[string]interface{}{
		"type": "player_joined",
		"player": player,
	})
}

// findOrCreateRoom 寻找或创建房间
func (gs *GameServer) findOrCreateRoom(player *Player) *GameRoom {
	// 寻找未满的房间
	for _, room := range gs.Rooms {
		if len(room.Players) < 4 && !room.IsPlaying {
			room.Players = append(room.Players, player)
			return room
		}
	}

	// 创建新房间
	roomID := fmt.Sprintf("room_%d", time.Now().Unix())
	room := &GameRoom{
		ID:        roomID,
		Players:   []*Player{player},
		CreatedAt: time.Now(),
		IsPlaying: false,
	}
	gs.Rooms[roomID] = room
	return room
}

// broadcastToRoom 向房间内广播消息
func (gs *GameServer) broadcastToRoom(roomID string, msg map[string]interface{}) {
	room, exists := gs.Rooms[roomID]
	if !exists {
		return
	}

	for _, player := range room.Players {
		if player.Conn != nil {
			player.Conn.WriteJSON(msg)
		}
	}
}

// handleLeave 处理玩家离开
func (gs *GameServer) handleLeave(msg map[string]interface{}) {
	playerID, _ := msg["player_id"].(string)
	// 实现离开逻辑
}

// handleAction 处理玩家动作
func (gs *GameServer) handleAction(msg map[string]interface{}) {
	// 实现游戏动作处理
}

// handleChat 处理聊天消息
func (gs *GameServer) handleChat(msg map[string]interface{}) {
	// 实现聊天功能
}

func main() {
	gs := NewGameServer()

	// 静态文件服务
	fs := http.FileServer(http.Dir("./static"))
	http.Handle("/", fs)

	// WebSocket端点
	http.HandleFunc("/ws", gs.handleWebSocket)

	// API端点
	http.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		gs.mu.RLock()
		defer gs.mu.RUnlock()

		status := map[string]interface{}{
			"players": len(gs.Players),
			"rooms":   len(gs.Rooms),
			"time":    time.Now().Format(time.RFC3339),
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(status)
	})

	log.Println("游戏服务器启动在 :8080 端口")
	log.Fatal(http.ListenAndServe(":8080", nil))
}