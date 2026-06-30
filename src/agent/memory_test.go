package agent

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestGitMemoryInit(t *testing.T) {
	root := t.TempDir()
	mem, err := NewGitMemory(root)
	if err != nil {
		t.Fatalf("NewGitMemory failed: %v", err)
	}

	// 验证目录结构
	dirs := []string{"sessions", "episodes", "knowledge", "system", "archive"}
	for _, d := range dirs {
		path := filepath.Join(root, d)
		if _, err := os.Stat(path); os.IsNotExist(err) {
			t.Errorf("expected directory %s to exist", d)
		}
	}

	// 验证 .git
	if _, err := os.Stat(filepath.Join(root, ".git")); os.IsNotExist(err) {
		t.Error("expected .git to exist")
	}

	// 验证 README
	if _, err := os.Stat(filepath.Join(root, "README.md")); os.IsNotExist(err) {
		t.Error("expected README.md to exist")
	}

	// 初始 commit 存在
	history, err := mem.History(1)
	if err != nil {
		t.Fatalf("History failed: %v", err)
	}
	if len(history) == 0 {
		t.Error("expected at least 1 commit after init")
	}

	mem.Close()
}

func TestAppendSession(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	sessionID := "test-001"

	// 追加第一条消息
	err := mem.AppendSession(sessionID, "User", "你好")
	if err != nil {
		t.Fatalf("AppendSession failed: %v", err)
	}

	// 追加第二条消息
	err = mem.AppendSession(sessionID, "Agent (result)", "你好！有什么需要帮忙的？")
	if err != nil {
		t.Fatalf("AppendSession 2 failed: %v", err)
	}

	// 读取会话
	content, err := mem.GetSession(sessionID)
	if err != nil {
		t.Fatalf("GetSession failed: %v", err)
	}
	if !contains(content, "你好") {
		t.Error("expected session to contain '你好'")
	}
	if !contains(content, "有什么需要帮忙的") {
		t.Error("expected session to contain response")
	}

	// 文件存在
	path := filepath.Join(root, "sessions", sessionID+".md")
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Error("expected session file to exist")
	}
}

func TestSaveEpisode(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	err := mem.SaveEpisode("测试磁盘清理", "成功释放 3.4GB", true, "/tmp 是最主要的可回收空间")
	if err != nil {
		t.Fatalf("SaveEpisode failed: %v", err)
	}

	// 搜索
	results, err := mem.SearchEpisodes("磁盘", 10)
	if err != nil {
		t.Fatalf("SearchEpisodes failed: %v", err)
	}
	if len(results) == 0 {
		t.Error("expected at least 1 search result")
	}

	// 列出最近
	recent, err := mem.ListRecentEpisodes(5)
	if err != nil {
		t.Fatalf("ListRecentEpisodes failed: %v", err)
	}
	if len(recent) == 0 {
		t.Error("expected at least 1 recent episode")
	}
}

func TestSaveKnowledge(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	err := mem.SaveKnowledge("windows-gpu-detection", "Windows GPU 检测通过 WMI 回退")
	if err != nil {
		t.Fatalf("SaveKnowledge failed: %v", err)
	}

	results, err := mem.SearchKnowledge("GPU", 10)
	if err != nil {
		t.Fatalf("SearchKnowledge failed: %v", err)
	}
	if len(results) == 0 {
		t.Error("expected at least 1 knowledge result")
	}
}

func TestLinkAndAssociations(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	// 创建两个 episode
	mem.SaveEpisode("磁盘清理", "释放空间", true, "/tmp 可回收")
	// 获取实际的 episode 文件名
	entries, _ := os.ReadDir(filepath.Join(root, "episodes"))
	if len(entries) == 0 {
		t.Fatal("no episode file created")
	}
	ep1 := "episodes/" + entries[0].Name()

	// 创建知识
	mem.SaveKnowledge("tmp-cleanup", "/tmp 清理方法")
	knowledgeEntries, _ := os.ReadDir(filepath.Join(root, "knowledge"))
	if len(knowledgeEntries) == 0 {
		t.Fatal("no knowledge file created")
	}
	kn1 := "knowledge/" + knowledgeEntries[0].Name()

	// 建立关联
	err := mem.Link(ep1, kn1, "solves")
	if err != nil {
		t.Fatalf("Link failed: %v", err)
	}

	// 读取关联
	links, err := mem.GetAssociations(ep1)
	if err != nil {
		t.Fatalf("GetAssociations failed: %v", err)
	}
	if len(links) == 0 {
		t.Error("expected at least 1 association")
	}
}

func TestRecallAndStrength(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	mem.SaveEpisode("Windows 日志分析", "找到 3 个错误", true, "Select-String 优于 findstr")

	// Recall
	items, err := mem.Recall("日志", []string{"Windows"}, 10)
	if err != nil {
		t.Fatalf("Recall failed: %v", err)
	}
	if len(items) == 0 {
		t.Error("expected at least 1 recall result")
	}
}

func TestSystemStatus(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	err := mem.UpdateSystemStatus(`{"nodes": 3, "queue": 0}`)
	if err != nil {
		t.Fatalf("UpdateSystemStatus failed: %v", err)
	}

	status, err := mem.GetSystemStatus()
	if err != nil {
		t.Fatalf("GetSystemStatus failed: %v", err)
	}
	if !contains(status, "3") {
		t.Error("expected status to contain node count")
	}
}

func TestCommitAndHistory(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	// 初始至少有一个 init commit
	history, err := mem.History(10)
	if err != nil {
		t.Fatalf("History failed: %v", err)
	}
	if len(history) < 1 {
		t.Error("expected at least 1 commit")
	}

	// 写个 episode，会触发自动 commit
	mem.SaveEpisode("测试", "成功", true, "test")
	history, err = mem.History(10)
	if err != nil {
		t.Fatalf("History after episode failed: %v", err)
	}
	if len(history) < 2 {
		t.Error("expected at least 2 commits after episode")
	}

	// Diff
	diff, err := mem.Diff(history[0].Hash)
	if err != nil {
		t.Fatalf("Diff failed: %v", err)
	}
	t.Logf("Diff output:\n%s", diff)
}

func TestStats(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	mem.SaveEpisode("测试1", "成功1", true, "learned1")
	mem.SaveEpisode("测试2", "成功2", true, "learned2")
	mem.SaveKnowledge("topic1", "content1")

	stats, err := mem.Stats()
	if err != nil {
		t.Fatalf("Stats failed: %v", err)
	}
	if stats.EpisodeCount < 2 {
		t.Errorf("expected >= 2 episodes, got %d", stats.EpisodeCount)
	}
	if stats.KnowledgeCount < 1 {
		t.Errorf("expected >= 1 knowledge, got %d", stats.KnowledgeCount)
	}
	if stats.TotalCommits < 1 {
		t.Errorf("expected >= 1 commits, got %d", stats.TotalCommits)
	}
}

func TestSanitize(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"sk-abc123def456ghi789jklmnop", "sk-[REDACTED]"},
		{"Bearer my-secret-token-12345", "Bearer [REDACTED]"},
		{"password=123456", "password=[REDACTED]"},
		{"正常内容，没有敏感信息", "正常内容，没有敏感信息"},
		{"", ""},
	}

	for _, tt := range tests {
		result, err := sanitize(tt.input)
		if err != nil {
			t.Errorf("sanitize(%q) returned error: %v", tt.input, err)
			continue
		}
		if result != tt.expected {
			t.Errorf("sanitize(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestSlugify(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Hello World", "hello-world"},
		{"测试中文", "测试中文"},
		{"  spaces  ", "spaces"},
		{"SPECIAL!!!chars", "specialchars"},
		{"", "untitled"},
	}

	for _, tt := range tests {
		result := slugify(tt.input)
		if result != tt.expected {
			t.Errorf("slugify(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestInvalidSessionRole(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	err := mem.AppendSession("test-002", "InvalidRole", "测试")
	if err == nil {
		t.Error("expected error for invalid role")
	}
}

func TestEmptySessionID(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	err := mem.AppendSession("", "User", "测试")
	if err == nil {
		t.Error("expected error for empty session ID")
	}
}

func TestDailyDecay(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	// 创建几条 episode
	for i := 0; i < 5; i++ {
		mem.SaveEpisode(
			fmt.Sprintf("测试任务 %d", i),
			"成功",
			true,
			"测试经验",
		)
	}

	// 验证强度初始为 1.0
	for _, s := range mem.strengths {
		if s.Strength != 1.0 {
			t.Errorf("expected initial strength 1.0, got %f", s.Strength)
		}
	}
}

func TestRecallStrengthens(t *testing.T) {
	root := t.TempDir()
	mem, _ := NewGitMemory(root)
	defer mem.Close()

	mem.SaveEpisode("重要测试", "完成", true, "学到东西")

	// Count episode entries before recall
	epCountBefore := 0
	for k, s := range mem.strengths {
		if strings.HasPrefix(k, "episodes/") {
			epCountBefore++
			_ = s
		}
	}

	// Recall
	mem.Recall("重要", nil, 10)

	// Verify episode entries were hit
	foundEpisode := false
	for k, s := range mem.strengths {
		if strings.HasPrefix(k, "episodes/") {
			foundEpisode = true
			if s.AccessCount < 1 {
				t.Errorf("episode %s expected access count >= 1 after recall, got %d",
					k, s.AccessCount)
			} else {
				t.Logf("✅ episode %s access count = %d", k, s.AccessCount)
			}
		}
	}
	if !foundEpisode {
		t.Error("no episode entries found in strengths after recall")
	}

	// Verify: episode count should not decrease
	epCountAfter := 0
	for k := range mem.strengths {
		if strings.HasPrefix(k, "episodes/") {
			epCountAfter++
		}
	}
	t.Logf("episode entries: before=%d after=%d", epCountBefore, epCountAfter)
}

// ──────── Helper ────────

func contains(s, substr string) bool {
	if len(substr) == 0 {
		return true
	}
	if len(s) < len(substr) {
		return false
	}
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
