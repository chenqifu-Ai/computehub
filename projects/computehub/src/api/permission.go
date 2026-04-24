package api

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

// ====== 权限模型 ======

// PermissionLevel 权限级别
type PermissionLevel int

const (
	PermLevelNone PermissionLevel = iota // 无权限
	PermLevelRead                        // 只读
	PermLevelWrite                       // 读写
	PermLevelAdmin                       // 管理员
	PermLevelSuperAdmin                  // 超级管理员
)

func (p PermissionLevel) String() string {
	switch p {
	case PermLevelNone:
		return "NONE"
	case PermLevelRead:
		return "READ"
	case PermLevelWrite:
		return "WRITE"
	case PermLevelAdmin:
		return "ADMIN"
	case PermLevelSuperAdmin:
		return "SUPER_ADMIN"
	default:
		return "UNKNOWN"
	}
}

// ====== 角色 ======

type Role struct {
	Name        string           `json:"name"`
	Level       PermissionLevel  `json:"level"`
	Description string           `json:"description"`
	Permissions []Permission     `json:"permissions"`
}

type Permission struct {
	Resource string `json:"resource"` // "node", "task", "system", etc.
	Action   string `json:"action"`   // "read", "write", "delete", "admin"
}

// ====== 用户 ======

type User struct {
	UserID    string          `json:"user_id"`
	Username  string          `json:"username"`
	Email     string          `json:"email"`
	Role      *Role           `json:"role"`
	ApiKey    string          `json:"api_key,omitempty"`
	IPWhitelist []string      `json:"ip_whitelist,omitempty"`
	Enabled   bool            `json:"enabled"`
	CreatedAt time.Time       `json:"created_at"`
	LastLogin time.Time       `json:"last_login"`
}

// ====== 权限检查器 ======

type PermissionChecker struct {
	mu       sync.RWMutex
	users    map[string]*User
	roles    map[string]*Role
	apiKeys  map[string]string // apiKey -> userID
}

// NewPermissionChecker 创建权限检查器
func NewPermissionChecker() *PermissionChecker {
	pc := &PermissionChecker{
		users:   make(map[string]*User),
		roles:   make(map[string]*Role),
		apiKeys: make(map[string]string),
	}

	// 初始化内置角色
	pc.initDefaultRoles()

	return pc
}

// initDefaultRoles 初始化默认角色
func (pc *PermissionChecker) initDefaultRoles() {
	// 超级管理员角色
	superAdminRole := &Role{
		Name:        "super_admin",
		Level:       PermLevelSuperAdmin,
		Description: "超级管理员，拥有所有权限",
		Permissions: []Permission{
			{Resource: "*", Action: "*"},
		},
	}
	pc.roles["super_admin"] = superAdminRole

	// 管理员角色
	adminRole := &Role{
		Name:        "admin",
		Level:       PermLevelAdmin,
		Description: "管理员，管理节点和任务",
		Permissions: []Permission{
			{Resource: "node", Action: "*"},
			{Resource: "task", Action: "*"},
			{Resource: "system", Action: "read"},
		},
	}
	pc.roles["admin"] = adminRole

	// 开发者角色
	developerRole := &Role{
		Name:        "developer",
		Level:       PermLevelWrite,
		Description: "开发者，提交任务和读取结果",
		Permissions: []Permission{
			{Resource: "task", Action: "read"},
			{Resource: "task", Action: "write"},
			{Resource: "node", Action: "read"},
			{Resource: "system", Action: "read"},
		},
	}
	pc.roles["developer"] = developerRole

	// 只读角色
	readerRole := &Role{
		Name:        "reader",
		Level:       PermLevelRead,
		Description: "只读用户，只能查看信息",
		Permissions: []Permission{
			{Resource: "node", Action: "read"},
			{Resource: "task", Action: "read"},
			{Resource: "system", Action: "read"},
		},
	}
	pc.roles["reader"] = readerRole
}

// CreateUser 创建用户
func (pc *PermissionChecker) CreateUser(userID, username, email, roleName string) (*User, error) {
	pc.mu.Lock()
	defer pc.mu.Unlock()

	// 验证角色
	role, exists := pc.roles[roleName]
	if !exists {
		return nil, fmt.Errorf("role %s not found", roleName)
	}

	user := &User{
		UserID:    userID,
		Username:  username,
		Email:     email,
		Role:      role,
		ApiKey:    generateAPIKey(),
		Enabled:   true,
		CreatedAt: time.Now(),
	}

	pc.users[userID] = user
	pc.apiKeys[user.ApiKey] = userID

	return user, nil
}

// AuthenticateByAPIKey 通过 API Key 认证用户
func (pc *PermissionChecker) AuthenticateByAPIKey(apiKey string) (*User, error) {
	pc.mu.RLock()
	defer pc.mu.RUnlock()

	userID, exists := pc.apiKeys[apiKey]
	if !exists {
		return nil, fmt.Errorf("invalid API key")
	}

	user, exists := pc.users[userID]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}

	if !user.Enabled {
		return nil, fmt.Errorf("user disabled")
	}

	return user, nil
}

// HasPermission 检查用户是否有指定权限
func (pc *PermissionChecker) HasPermission(userID, resource, action string) bool {
	pc.mu.RLock()
	defer pc.mu.RUnlock()

	user, exists := pc.users[userID]
	if !exists {
		return false
	}

	return checkPermission(user.Role, resource, action)
}

// HasReadPermission 检查读权限
func (pc *PermissionChecker) HasReadPermission(userID, resource string) bool {
	return pc.HasPermission(userID, resource, "read")
}

// HasWritePermission 检查写权限
func (pc *PermissionChecker) HasWritePermission(userID, resource string) bool {
	return pc.HasPermission(userID, resource, "write")
}

// HasAdminPermission 检查管理员权限
func (pc *PermissionChecker) HasAdminPermission(userID, resource string) bool {
	return pc.HasPermission(userID, resource, "admin")
}

// ====== 权限检查逻辑 ======

// checkPermission 检查角色是否有指定权限
func checkPermission(role *Role, resource, action string) bool {
	if role == nil {
		return false
	}

	// 超级管理员有所有权限
	if role.Level >= PermLevelSuperAdmin {
		return true
	}

	// 检查具体权限
	for _, perm := range role.Permissions {
		if matchResource(perm.Resource, resource) && matchAction(perm.Action, action) {
			return true
		}
	}

	return false
}

// matchResource 匹配资源名称（支持通配符）
func matchResource(pattern, resource string) bool {
	if pattern == "*" {
		return true
	}
	return pattern == resource
}

// matchAction 匹配动作名称（支持通配符）
func matchAction(pattern, action string) bool {
	if pattern == "*" {
		return true
	}
	return pattern == action
}

// ====== API Key 管理 ======

// generateAPIKey 生成随机 API Key
func generateAPIKey() string {
	// 简化实现，实际应使用加密随机数生成
	return "ak_" + time.Now().Format("20060102150405") + "_" + strings.ReplaceAll(time.Now().String(), " ", "")
}

// RotateAPIKey 轮换 API Key
func (pc *PermissionChecker) RotateAPIKey(userID string) (string, error) {
	pc.mu.Lock()
	defer pc.mu.Unlock()

	user, exists := pc.users[userID]
	if !exists {
		return "", fmt.Errorf("user %s not found", userID)
	}

	oldKey := user.ApiKey
	newKey := generateAPIKey()

	delete(pc.apiKeys, oldKey)
	user.ApiKey = newKey
	pc.apiKeys[newKey] = userID

	return newKey, nil
}

// DisableUser 禁用用户
func (pc *PermissionChecker) DisableUser(userID string) error {
	pc.mu.Lock()
	defer pc.mu.Unlock()

	user, exists := pc.users[userID]
	if !exists {
		return fmt.Errorf("user %s not found", userID)
	}

	user.Enabled = false
	return nil
}

// EnableUser 启用用户
func (pc *PermissionChecker) EnableUser(userID string) error {
	pc.mu.Lock()
	defer pc.mu.Unlock()

	user, exists := pc.users[userID]
	if !exists {
		return fmt.Errorf("user %s not found", userID)
	}

	user.Enabled = true
	return nil
}

// ====== 审计日志 ======

// AuditAction 审计操作类型
type AuditAction string

const (
	AuditActionLogin        AuditAction = "LOGIN"
	AuditActionLogout       AuditAction = "LOGOUT"
	AuditActionCreateTask   AuditAction = "CREATE_TASK"
	AuditActionDeleteTask   AuditAction = "DELETE_TASK"
	AuditActionAssignTask   AuditAction = "ASSIGN_TASK"
	AuditActionRegisterNode AuditAction = "REGISTER_NODE"
	AuditActionRemoveNode   AuditAction = "REMOVE_NODE"
	AuditActionConfigChange AuditAction = "CONFIG_CHANGE"
	AuditActionPermission   AuditAction = "PERMISSION_CHANGE"
	AuditActionUnauthorized AuditAction = "UNAUTHORIZED_ACCESS"
)

// AuditLogEntry 审计日志条目
type AuditLogEntry struct {
	ID        string       `json:"id"`
	Timestamp time.Time    `json:"timestamp"`
	UserID    string       `json:"user_id"`
	IP        string       `json:"ip"`
	Action    AuditAction  `json:"action"`
	Resource  string       `json:"resource"`
	TargetID  string       `json:"target_id,omitempty"`
	Success   bool         `json:"success"`
	Details   string       `json:"details,omitempty"`
	UserAgent string       `json:"user_agent,omitempty"`
}

// AuditLogger 审计日志记录器
type AuditLogger struct {
	mu     sync.RWMutex
	entries []AuditLogEntry
	maxSize int
}

// NewAuditLogger 创建审计日志记录器
func NewAuditLogger(maxSize int) *AuditLogger {
	return &AuditLogger{
		entries: make([]AuditLogEntry, 0),
		maxSize: maxSize,
	}
}

// Log 记录审计日志
func (al *AuditLogger) Log(userID, ip, action, resource, targetID, details, userAgent string, success bool) {
	al.mu.Lock()
	defer al.mu.Unlock()

	entry := AuditLogEntry{
		ID:        fmt.Sprintf("audit-%d", time.Now().UnixNano()),
		Timestamp: time.Now(),
		UserID:    userID,
		IP:        ip,
		Action:    AuditAction(action),
		Resource:  resource,
		TargetID:  targetID,
		Success:   success,
		Details:   details,
		UserAgent: userAgent,
	}

	al.entries = append(al.entries, entry)

	// 限制日志大小
	if len(al.entries) > al.maxSize {
		al.entries = al.entries[len(al.entries)-al.maxSize:]
	}
}

// GetLogs 获取审计日志
func (al *AuditLogger) GetLogs(limit int, userID string) []AuditLogEntry {
	al.mu.RLock()
	defer al.mu.RUnlock()

	var entries []AuditLogEntry

	if userID != "" {
		// 过滤特定用户
		for _, entry := range al.entries {
			if entry.UserID == userID {
				entries = append(entries, entry)
			}
			if len(entries) >= limit {
				break
			}
		}
	} else {
		// 返回最近日志
		for i := len(al.entries) - 1; i >= 0 && len(entries) < limit; i-- {
			entries = append(entries, al.entries[i])
		}
	}

	// 反转顺序（最新在前）
	for i, j := 0, len(entries)-1; i < j; i, j = i+1, j-1 {
		entries[i], entries[j] = entries[j], entries[i]
	}

	return entries
}

// GetFailedLogs 获取失败的审计日志
func (al *AuditLogger) GetFailedLogs(limit int) []AuditLogEntry {
	al.mu.RLock()
	defer al.mu.RUnlock()

	var entries []AuditLogEntry

	for _, entry := range al.entries {
		if !entry.Success {
			entries = append(entries, entry)
			if len(entries) >= limit {
				break
			}
		}
	}

	return entries
}

// GetStats 获取审计统计
func (al *AuditLogger) GetStats() map[string]int {
	al.mu.RLock()
	defer al.mu.RUnlock()

	stats := make(map[string]int)
	for _, entry := range al.entries {
		stats[string(entry.Action)]++
	}

	return stats
}
