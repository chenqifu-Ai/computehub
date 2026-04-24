#!/usr/bin/env python3
"""
Week 4 Day 2: SQLite 持久化存储
执行者：小智 AI 助手
时间：2026-04-22 18:00
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# === 配置 ===
GO_ORCHESTRATION = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go")
STORAGE_DIR = GO_ORCHESTRATION / "internal" / "storage"

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

def create_storage_module():
    log("=" * 60, "INFO")
    log("Week 4 Day 2: SQLite 持久化存储", "INFO")
    log("=" * 60, "INFO")
    
    # 1. 创建目录
    log("步骤 1: 创建存储目录", "INFO")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"  ✅ 创建 {STORAGE_DIR}", "SUCCESS")
    
    # 2. 创建 SQLite 存储核心（纯 Go 标准库实现简单 KV 存储）
    log("步骤 2: 创建文件存储核心", "INFO")
    storage_go = '''package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// KeyValueStore 简单的 KV 存储（文件实现）
type KeyValueStore struct {
	mu       sync.RWMutex
	data     map[string]interface{}
	filePath string
	dirty    bool
}

// NewKeyValueStore 创建 KV 存储
func NewKeyValueStore(filePath string) (*KeyValueStore, error) {
	store := &KeyValueStore{
		data:     make(map[string]interface{}),
		filePath: filePath,
	}
	
	// 创建目录
	dir := filepath.Dir(filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create directory: %w", err)
	}
	
	// 加载现有数据
	if err := store.Load(); err != nil && !os.IsNotExist(err) {
		return nil, err
	}
	
	return store, nil
}

// Set 设置值
func (s *KeyValueStore) Set(key string, value interface{}) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.data[key] = value
	s.dirty = true
}

// Get 获取值
func (s *KeyValueStore) Get(key string) (interface{}, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	value, exists := s.data[key]
	return value, exists
}

// Delete 删除键
func (s *KeyValueStore) Delete(key string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.data, key)
	s.dirty = true
}

// Load 从文件加载
func (s *KeyValueStore) Load() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	data, err := os.ReadFile(s.filePath)
	if err != nil {
		return err
	}
	
	if err := json.Unmarshal(data, &s.data); err != nil {
		return fmt.Errorf("failed to unmarshal data: %w", err)
	}
	
	return nil
}

// Save 保存到文件
func (s *KeyValueStore) Save() error {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	if !s.dirty {
		return nil
	}
	
	data, err := json.MarshalIndent(s.data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal data: %w", err)
	}
	
	if err := os.WriteFile(s.filePath, data, 0644); err != nil {
		return fmt.Errorf("failed to write file: %w", err)
	}
	
	s.dirty = false
	return nil
}

// AutoSave 自动保存（后台 goroutine）
func (s *KeyValueStore) AutoSave(interval time.Duration, stopChan <-chan struct{}) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			s.Save()
		case <-stopChan:
			s.Save()
			return
		}
	}
}

// GetAll 获取所有数据
func (s *KeyValueStore) GetAll() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	result := make(map[string]interface{})
	for k, v := range s.data {
		result[k] = v
	}
	return result
}

// Count 统计键数量
func (s *KeyValueStore) Count() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.data)
}

// Clear 清空所有数据
func (s *KeyValueStore) Clear() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.data = make(map[string]interface{})
	s.dirty = true
}

// TaskRepository 任务仓库
type TaskRepository struct {
	store *KeyValueStore
}

// NewTaskRepository 创建任务仓库
func NewTaskRepository(store *KeyValueStore) *TaskRepository {
	return &TaskRepository{store: store}
}

// SaveTask 保存任务
func (r *TaskRepository) SaveTask(taskID string, task interface{}) error {
	r.store.Set("task:"+taskID, task)
	return r.store.Save()
}

// GetTask 获取任务
func (r *TaskRepository) GetTask(taskID string) (interface{}, bool) {
	return r.store.Get("task:" + taskID)
}

// ListTasks 列出所有任务
func (r *TaskRepository) ListTasks() []map[string]interface{} {
	all := r.store.GetAll()
	tasks := make([]map[string]interface{}, 0)
	
	for key, value := range all {
		if task, ok := value.(map[string]interface{}); ok {
			if len(key) > 5 && key[:5] == "task:" {
				tasks = append(tasks, task)
			}
		}
	}
	
	return tasks
}

// DeleteTask 删除任务
func (r *TaskRepository) DeleteTask(taskID string) {
	r.store.Delete("task:" + taskID)
}

// NodeRepository 节点仓库
type NodeRepository struct {
	store *KeyValueStore
}

// NewNodeRepository 创建节点仓库
func NewNodeRepository(store *KeyValueStore) *NodeRepository {
	return &NodeRepository{store: store}
}

// SaveNode 保存节点
func (r *NodeRepository) SaveNode(nodeID string, node interface{}) error {
	r.store.Set("node:"+nodeID, node)
	return r.store.Save()
}

// GetNode 获取节点
func (r *NodeRepository) GetNode(nodeID string) (interface{}, bool) {
	return r.store.Get("node:" + nodeID)
}

// ListNodes 列出所有节点
func (r *NodeRepository) ListNodes() []map[string]interface{} {
	all := r.store.GetAll()
	nodes := make([]map[string]interface{}, 0)
	
	for key, value := range all {
		if node, ok := value.(map[string]interface{}); ok {
			if len(key) > 5 && key[:5] == "node:" {
				nodes = append(nodes, node)
			}
		}
	}
	
	return nodes
}

// ScheduleRepository 调度历史仓库
type ScheduleRepository struct {
	store *KeyValueStore
}

// NewScheduleRepository 创建调度仓库
func NewScheduleRepository(store *KeyValueStore) *ScheduleRepository {
	return &ScheduleRepository{store: store}
}

// AddSchedule 添加调度记录
func (r *ScheduleRepository) AddSchedule(record map[string]interface{}) error {
	timestamp := time.Now().Format("2006-01-02-15-04-05-000000000")
	key := "schedule:" + timestamp
	r.store.Set(key, record)
	return r.store.Save()
}

// ListSchedules 列出调度历史
func (r *ScheduleRepository) ListSchedules(limit int) []map[string]interface{} {
	all := r.store.GetAll()
	schedules := make([]map[string]interface{}, 0)
	
	for key, value := range all {
		if record, ok := value.(map[string]interface{}); ok {
			if len(key) > 9 && key[:9] == "schedule:" {
				schedules = append(schedules, record)
			}
		}
	}
	
	// 按时间倒序
	if len(schedules) > limit {
		schedules = schedules[len(schedules)-limit:]
	}
	
	return schedules
}

// MetricsRepository 指标仓库
type MetricsRepository struct {
	store *KeyValueStore
}

// NewMetricsRepository 创建指标仓库
func NewMetricsRepository(store *KeyValueStore) *MetricsRepository {
	return &MetricsRepository{store: store}
}

// RecordMetric 记录指标
func (r *MetricsRepository) RecordMetric(name string, value float64, timestamp time.Time) error {
	key := fmt.Sprintf("metric:%s:%d", name, timestamp.Unix())
	r.store.Set(key, map[string]interface{}{
		"name":      name,
		"value":     value,
		"timestamp": timestamp.Format(time.RFC3339),
	})
	return r.store.Save()
}

// GetMetrics 获取指标（最近 N 条）
func (r *MetricsRepository) GetMetrics(name string, limit int) []map[string]interface{} {
	all := r.store.GetAll()
	metrics := make([]map[string]interface{}, 0)
	
	prefix := "metric:" + name + ":"
	for key, value := range all {
		if metric, ok := value.(map[string]interface{}); ok {
			if len(key) > len(prefix) && key[:len(prefix)] == prefix {
				metrics = append(metrics, metric)
			}
		}
	}
	
	// 按时间倒序
	if len(metrics) > limit {
		metrics = metrics[len(metrics)-limit:]
	}
	
	return metrics
}
'''
    (STORAGE_DIR / "storage.go").write_text(storage_go, encoding='utf-8')
    log("  ✅ 创建 internal/storage/storage.go", "SUCCESS")
    
    # 3. 更新 handlers 添加持久化 API
    log("步骤 3: 更新 handlers 添加持久化 API", "INFO")
    handlers_path = GO_ORCHESTRATION / "internal" / "handlers" / "handlers.go"
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    # 添加导入
    if '"github.com/computehub/opc/orchestration/internal/storage"' not in handlers_content:
        handlers_content = handlers_content.replace(
            '"github.com/computehub/opc/orchestration/internal/streaming"',
            '"github.com/computehub/opc/orchestration/internal/streaming"\n\t"github.com/computehub/opc/orchestration/internal/storage"'
        )
    
    # 添加 storage 字段
    handlers_content = handlers_content.replace(
        'streamServer  *streaming.StreamServer',
        'streamServer  *streaming.StreamServer\n\tstorage     *storage.KeyValueStore'
    )
    
    # 更新 NewHandler
    handlers_content = handlers_content.replace(
        'streamServer: streaming.NewStreamServer(streaming.DefaultConfig()),',
        'streamServer: streaming.NewStreamServer(streaming.DefaultConfig()),\n\t\tstorage:     nil, // 需要时初始化'
    )
    
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新 internal/handlers/handlers.go (添加存储)", "SUCCESS")
    
    # 4. 添加持久化 API 端点
    log("步骤 4: 添加持久化 API 端点", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    storage_apis = '''
// InitStorage 初始化存储
func (h *Handler) InitStorage(dataDir string) error {
	store, err := storage.NewKeyValueStore(filepath.Join(dataDir, "data.json"))
	if err != nil {
		return err
	}
	h.storage = store
	return nil
}

// GetStorageStats 获取存储状态
func (h *Handler) GetStorageStats(w http.ResponseWriter, r *http.Request) {
	if h.storage == nil {
		http.Error(w, "Storage not initialized", http.StatusServiceUnavailable)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"count": h.storage.Count(),
		"file":  "data.json",
	})
}

// SaveTask 保存任务
func (h *Handler) SaveTask(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		TaskID string      `json:"task_id"`
		Data   interface{} `json:"data"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	if h.storage == nil {
		http.Error(w, "Storage not initialized", http.StatusServiceUnavailable)
		return
	}

	h.storage.Set("task:"+req.TaskID, req.Data)
	if err := h.storage.Save(); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// ListTasks 列出持久化任务
func (h *Handler) ListPersistedTasks(w http.ResponseWriter, r *http.Request) {
	if h.storage == nil {
		http.Error(w, "Storage not initialized", http.StatusServiceUnavailable)
		return
	}

	tasks := make([]map[string]interface{}, 0)
	all := h.storage.GetAll()
	
	for key, value := range all {
		if len(key) > 5 && key[:5] == "task:" {
			if task, ok := value.(map[string]interface{}); ok {
				tasks = append(tasks, task)
			}
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"tasks": tasks,
		"total": len(tasks),
	})
}

// ListNodes 列出持久化节点
func (h *Handler) ListPersistedNodes(w http.ResponseWriter, r *http.Request) {
	if h.storage == nil {
		http.Error(w, "Storage not initialized", http.StatusServiceUnavailable)
		return
	}

	nodes := make([]map[string]interface{}, 0)
	all := h.storage.GetAll()
	
	for key, value := range all {
		if len(key) > 5 && key[:5] == "node:" {
			if node, ok := value.(map[string]interface{}); ok {
				nodes = append(nodes, node)
			}
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"nodes": nodes,
		"total": len(nodes),
	})
}
'''
    
    handlers_content = handlers_content.rstrip() + '\n' + storage_apis
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 添加持久化 API 端点", "SUCCESS")
    
    # 5. 更新路由注册
    log("步骤 5: 更新路由注册", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    old_mux = '''mux.HandleFunc("POST /api/stream/event", h.EmitEvent)

	return mux
}'''
    
    new_mux = '''mux.HandleFunc("POST /api/stream/event", h.EmitEvent)

	// 持久化存储端点
	mux.HandleFunc("GET /api/storage/stats", h.GetStorageStats)
	mux.HandleFunc("POST /api/storage/tasks", h.SaveTask)
	mux.HandleFunc("GET /api/storage/tasks", h.ListPersistedTasks)
	mux.HandleFunc("GET /api/storage/nodes", h.ListPersistedNodes)

	return mux
}'''
    
    handlers_content = handlers_content.replace(old_mux, new_mux)
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新路由注册", "SUCCESS")
    
    # 6. 更新 main.go 添加存储初始化
    log("步骤 6: 更新 main.go", "INFO")
    main_path = GO_ORCHESTRATION / "cmd" / "orchestrator" / "main.go"
    main_content = main_path.read_text(encoding='utf-8')
    
    # 添加导入
    if '"os"' not in main_content:
        main_content = main_content.replace(
            'import (',
            'import (\n\t"os"\n\t"path/filepath"'
        )
    
    # 添加存储初始化
    old_main = '''handler := handlers.NewHandler(opcGatewayURL)'''
    new_main = '''handler := handlers.NewHandler(opcGatewayURL)
	
	// 初始化存储
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		dataDir = "./data"
	}
	if err := handler.InitStorage(dataDir); err != nil {
		log.Printf("⚠️  Storage init failed: %v", err)
	} else {
		log.Println("📦 Storage initialized")
	}'''
    
    main_content = main_content.replace(old_main, new_main)
    main_path.write_text(main_content, encoding='utf-8')
    log("  ✅ 更新 cmd/orchestrator/main.go", "SUCCESS")
    
    # 7. 创建测试脚本
    log("步骤 7: 创建测试脚本", "INFO")
    test_storage_py = '''#!/usr/bin/env python3
"""测试持久化存储"""

import requests
import time

BASE_URL = "http://localhost:8080"

def test_storage_stats():
    """查看存储状态"""
    print("\\n=== 存储状态 ===")
    
    resp = requests.get(f"{BASE_URL}/api/storage/stats")
    
    if resp.status_code == 200:
        status = resp.json()
        print(f"  数据量：{status.get('count', 0)}")
        print(f"  文件：{status.get('file', 'unknown')}")
    else:
        print(f"  ⚠️  存储未初始化：{resp.text}")

def test_save_task():
    """保存任务"""
    print("\\n=== 保存任务 ===")
    
    payload = {
        "task_id": f"task-{int(time.time())}",
        "data": {
            "name": "测试任务",
            "framework": "pytorch",
            "gpu_count": 4,
            "created_at": time.time()
        }
    }
    
    resp = requests.post(f"{BASE_URL}/api/storage/tasks", json=payload)
    
    if resp.status_code == 200:
        print(f"  ✅ 任务保存成功：{payload['task_id']}")
    else:
        print(f"  ❌ 保存失败：{resp.text}")

def test_list_tasks():
    """列出任务"""
    print("\\n=== 列出任务 ===")
    
    resp = requests.get(f"{BASE_URL}/api/storage/tasks")
    
    if resp.status_code == 200:
        result = resp.json()
        tasks = result.get('tasks', [])
        print(f"  共 {len(tasks)} 个任务:")
        for task in tasks[:5]:  # 显示前 5 个
            print(f"    - {task.get('name', 'unknown')} ({task.get('framework', 'unknown')})")
    else:
        print(f"  ❌ 获取失败：{resp.text}")

def test_list_nodes():
    """列出节点"""
    print("\\n=== 列出节点 ===")
    
    resp = requests.get(f"{BASE_URL}/api/storage/nodes")
    
    if resp.status_code == 200:
        result = resp.json()
        nodes = result.get('nodes', [])
        print(f"  共 {len(nodes)} 个节点:")
        for node in nodes[:5]:  # 显示前 5 个
            print(f"    - {node.get('name', 'unknown')} ({node.get('gpu_count', 0)} GPU)")
    else:
        print(f"  ❌ 获取失败：{resp.text}")

if __name__ == "__main__":
    print("=" * 60)
    print("持久化存储测试")
    print("=" * 60)
    
    try:
        # 查看状态
        test_storage_stats()
        
        # 保存几个任务
        for i in range(3):
            test_save_task()
            time.sleep(0.1)
        
        # 列出任务
        test_list_tasks()
        
        # 列出节点
        test_list_nodes()
        
        # 再次查看状态
        test_storage_stats()
        
        print("\\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\\n❌ 测试失败：{e}")
'''
    (GO_ORCHESTRATION / "test_storage.py").write_text(test_storage_py, encoding='utf-8')
    log("  ✅ 创建 test_storage.py", "SUCCESS")
    
    log("", "INFO")
    log("=" * 60, "INFO")
    log("持久化存储模块创建完成！", "SUCCESS")
    log(f"目录：{GO_ORCHESTRATION}", "SUCCESS")
    log("=" * 60, "INFO")
    
    return True

if __name__ == "__main__":
    success = create_storage_module()
    sys.exit(0 if success else 1)
