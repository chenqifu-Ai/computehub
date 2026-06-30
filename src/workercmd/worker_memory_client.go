// Package workercmd — Worker 记忆同步客户端
// SPEC-DMEM-001 Phase 1: 每次 SaveEpisode/SaveKnowledge 后异步同步到 Gateway
//
// 设计原则:
//   - 写时同步：每次本地记忆变更后异步 POST 到 Gateway
//   - 启动时拉取：Worker 启动时拉取 Gateway 上的共享记忆
//   - 最终一致性：允许短暂延迟，不阻塞本地操作

package workercmd

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/agent"
)

// MemorySyncClient 记忆同步客户端
type MemorySyncClient struct {
	gatewayURL string
	httpClient *http.Client
	nodeID     string
	mu         sync.Mutex
	enabled    bool
	lastSync   time.Time
}

// NewMemorySyncClient 创建记忆同步客户端
func NewMemorySyncClient(gatewayURL, nodeID string) *MemorySyncClient {
	return &MemorySyncClient{
		gatewayURL: strings.TrimRight(gatewayURL, "/"),
		nodeID:     nodeID,
		httpClient: &http.Client{Timeout: 10 * time.Second},
		enabled:    true,
	}
}

// Enable/Disable 控制开关
func (msc *MemorySyncClient) Enable()  { msc.mu.Lock(); defer msc.mu.Unlock(); msc.enabled = true }
func (msc *MemorySyncClient) Disable() { msc.mu.Lock(); defer msc.mu.Unlock(); msc.enabled = false }

// SyncEpisode 同步一条经验到 Gateway
// 异步非阻塞，失败不重试（最终一致性）
func (msc *MemorySyncClient) SyncEpisode(task, result string, success bool, learned string) {
	msc.mu.Lock()
	enabled := msc.enabled
	msc.mu.Unlock()
	if !enabled {
		return
	}

	ep := map[string]interface{}{
		"node_id": msc.nodeID,
		"episodes": []map[string]interface{}{
			{
				"task":      task,
				"result":    result,
				"success":   success,
				"learned":   learned,
				"timestamp": time.Now(),
				"strength":  1.0,
			},
		},
	}

	go func() {
		body, _ := json.Marshal(ep)
		resp, err := msc.httpClient.Post(
			msc.gatewayURL+"/api/v1/memory/sync",
			"application/json",
			bytes.NewReader(body),
		)
		if err != nil {
			fmt.Printf(" [MemorySync:%s] ⚠️ 同步经验失败: %v\n", msc.nodeID, err)
			return
		}
		defer resp.Body.Close()
		io.Copy(io.Discard, resp.Body)
		msc.mu.Lock()
		msc.lastSync = time.Now()
		msc.mu.Unlock()
	}()
}

// SyncKnowledge 同步一条知识到 Gateway
func (msc *MemorySyncClient) SyncKnowledge(topic, content string, tags []string) {
	msc.mu.Lock()
	enabled := msc.enabled
	msc.mu.Unlock()
	if !enabled {
		return
	}

	kn := map[string]interface{}{
		"node_id": msc.nodeID,
		"knowledge": []map[string]interface{}{
			{
				"topic":     topic,
				"content":   content,
				"author":    msc.nodeID,
				"verified":  time.Now().Format("2006-01-02"),
				"tags":      tags,
				"timestamp": time.Now(),
			},
		},
	}

	go func() {
		body, _ := json.Marshal(kn)
		resp, err := msc.httpClient.Post(
			msc.gatewayURL+"/api/v1/memory/sync",
			"application/json",
			bytes.NewReader(body),
		)
		if err != nil {
			fmt.Printf(" [MemorySync:%s] ⚠️ 同步知识失败: %v\n", msc.nodeID, err)
			return
		}
		defer resp.Body.Close()
		io.Copy(io.Discard, resp.Body)
		msc.mu.Lock()
		msc.lastSync = time.Now()
		msc.mu.Unlock()
	}()
}

// SearchRemote 搜索远程共享记忆
func (msc *MemorySyncClient) SearchRemote(query string, limit int) (string, error) {
	url := fmt.Sprintf("%s/api/v1/memory/search?q=%s&limit=%d", msc.gatewayURL, url.QueryEscape(query), limit)
	resp, err := msc.httpClient.Get(url)
	if err != nil {
		return "", fmt.Errorf("搜索远程记忆失败: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var wrapper struct {
		Success bool `json:"success"`
		Data    struct {
			Episodes []map[string]interface{} `json:"episodes"`
			Knowledge []map[string]interface{} `json:"knowledge"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &wrapper); err != nil {
		return "", fmt.Errorf("解析远程记忆失败: %w", err)
	}
	if !wrapper.Success {
		return "", fmt.Errorf("远程记忆搜索失败")
	}

	var b strings.Builder
	if len(wrapper.Data.Episodes) > 0 {
		b.WriteString(fmt.Sprintf("📚 共享经验 (%d 条):\n", len(wrapper.Data.Episodes)))
		for _, ep := range wrapper.Data.Episodes {
			task, _ := ep["task"].(string)
			nodeID, _ := ep["node_id"].(string)
			success, _ := ep["success"].(bool)
			icon := "✅"
			if !success {
				icon = "❌"
			}
			b.WriteString(fmt.Sprintf("  %s [%s] %s\n", icon, nodeID, truncateStr(task, 80)))
		}
	}
	if len(wrapper.Data.Knowledge) > 0 {
		b.WriteString(fmt.Sprintf("📖 共享知识 (%d 条):\n", len(wrapper.Data.Knowledge)))
		for _, kn := range wrapper.Data.Knowledge {
			topic, _ := kn["topic"].(string)
			nodeID, _ := kn["node_id"].(string)
			b.WriteString(fmt.Sprintf("  📝 [%s] %s\n", nodeID, topic))
		}
	}
	if b.Len() == 0 {
		return "📭 远程记忆无匹配结果", nil
	}
	return b.String(), nil
}

// GetStats 获取集群记忆统计
func (msc *MemorySyncClient) GetStats() (string, error) {
	resp, err := msc.httpClient.Get(msc.gatewayURL + "/api/v1/memory/stats")
	if err != nil {
		return "", fmt.Errorf("获取记忆统计失败: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var wrapper struct {
		Success bool                   `json:"success"`
		Data    map[string]interface{} `json:"data"`
	}
	if err := json.Unmarshal(body, &wrapper); err != nil {
		return "", fmt.Errorf("解析记忆统计失败: %w", err)
	}
	if !wrapper.Success {
		return "", fmt.Errorf("获取记忆统计失败")
	}

	data := wrapper.Data
	var b strings.Builder
	b.WriteString("🧠 集群记忆统计:\n")
	if nodes, ok := data["nodes"].(float64); ok {
		b.WriteString(fmt.Sprintf("  节点数: %.0f\n", nodes))
	}
	if eps, ok := data["episodes"].(float64); ok {
		b.WriteString(fmt.Sprintf("  经验数: %.0f\n", eps))
	}
	if kn, ok := data["knowledge"].(float64); ok {
		b.WriteString(fmt.Sprintf("  知识数: %.0f\n", kn))
	}
	return b.String(), nil
}

// registerMemorySyncTools 注册记忆同步工具到 Agent 工具集
func registerMemorySyncTools(tr *agent.ToolRegistry, msc *MemorySyncClient) {
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "memory_sync_episode",
			Description: "将本节点的执行经验同步到 Gateway 共享记忆层，其他节点可以搜索到。task=任务描述, result=结果, success=是否成功, learned=学到的经验",
			Parameters: []agent.Param{
				{Name: "task", Type: "string", Required: true, Description: "任务描述"},
				{Name: "result", Type: "string", Required: true, Description: "执行结果"},
				{Name: "success", Type: "string", Required: true, Description: "是否成功: true/false"},
				{Name: "learned", Type: "string", Required: false, Description: "学到的经验教训"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			task, _ := args["task"].(string)
			result, _ := args["result"].(string)
			successStr, _ := args["success"].(string)
			learned, _ := args["learned"].(string)
			if task == "" {
				return "", fmt.Errorf("task is required")
			}
			success := successStr == "true" || successStr == "1" || successStr == "yes"
			msc.SyncEpisode(task, result, success, learned)
			return "✅ 经验已同步到共享记忆层", nil
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "memory_search",
			Description: "搜索 Gateway 共享记忆层中的经验和知识。query=搜索关键词, limit=返回条数（默认5）",
			Parameters: []agent.Param{
				{Name: "query", Type: "string", Required: true, Description: "搜索关键词"},
				{Name: "limit", Type: "int", Required: false, Description: "返回条数（默认5）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			query, _ := args["query"].(string)
			if query == "" {
				return "", fmt.Errorf("query is required")
			}
			limit := 5
			if l, ok := args["limit"].(float64); ok {
				limit = int(l)
			}
			return msc.SearchRemote(query, limit)
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "memory_stats",
			Description: "查看集群共享记忆层的统计信息（节点数、经验数、知识数）",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			return msc.GetStats()
		},
	})
}
