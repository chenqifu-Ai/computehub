// Copyright (c) 2026 ComputeHub. All rights reserved.
//
// 优化: NodeManager 热点状态 LRU 缓存 (2026-07-05)
// - 节点状态查询从 O(N) 遍历 → O(1) 缓存命中
// - 任务分配、列表查询等高频场景直接从缓存读取
// - 缓存失效策略: 注册/心跳/任务状态变更时自动失效

package kernel

import (
	"container/list"
	"sync"
	"time"
)

// nodeCacheEntry 缓存的节点状态快照
type nodeCacheEntry struct {
	state    *NodeManagerState
	register *NodeRegister
	metrics  *NodeMetrics
	tasks    map[string]*TaskState
	updated  time.Time
}

// NodeCache 热点节点状态 LRU 缓存
type NodeCache struct {
	mu       sync.RWMutex
	entries  map[string]*list.Element // nodeID → list.Element
	order    *list.List               // 最近使用顺序
	maxItems int                      // 最大缓存条目数
	ttl      time.Duration            // TTL
}

// NewNodeCache 创建 LRU 缓存
func NewNodeCache(maxItems int, ttl time.Duration) *NodeCache {
	return &NodeCache{
		entries:  make(map[string]*list.Element),
		order:    list.New(),
		maxItems: maxItems,
		ttl:      ttl,
	}
}

// Get 获取缓存的节点状态（线程安全）
func (c *NodeCache) Get(nodeID string) (*nodeCacheEntry, bool) {
	c.mu.RLock()
	elem, ok := c.entries[nodeID]
	c.mu.RUnlock()

	if !ok {
		return nil, false
	}

	entry := elem.Value.(*nodeCacheEntry)
	// TTL 检查
	if time.Since(entry.updated) > c.ttl {
		c.mu.Lock()
		c.evictUnlocked(nodeID)
		c.mu.Unlock()
		return nil, false
	}

	// 移动到最近使用
	c.mu.Lock()
	c.order.MoveToFront(elem)
	c.mu.Unlock()

	return entry, true
}

// Set 缓存节点状态（线程安全）
func (c *NodeCache) Set(nodeID string, state *NodeManagerState) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// 更新已有条目
	if elem, ok := c.entries[nodeID]; ok {
		elem.Value = &nodeCacheEntry{
			state:    state,
			register: state.Register,
			metrics:  state.Metrics,
			tasks:    state.Tasks,
			updated:  time.Now(),
		}
		c.order.MoveToFront(elem)
		return
	}

	// 插入新条目
	entry := &nodeCacheEntry{
		state:    state,
		register: state.Register,
		metrics:  state.Metrics,
		tasks:    state.Tasks,
		updated:  time.Now(),
	}
	elem := c.order.PushFront(entry)
	c.entries[nodeID] = elem

	// 超出容量 → 淘汰最旧
	for c.order.Len() > c.maxItems {
		c.evictOldest()
	}
}

// Invalidate 使缓存失效（写操作后调用）
func (c *NodeCache) Invalidate(nodeID string) {
	c.mu.Lock()
	c.evictUnlocked(nodeID)
	c.mu.Unlock()
}

// InvalidateAll 失效全部缓存（节点列表变更时调用）
func (c *NodeCache) InvalidateAll() {
	c.mu.Lock()
	c.entries = make(map[string]*list.Element)
	c.order = list.New()
	c.mu.Unlock()
}

func (c *NodeCache) evictUnlocked(nodeID string) {
	if elem, ok := c.entries[nodeID]; ok {
		c.order.Remove(elem)
		delete(c.entries, nodeID)
	}
}

func (c *NodeCache) evictOldest() {
	oldest := c.order.Back()
	if oldest != nil {
		nodeID := oldest.Value.(*nodeCacheEntry).state.Register.NodeID
		c.order.Remove(oldest)
		delete(c.entries, nodeID)
	}
}
