// Package node - RemoteClient handles HTTP communication with remote nodes.
// Sends heartbeats, dispatches tasks, and collects results.
package node

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// RemoteClient communicates with a remote compute node via HTTP.
type RemoteClient struct {
	BaseURL  string
	Timeout  time.Duration
	HTTPClient *http.Client
}

// NewRemoteClient creates a client for the given node address.
func NewRemoteClient(ip string, port int) *RemoteClient {
	return &RemoteClient{
		BaseURL: fmt.Sprintf("http://%s:%d", ip, port),
		Timeout: 30 * time.Second,
		HTTPClient: &http.Client{Timeout: 30 * time.Second},
	}
}

// ─── 节点注册 ───

// Register sends a registration request to the gateway.
func (rc *RemoteClient) Register(req RegisterRequest) (*RegisterResponse, error) {
	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal register request: %w", err)
	}

	resp, err := rc.HTTPClient.Post(
		fmt.Sprintf("%s/api/node/register", rc.BaseURL),
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		return nil, fmt.Errorf("register request failed: %w", err)
	}
	defer resp.Body.Close()

	var result RegisterResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode register response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("register failed: HTTP %d", resp.StatusCode)
	}

	return &result, nil
}

// ─── 心跳 ───

// SendHeartbeat sends a heartbeat to the remote node.
func (rc *RemoteClient) SendHeartbeat(req HeartbeatRequest) (*HeartbeatResponse, error) {
	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal heartbeat: %w", err)
	}

	resp, err := rc.HTTPClient.Post(
		fmt.Sprintf("%s/api/node/heartbeat", rc.BaseURL),
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		return nil, fmt.Errorf("heartbeat request failed: %w", err)
	}
	defer resp.Body.Close()

	var result HeartbeatResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode heartbeat response: %w", err)
	}

	return &result, nil
}

// ─── 任务分发 ───

// DispatchTask sends a task to the remote node for execution.
func (rc *RemoteClient) DispatchTask(taskID, nodeID, action string) (*TaskAssignment, error) {
	data, _ := json.Marshal(TaskAssignment{
		TaskID: taskID,
		Action: action,
	})

	resp, err := rc.HTTPClient.Post(
		fmt.Sprintf("%s/api/node/assign", rc.BaseURL),
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		return nil, fmt.Errorf("dispatch task failed: %w", err)
	}
	defer resp.Body.Close()

	var result TaskAssignment
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode assign response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("dispatch failed: HTTP %d", resp.StatusCode)
	}

	return &result, nil
}

// ─── 结果收集 ───

// ReportResult sends task completion results to the remote node.
func (rc *RemoteClient) ReportResult(report TaskResultReport) error {
	data, err := json.Marshal(report)
	if err != nil {
		return fmt.Errorf("marshal result report: %w", err)
	}

	resp, err := rc.HTTPClient.Post(
		fmt.Sprintf("%s/api/node/result", rc.BaseURL),
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		return fmt.Errorf("report result failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("report failed: HTTP %d", resp.StatusCode)
	}

	return nil
}

// ─── 节点查询 ───

// GetNodeStatus queries a remote node's status.
func (rc *RemoteClient) GetNodeStatus() (map[string]any, error) {
	resp, err := rc.HTTPClient.Get(fmt.Sprintf("%s/api/status", rc.BaseURL))
	if err != nil {
		return nil, fmt.Errorf("status query failed: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode status: %w", err)
	}

	return result, nil
}

// ─── 能力查询 ───

// QueryCapability requests a node's full capability report.
func (rc *RemoteClient) QueryCapability() (*NodeCapability, error) {
	resp, err := rc.HTTPClient.Get(fmt.Sprintf("%s/api/node/capability", rc.BaseURL))
	if err != nil {
		return nil, fmt.Errorf("capability query failed: %w", err)
	}
	defer resp.Body.Close()

	var cap NodeCapability
	if err := json.NewDecoder(resp.Body).Decode(&cap); err != nil {
		return nil, fmt.Errorf("decode capability: %w", err)
	}

	return &cap, nil
}

// ─── 健康检查 ───

// Health checks if the remote node is reachable.
func (rc *RemoteClient) Health() error {
	resp, err := rc.HTTPClient.Get(fmt.Sprintf("%s/api/health", rc.BaseURL))
	if err != nil {
		return fmt.Errorf("health check failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check: HTTP %d", resp.StatusCode)
	}

	return nil
}

// ─── 连接测试 ───

// TestConnection verifies network connectivity to the remote node.
func (rc *RemoteClient) TestConnection() error {
	start := time.Now()
	if err := rc.Health(); err != nil {
		return fmt.Errorf("connectivity test failed after %v: %w", time.Since(start), err)
	}
	return nil
}
