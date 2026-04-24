package api

import (
	"testing"
)

func TestPermissionCheckerInitRoles(t *testing.T) {
	pc := NewPermissionChecker()

	if len(pc.roles) != 4 {
		t.Errorf("Expected 4 default roles, got %d", len(pc.roles))
	}

	expectedRoles := []string{"super_admin", "admin", "developer", "reader"}
	for _, role := range expectedRoles {
		if _, exists := pc.roles[role]; !exists {
			t.Errorf("Expected role %s not found", role)
		}
	}
}

func TestCreateUser(t *testing.T) {
	pc := NewPermissionChecker()

	user, err := pc.CreateUser("user-001", "testuser", "test@example.com", "developer")
	if err != nil {
		t.Fatalf("CreateUser failed: %v", err)
	}

	if user.UserID != "user-001" {
		t.Errorf("Expected user-001, got %s", user.UserID)
	}
	if user.Role == nil {
		t.Error("Role should not be nil")
	}
	if user.ApiKey == "" {
		t.Error("API key should be generated")
	}
	if !user.Enabled {
		t.Error("User should be enabled by default")
	}
}

func TestCreateUserInvalidRole(t *testing.T) {
	pc := NewPermissionChecker()

	_, err := pc.CreateUser("user-001", "testuser", "test@example.com", "invalid_role")
	if err == nil {
		t.Fatal("Expected error for invalid role")
	}
}

func TestAuthenticateByAPIKey(t *testing.T) {
	pc := NewPermissionChecker()

	// Create user
	user, _ := pc.CreateUser("user-001", "testuser", "test@example.com", "developer")

	// Authenticate
	authenticated, err := pc.AuthenticateByAPIKey(user.ApiKey)
	if err != nil {
		t.Fatalf("Authenticate failed: %v", err)
	}

	if authenticated.UserID != "user-001" {
		t.Errorf("Expected user-001, got %s", authenticated.UserID)
	}
}

func TestAuthenticateInvalidKey(t *testing.T) {
	pc := NewPermissionChecker()

	_, err := pc.AuthenticateByAPIKey("invalid-key")
	if err == nil {
		t.Fatal("Expected error for invalid API key")
	}
}

func TestHasPermission(t *testing.T) {
	pc := NewPermissionChecker()

	// Create users with different roles
	pc.CreateUser("dev-user", "developer", "dev@test.com", "developer")
	pc.CreateUser("reader-user", "reader", "reader@test.com", "reader")
	pc.CreateUser("admin-user", "admin", "admin@test.com", "admin")

	// Developer can read tasks
	if !pc.HasReadPermission("dev-user", "task") {
		t.Error("Developer should have read permission on tasks")
	}

	// Developer can write tasks
	if !pc.HasWritePermission("dev-user", "task") {
		t.Error("Developer should have write permission on tasks")
	}

	// Developer cannot write nodes
	if pc.HasWritePermission("dev-user", "node") {
		t.Error("Developer should not have write permission on nodes")
	}

	// Reader cannot write tasks
	if pc.HasWritePermission("reader-user", "task") {
		t.Error("Reader should not have write permission on tasks")
	}

	// Admin can read system
	if !pc.HasReadPermission("admin-user", "system") {
		t.Error("Admin should have read permission on system")
	}
}

func TestHasPermissionSuperAdmin(t *testing.T) {
	pc := NewPermissionChecker()

	pc.CreateUser("super-user", "superadmin", "super@test.com", "super_admin")

	// Super admin should have all permissions
	if !pc.HasPermission("super-user", "*", "*") {
		t.Error("Super admin should have all permissions")
	}

	if !pc.HasReadPermission("super-user", "anything") {
		t.Error("Super admin should have read permission on anything")
	}

	if !pc.HasWritePermission("super-user", "anything") {
		t.Error("Super admin should have write permission on anything")
	}

	if !pc.HasAdminPermission("super-user", "anything") {
		t.Error("Super admin should have admin permission on anything")
	}
}

func TestRotateAPIKey(t *testing.T) {
	pc := NewPermissionChecker()

	user, _ := pc.CreateUser("user-001", "testuser", "test@example.com", "developer")
	oldKey := user.ApiKey

	newKey, err := pc.RotateAPIKey("user-001")
	if err != nil {
		t.Fatalf("RotateAPIKey failed: %v", err)
	}

	if newKey == oldKey {
		t.Error("New API key should be different from old key")
	}

	// Old key should not work
	_, err = pc.AuthenticateByAPIKey(oldKey)
	if err == nil {
		t.Fatal("Old API key should be invalid")
	}

	// New key should work
	_, err = pc.AuthenticateByAPIKey(newKey)
	if err != nil {
		t.Fatalf("New API key should be valid: %v", err)
	}
}

func TestDisableEnableUser(t *testing.T) {
	pc := NewPermissionChecker()

	user, _ := pc.CreateUser("user-001", "testuser", "test@example.com", "developer")

	// Disable user
	err := pc.DisableUser("user-001")
	if err != nil {
		t.Fatalf("DisableUser failed: %v", err)
	}

	// Disabled user should not authenticate
	_, err = pc.AuthenticateByAPIKey(user.ApiKey)
	if err == nil {
		t.Fatal("Disabled user should not authenticate")
	}

	// Re-enable user
	err = pc.EnableUser("user-001")
	if err != nil {
		t.Fatalf("EnableUser failed: %v", err)
	}

	// Re-enabled user should authenticate
	_, err = pc.AuthenticateByAPIKey(user.ApiKey)
	if err != nil {
		t.Fatalf("Re-enabled user should authenticate: %v", err)
	}
}

func TestNonExistentUser(t *testing.T) {
	pc := NewPermissionChecker()

	_, err := pc.AuthenticateByAPIKey("any-key")
	if err == nil {
		t.Fatal("Expected error for non-existent user")
	}

	// Permission check should fail for non-existent user
	if pc.HasReadPermission("nonexistent", "task") {
		t.Error("Non-existent user should not have permissions")
	}
}

func TestPermissionLevels(t *testing.T) {
	_ = NewPermissionChecker()

	if PermLevelNone.String() != "NONE" {
		t.Errorf("Expected NONE, got %s", PermLevelNone.String())
	}
	if PermLevelRead.String() != "READ" {
		t.Errorf("Expected READ, got %s", PermLevelRead.String())
	}
	if PermLevelWrite.String() != "WRITE" {
		t.Errorf("Expected WRITE, got %s", PermLevelWrite.String())
	}
	if PermLevelAdmin.String() != "ADMIN" {
		t.Errorf("Expected ADMIN, got %s", PermLevelAdmin.String())
	}
	if PermLevelSuperAdmin.String() != "SUPER_ADMIN" {
		t.Errorf("Expected SUPER_ADMIN, got %s", PermLevelSuperAdmin.String())
	}
}

func TestAuditLogger(t *testing.T) {
	al := NewAuditLogger(100)

	// Log some entries
	al.Log("user-001", "192.168.1.1", string(AuditActionLogin), "system", "", "login success", "", true)
	al.Log("user-001", "192.168.1.1", string(AuditActionCreateTask), "task", "task-001", "create task", "", true)
	al.Log("user-002", "192.168.1.2", string(AuditActionUnauthorized), "node", "node-001", "unauthorized access", "", false)

	// Get logs
	logs := al.GetLogs(10, "")
	if len(logs) != 3 {
		t.Errorf("Expected 3 logs, got %d", len(logs))
	}

	// Get failed logs
	failed := al.GetFailedLogs(10)
	if len(failed) != 1 {
		t.Errorf("Expected 1 failed log, got %d", len(failed))
	}

	// Get stats
	stats := al.GetStats()
	if stats[string(AuditActionLogin)] != 1 {
		t.Errorf("Expected 1 LOGIN, got %d", stats[string(AuditActionLogin)])
	}
	if stats[string(AuditActionUnauthorized)] != 1 {
		t.Errorf("Expected 1 UNAUTHORIZED, got %d", stats[string(AuditActionUnauthorized)])
	}
}

func TestAuditLoggerUserFilter(t *testing.T) {
	al := NewAuditLogger(100)

	al.Log("user-001", "192.168.1.1", string(AuditActionLogin), "system", "", "", "", true)
	al.Log("user-002", "192.168.1.2", string(AuditActionLogin), "system", "", "", "", true)
	al.Log("user-001", "192.168.1.1", string(AuditActionCreateTask), "task", "task-001", "", "", true)

	// Filter by user-001
	logs := al.GetLogs(10, "user-001")
	if len(logs) != 2 {
		t.Errorf("Expected 2 logs for user-001, got %d", len(logs))
	}
}

func TestAuditLoggerSizeLimit(t *testing.T) {
	al := NewAuditLogger(5)

	// Log 10 entries
	for i := 0; i < 10; i++ {
		al.Log("user-001", "192.168.1.1", string(AuditActionLogin), "system", "", "", "", true)
	}

	// Should only keep last 5
	logs := al.GetLogs(100, "")
	if len(logs) != 5 {
		t.Errorf("Expected 5 logs, got %d", len(logs))
	}
}
