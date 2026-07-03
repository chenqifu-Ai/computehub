package agent

import (
	"os"
	"path/filepath"
	"testing"
)

// ──────────────────────────────────────────────
// 集成测试：Agent + Memory 全链路
// ├─ 记忆仓库初始化
// ├─ buildSystemPrompt 注入记忆
// ├─ session 读写
// ├─ episode 读写
// ├─ knowledge 读写
// ├─ 联想网络
// ├─ Recall
// ├─ Memory Stats
// └─ Agent 启动容错
// ──────────────────────────────────────────────

func TestAgentIntegrationWithMemory(t *testing.T) {
	root := t.TempDir()
	memRoot := filepath.Join(root, "opc-memory")

	// ── Step 1: 写入初始数据到记忆仓库 ──
	mem, err := NewGitMemory(memRoot)
	if err != nil {
		t.Fatalf("NewGitMemory failed: %v", err)
	}

	err = mem.SaveEpisode("分析三台服务器日志", "发现15个异常, 3个关键", true,
		"Windows 的 findstr 和 Linux 的 grep 行为不同")
	if err != nil {
		t.Fatalf("SaveEpisode 1: %v", err)
	}
	err = mem.SaveEpisode("清理 ecs-p2ph 磁盘空间", "释放 3.4GB", true,
		"/tmp 是最主要的可回收空间，应每周自动清理")
	if err != nil {
		t.Fatalf("SaveEpisode 2: %v", err)
	}
	err = mem.SaveKnowledge("windows-gpu-detection", "Windows GPU 检测通过 WMI 回退")
	if err != nil {
		t.Fatalf("SaveKnowledge: %v", err)
	}
	err = mem.AppendSession("test-init-session", "User", "帮我查一下集群状态")
	if err != nil {
		t.Fatalf("AppendSession: %v", err)
	}
	mem.Close()

	// ── Step 2: 创建 Agent 并验证记忆加载 ──
	agent := NewAgent(nil, nil, memRoot)
	if agent.memory == nil {
		t.Fatal("memory should be loaded")
	}
	if _, err := os.Stat(filepath.Join(memRoot, ".git")); os.IsNotExist(err) {
		t.Error("expected .git to exist")
	}

	// ── Step 3: 验证 buildSystemPrompt 注入记忆 ──
	req := &AgentRequest{
		Task:      "检查一下服务器状态",
		SessionID: "test-session-001",
	}
	prompt := agent.buildSystemPrompt(req)
	t.Log("========== System Prompt 记忆注入 ==========")
	t.Log(prompt)

	checks := []struct {
		keyword string
		reason  string
	}{
		{"最近经验", "应该包含最近经验段落"},
		{"分析三台服务器日志", "最近第一条 episode 应该出现"},
		{"清理 ecs-p2ph 磁盘空间", "最近第二条 episode 应该出现"},
		{"可用 Worker 节点", "应该包含节点信息段落"},
		{"响应格式", "应该包含响应格式说明"},
	}
	allPassed := true
	for _, c := range checks {
		if !contains(prompt, c.keyword) {
			t.Errorf("❌ 缺少: %s (%s)", c.keyword, c.reason)
			allPassed = false
		} else {
			t.Logf("✅ 包含: %s", c.keyword)
		}
	}
	if !allPassed {
		t.Fatal("system prompt 记忆注入验证失败")
	}

	// ── Step 4: 验证 session 读写 ──
	err = agent.memory.AppendSession("test-session-001", "User", "手动添加的测试消息")
	if err != nil {
		t.Errorf("AppendSession failed: %v", err)
	}
	sessionContent, err := agent.memory.GetSession("test-session-001")
	if err != nil {
		t.Errorf("GetSession failed: %v", err)
	}
	t.Log("========== Session 读写 ==========")
	t.Log(sessionContent)
	if !contains(sessionContent, "手动添加的测试消息") {
		t.Error("❌ session 缺少手动添加的消息")
	} else {
		t.Log("✅ session 读写正常")
	}

	// ── Step 5: 验证 episode 读写 ──
	err = agent.memory.SaveEpisode("集成测试验证", "全部通过", true,
		"Agent + Memory 集成链路验证完成")
	if err != nil {
		t.Errorf("SaveEpisode failed: %v", err)
	}
	episodes, err := agent.memory.ListRecentEpisodes(10)
	if err != nil {
		t.Errorf("ListRecentEpisodes failed: %v", err)
	}
	t.Log("========== Episodes ==========")
	for _, ep := range episodes {
		icon := "✅"
		if !ep.Success {
			icon = "❌"
		}
		t.Logf("  %s %s: %s", icon, ep.Date, ep.Task)
	}
	if len(episodes) < 2 {
		t.Errorf("expected >= 2 episodes, got %d", len(episodes))
	}

	// ── Step 6: 验证 knowledge 读写 ──
	knowledgeList, err := agent.memory.SearchKnowledge("GPU", 5)
	if err != nil {
		t.Errorf("SearchKnowledge failed: %v", err)
	}
	t.Log("========== Knowledge ==========")
	for _, k := range knowledgeList {
		t.Logf("  %s: %s", k.File, k.Problem)
	}
	if len(knowledgeList) == 0 {
		t.Log("⚠️ SearchKnowledge('GPU') 返回空，检查文件...")
		entries, _ := os.ReadDir(filepath.Join(memRoot, "knowledge"))
		for _, e := range entries {
			data, _ := os.ReadFile(filepath.Join(memRoot, "knowledge", e.Name()))
			t.Logf("  文件: %s -> %.80s", e.Name(), string(data))
		}
	}

	// ── Step 7: 验证联想网络 ──
	// ListRecentEpisodes 返回的 File 已带 "episodes/" 前缀
	epFile := episodes[0].File
	knFile := "knowledge/windows-gpu-detection.md"
	err = agent.memory.Link(epFile, knFile, "relates")
	if err != nil {
		t.Errorf("Link failed: %v", err)
	}
	links, err := agent.memory.GetAssociations(epFile)
	if err != nil {
		t.Errorf("GetAssociations failed: %v", err)
	}
	t.Log("========== 联想网络 ==========")
	for _, l := range links {
		t.Logf("  %s → %s (%s)", l.FromPath, l.ToPath, l.Type)
	}
	if len(links) == 0 {
		t.Error("expected at least 1 association after Link()")
	}

	// ── Step 8: 验证 Recall ──
	allItems, err := agent.memory.Recall("日志", []string{"Windows"}, 10)
	if err != nil {
		t.Errorf("Recall failed: %v", err)
	}
	t.Log("========== Recall ==========")
	for _, item := range allItems {
		t.Logf("  [%s] %.60s", item.Type, item.Path)
	}
	if len(allItems) == 0 {
		t.Log("⚠️ Recall 返回空")
	}

	// ── Step 9: 验证 Stats ──
	stats, err := agent.memory.Stats()
	if err != nil {
		t.Errorf("Stats failed: %v", err)
	}
	t.Log("========== Memory Stats ==========")
	t.Logf("  Sessions: %d", stats.SessionCount)
	t.Logf("  Episodes: %d", stats.EpisodeCount)
	t.Logf("  Knowledge: %d", stats.KnowledgeCount)
	t.Logf("  Commits: %d", stats.TotalCommits)
	t.Logf("  Size: %s", stats.RepoSize)

	if stats.EpisodeCount < 2 {
		t.Errorf("expected >= 2 episodes, got %d", stats.EpisodeCount)
	}
	if stats.KnowledgeCount < 1 {
		t.Errorf("expected >= 1 knowledge, got %d", stats.KnowledgeCount)
	}
	if stats.TotalCommits < 1 {
		t.Errorf("expected >= 1 commits, got %d", stats.TotalCommits)
	}

	// ── Step 10: 验证 git log ──
	history, err := agent.memory.History(5)
	if err != nil {
		t.Errorf("History failed: %v", err)
	}
	t.Log("========== Git History ==========")
	for _, h := range history {
		t.Logf("  %s %s", h.Hash, h.Message)
	}
	if len(history) == 0 {
		t.Error("expected git history entries")
	}
}

func TestAgentMemoryInitFailsGracefully(t *testing.T) {
	// 验证：即使 memory 初始化失败，Agent 也能正常工作
	agent := NewAgent(nil, nil, "/tmp/this-path-does-not-exist/_memory")
	if agent == nil {
		t.Fatal("Agent should still be created even if memory init fails")
	}
	if agent.llm == nil {
		t.Error("agent.llm should not be nil")
	}
	if agent.tools == nil {
		t.Error("agent.tools should not be nil")
	}
	// memory 为 nil 时 buildSystemPrompt 不应 panic
	req := &AgentRequest{Task: "测试任务"}
	prompt := agent.buildSystemPrompt(req)
	if prompt == "" {
		t.Error("prompt should not be empty even without memory")
	}
	if !contains(prompt, "响应格式") {
		t.Error("basic prompt structure should still be present")
	}
}

func TestAgentMemoryRecordAndRecover(t *testing.T) {
	// 验证：Agent 记录 → 关闭 → 重新加载 → 数据恢复
	root := t.TempDir()
	memRoot := filepath.Join(root, "opc-memory")

	// 第一次生命周期
	func() {
		agent := NewAgent(nil, nil, memRoot)
		if agent.memory == nil {
			t.Fatal("memory should be loaded")
		}
		agent.memory.SaveEpisode("第一次运行", "完成", true, "测试数据")
		agent.memory.AppendSession("persist-test", "User", "持久化测试")
		agent.memory.AutoCommit()
		agent.memory.Close()
	}()

	// 第二次生命周期——重新加载
	agent := NewAgent(nil, nil, memRoot)
	if agent.memory == nil {
		t.Fatal("memory should be reloaded")
	}

	// 验证数据还在
	episodes, _ := agent.memory.SearchEpisodes("第一次", 5)
	if len(episodes) == 0 {
		t.Error("❌ episode 在重启后丢失")
	} else {
		t.Logf("✅ episode 重启后恢复: %s", episodes[0].Task)
	}

	session, err := agent.memory.GetSession("persist-test")
	if err != nil {
		t.Errorf("❌ session 在重启后丢失: %v", err)
	} else if contains(session, "持久化测试") {
		t.Log("✅ session 重启后恢复")
	} else {
		t.Error("❌ session 内容异常")
	}

	history, _ := agent.memory.History(5)
	t.Logf("✅ git 历史: %d commits", len(history))
}
