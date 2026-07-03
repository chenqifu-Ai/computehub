// Copyright (c) 2026 ComputeHub. All rights reserved.
// WebSocket Tunnel — TCP-over-WebSocket 隧道
//
// 本文件是 ComputeHub WSHub 的隧道转发层。
// 隧道 client/server 独立 binary 见 cmd/tunnel/main.go。
//
// 架构:
//   TCP Client ←→ tunnel-client ←WS→ WSHub ←WS→ tunnel-server ←TCP→ Target
//
// 消息流:
//   tunnel-client 收到 TCP 连接 → 分配 session_id → WS tunnel_data → WSHub 转发
//   → tunnel-server 收到 WS tunnel_data → 写入对应 TCP 连接
//
// 消息格式:
//   {
//     "msg_type": "tunnel_data",
//     "sender_id": "tunnel-client",
//     "target_node": "tunnel-server",
//     "session_id": "sess-001",
//     "data": "<base64>",       // TCP 数据（base64 编码）
//     "close": false            // 是否关闭此 session
//   }
//
// 使用场景:
//   - 打通 Windows OpenClaw → ECS OpenClaw（绕过 NAT/防火墙）
//   - 任意两个无法直连的 TCP 服务通过 WS Hub 中继
//   - 无需暴露公网端口，仅需 WS Hub 可达

package gateway

import (
	"encoding/base64"
	"encoding/json"
	"log"
	"time"
)

// Tunnel 消息类型常量
const (
	MsgTypeTunnelData = "tunnel_data" // TCP 隧道数据
)

// WSMessage 新增字段（在 gateway_ws.go 的 WSMessage 结构体中）
// 这些字段已存在:
//   SessionID string  — 用作 tunnel session_id
//   TargetNode string — 用作 tunnel 目标节点
//   Content string    — 用作 base64 编码的 TCP 数据
//
// 新增字段（通过 Payload 传递）:
// TunnelClose bool — 是否关闭 session

// TunnelPayload WSMessage.Payload 中携带的额外字段
type TunnelPayload struct {
	Close bool `json:"close,omitempty"` // 是否关闭 session
}

// HandleTunnelData 处理隧道数据消息
// 在 readPump 中调用: 收到 tunnel_data → 转发给 target_node
func (h *WSHub) HandleTunnelData(envelope *WSMessage) {
	if envelope.TargetNode == "" {
		log.Printf("📡 Tunnel: 收到 tunnel_data 但 target_node 为空 (from=%s)", envelope.SenderID)
		return
	}

	// 补充时间戳
	if envelope.Timestamp == 0 {
		envelope.Timestamp = time.Now().UnixMilli()
	}

	// 转发给目标节点
	sent := h.SendTo(envelope.TargetNode, envelope)
	if !sent {
		log.Printf("📡 Tunnel: 转发 tunnel_data 到 %s 失败 (session=%s)", envelope.TargetNode, envelope.SessionID)
	}
}

// EncodeTunnelData 编码隧道数据为 WSMessage
func EncodeTunnelData(sessionID, targetNode string, data []byte, close bool) *WSMessage {
	msg := &WSMessage{
		MsgType:    MsgTypeTunnelData,
		SenderID:   "tunnel",
		TargetNode: targetNode,
		SessionID:  sessionID,
		Content:    base64.StdEncoding.EncodeToString(data),
		Timestamp:  time.Now().UnixMilli(),
	}
	if close {
		msg.Payload = mustMarshalJSON(TunnelPayload{Close: true})
	}
	return msg
}

// DecodeTunnelData 解码隧道数据
func DecodeTunnelData(msg *WSMessage) (data []byte, close bool, err error) {
	data, err = base64.StdEncoding.DecodeString(msg.Content)
	if err != nil {
		return nil, false, err
	}
	if len(msg.Payload) > 0 {
		var p TunnelPayload
		if err := json.Unmarshal(msg.Payload, &p); err == nil {
			close = p.Close
		}
	}
	return data, close, nil
}
