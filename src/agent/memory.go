// Package agent — Git 记忆系统
//
// SPEC-MEMORY-001 v1.1 实现
// 向人类记忆学习：时间轴 + 联想网络 + 衰减强化 + 永不删除
//
// 依赖: Go 标准库 + 系统 git 命令
package agent

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ====================================================================== //
//  Memory 接口定义
// ====================================================================== //

// Memory 是 Agent 记忆系统的接口。
// 所有实现必须满足此接口。
type Memory interface {
	// ──────── 仓库管理 ────────

	// Init 初始化记忆仓库。已存在则直接加载。
	Init() error

	// Close 执行最终 commit 并释放资源。
	Close() error

	// ──────── 短期记忆：对话 ────────

	AppendSession(sessionID string, role string, content string) error
	GetSession(sessionID string) (string, error)
	ListSessions(limit int) ([]SessionInfo, error)

	// ──────── 中期记忆：经验 ────────

	SaveEpisode(task string, result string, success bool, learned string) error
	SearchEpisodes(query string, limit int) ([]EpisodeSummary, error)
	ListRecentEpisodes(limit int) ([]EpisodeSummary, error)

	// ──────── 长期记忆：知识 ────────

	SaveKnowledge(topic string, content string) error
	ListRecentKnowledge(limit int) ([]KnowledgeSummary, error)
	SearchKnowledge(query string, limit int) ([]KnowledgeSummary, error)

	// ──────── 系统状态 ────────

	UpdateSystemStatus(systemJSON string) error
	GetSystemStatus() (string, error)

	// ──────── 联想网络 ────────

	// Link 在两个记忆文件之间创建关联链接。
	Link(fromPath, toPath, linkType string) error

	// GetAssociations 获取某个记忆文件的所有关联。
	GetAssociations(filepath string) ([]Link, error)

	// Recall 按场景标签 + 关键词检索记忆。
	// 返回结果按强度排序，自动强化命中条目。
	Recall(query string, sceneTags []string, limit int) ([]MemoryItem, error)

	// ──────── 衰减与归档 ────────

	// OnRecall 通知系统某条记忆被检索命中，触发强化。
	OnRecall(filepath string)

	// DailyDecay 对所有 episode 执行一次衰减。由 Brain 每天调用。
	DailyDecay() error

	// ──────── Git 操作 ────────

	Commit(message string) error
	AutoCommit() error
	History(limit int) ([]CommitInfo, error)
	Diff(commitHash string) (string, error)

	// ──────── 查询统计 ────────

	Stats() (*MemoryStats, error)
}

// ──────── 数据结构 ────────

type SessionInfo struct {
	ID           string    `json:"id"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	MessageCount int       `json:"message_count"`
	Source       string    `json:"source"`
	Summary      string    `json:"summary,omitempty"`
	Archived     bool      `json:"archived"`
}

type EpisodeSummary struct {
	File       string `json:"file"`
	Title      string `json:"title"`
	Date       string `json:"date"`
	Task       string `json:"task"`
	Success    bool   `json:"success"`
	Learned    string `json:"learned,omitempty"`
	Strength   float64
	Archived   bool `json:"archived"`
}

type KnowledgeSummary struct {
	File     string `json:"file"`
	Topic    string `json:"topic"`
	Problem  string `json:"problem"`
	Verified string `json:"verified"`
}

type CommitInfo struct {
	Hash       string    `json:"hash"`
	Author     string    `json:"author"`
	Date       time.Time `json:"date"`
	Message    string    `json:"message"`
	Files      int       `json:"files"`
	Insertions int       `json:"insertions"`
	Deletions  int       `json:"deletions"`
}

type MemoryStats struct {
	SessionCount   int    `json:"session_count"`
	EpisodeCount   int    `json:"episode_count"`
	KnowledgeCount int    `json:"knowledge_count"`
	ArchivedCount  int    `json:"archived_count"`
	TotalCommits   int    `json:"total_commits"`
	RepoSize       string `json:"repo_size"`
	LastCommit     string `json:"last_commit"`
}

type MemoryItem struct {
	Path      string  `json:"path"`
	Title     string  `json:"title"`
	Type      string  `json:"type"` // session / episode / knowledge
	Strength  float64 `json:"strength"`
	Tags      string  `json:"tags"`
	Created   string  `json:"created"`
	Archived  bool    `json:"archived"`
	Snippet   string  `json:"snippet"`
}

type Link struct {
	FromPath string `json:"from_path"`
	ToPath   string `json:"to_path"`
	Type     string `json:"type"` // relates / causes / solves / follows / similar / contradicts
}

// ====================================================================== //
//  衰减策略配置
// ====================================================================== //

type DecayConfig struct {
	DailyDecay          float64 `json:"daily_decay"`           // 默认 0.02
	NeglectAccel        float64 `json:"neglect_accel"`         // 默认 0.1
	DirectHitReinforce  float64 `json:"direct_hit_reinforce"`  // 默认 0.3
	AssocHitReinforce   float64 `json:"assoc_hit_reinforce"`   // 默认 0.1
	SummarizeThreshold  float64 `json:"summarize_threshold"`   // 默认 0.15
	ArchiveThreshold    float64 `json:"archive_threshold"`     // 默认 0.05
	BatchSize           int     `json:"batch_size"`            // 默认 20
}

func DefaultDecayConfig() DecayConfig {
	return DecayConfig{
		DailyDecay:         0.02,
		NeglectAccel:       0.1,
		DirectHitReinforce: 0.3,
		AssocHitReinforce:  0.1,
		SummarizeThreshold: 0.15,
		ArchiveThreshold:   0.05,
		BatchSize:          20,
	}
}

// ====================================================================== //
//  GitMemory 实现
// ====================================================================== //

// GitMemory Git 驱动的记忆系统。
// 所有文件以 UTF-8 Markdown 存储，利用 git 做版本控制。
// 永远不会删除任何内容——只移入 archive/ 目录。
type GitMemory struct {
	root       string          // 仓库根目录
	cfg        DecayConfig
	mu         sync.Mutex
	dirty      bool
	lastCommit time.Time

	// 内存中的衰减状态（每日从文件加载，DailyDecay 时写回）
	strengths map[string]*memStrength
}

type memStrength struct {
	Path        string    `json:"path"`
	Strength    float64   `json:"strength"`
	AccessCount int       `json:"access_count"`
	LastAccess  time.Time `json:"last_access"`
	State       string    `json:"state"` // active / decaying / summarized / archived
}

// ──────── 构造与初始化 ────────

// NewGitMemory 创建/打开一个 Git 记忆仓库。
// root 为空时使用 ~/.computehub/memory 作为默认路径（与升级管理器共用数据目录）。
func NewGitMemory(root string) (*GitMemory, error) {
	if root == "" {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			homeDir = "/home/computehub" // fallback
		}
		root = filepath.Join(homeDir, ".computehub", "memory")
	}
	gm := &GitMemory{
		root:       root,
		cfg:        DefaultDecayConfig(),
		lastCommit: time.Now(),
		strengths:  make(map[string]*memStrength),
	}
	if err := gm.Init(); err != nil {
		return nil, fmt.Errorf("init memory: %w", err)
	}
	return gm, nil
}

// Init 初始化记忆仓库。已存在则直接加载。
func (gm *GitMemory) Init() error {
	// 创建目录结构
	dirs := []string{
		filepath.Join(gm.root, "sessions"),
		filepath.Join(gm.root, "episodes"),
		filepath.Join(gm.root, "knowledge"),
		filepath.Join(gm.root, "system"),
		filepath.Join(gm.root, "archive", "sessions"),
		filepath.Join(gm.root, "archive", "episodes"),
		filepath.Join(gm.root, "archive", "knowledge"),
	}
	for _, d := range dirs {
		if err := os.MkdirAll(d, 0755); err != nil {
			return fmt.Errorf("mkdir %s: %w", d, err)
		}
	}

	// 检查是否已初始化
	gitDir := filepath.Join(gm.root, ".git")
	if _, err := os.Stat(gitDir); err == nil {
		// 已初始化，验证完整性
		return gm.verify()
	}

	// git init
	if out, err := gm.git("init"); err != nil {
		return fmt.Errorf("git init: %s: %w", out, err)
	}

	// 设置 git config
	gm.git("config", "user.name", "ComputeHub Agent")
	gm.git("config", "user.email", "agent@computehub.ai")
	gm.git("config", "core.autocrlf", "input")
	gm.git("config", "commit.gpgsign", "false")

	// 写 README
	readme := strings.TrimSpace(`
# OPC Agent Memory

> Auto-managed by ComputeHub Agent
> SPEC-MEMORY-001 v1.1

## 目录结构
- sessions/    — 短期记忆：对话记录（永不删除）
- episodes/   — 中期记忆：执行经验（30天后归档）
- knowledge/  — 长期记忆：已验证的知识（永久）
- system/     — 集群状态快照（每次心跳更新）
- archive/    — 已归档的记忆（强度衰减后的记忆，永不丢失）
`)
	if err := os.WriteFile(filepath.Join(gm.root, "README.md"), []byte(readme), 0644); err != nil {
		return fmt.Errorf("write README: %w", err)
	}

	// .gitignore
	gitignore := "*.swp\n*.tmp\n*.log\n.DS_Store\n"
	if err := os.WriteFile(filepath.Join(gm.root, ".gitignore"), []byte(gitignore), 0644); err != nil {
		return fmt.Errorf("write .gitignore: %w", err)
	}

	// 首次提交
	gm.git("add", "-A")
	if out, err := gm.git("commit", "-m", "init: OPC Agent Memory repository"); err != nil {
		return fmt.Errorf("first commit: %s: %w", out, err)
	}

	// 尝试加载已有的强度数据
	gm.loadStrengths()

	return nil
}

// Close 执行最终 commit 并释放资源。
func (gm *GitMemory) Close() error {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	if gm.dirty {
		_, err := gm.git("add", "-A")
		if err != nil {
			return err
		}
		_, err = gm.git("commit", "-m",
			fmt.Sprintf("auto: memory shutdown at %s", time.Now().Format("2006-01-02 15:04")))
		return err
	}
	return nil
}

// verify 检查仓库完整性。
func (gm *GitMemory) verify() error {
	out, err := gm.git("fsck")
	if err != nil {
		log.Printf("[Memory] ⚠️ git fsck 发现异常，尝试自动修复: %s", out)
		// 轻量修复
		gm.git("checkout", "HEAD")
		// 重新验证
		out2, err2 := gm.git("fsck")
		if err2 != nil {
			return fmt.Errorf("memory repo damaged, auto-repair failed: %s / %s", out, out2)
		}
		log.Printf("[Memory] ✅ 自动修复成功")
	}
	return nil
}

// ====================================================================== //
//  短期记忆：会话
// ====================================================================== //

// AppendSession 追加一条对话消息到 session 文件。
func (gm *GitMemory) AppendSession(sessionID, role, content string) error {
	if sessionID == "" {
		return ErrSessionEmpty
	}
	if !isValidRole(role) {
		return ErrInvalidRole
	}

	content, err := sanitize(content)
	if err != nil {
		return err
	}

	gm.mu.Lock()
	defer gm.mu.Unlock()

	path := filepath.Join(gm.root, "sessions", sessionID+".md")
	now := time.Now()

	// 文件存在？
	if _, err := os.Stat(path); os.IsNotExist(err) {
		header := fmt.Sprintf("# Session: %s\n> Type: session\n> SessionID: %s\n> Created: %s\n> Updated: %s\n> Source: tui\n> Summarized: false\n\n",
			sessionID, sessionID, now.Format("2006-01-02 15:04:05"), now.Format("2006-01-02 15:04:05"))
		if err := os.WriteFile(path, []byte(header), 0644); err != nil {
			return fmt.Errorf("create session: %w", err)
		}
	} else {
		// 更新 Updated 时间戳（简单方式：写新行保留头部）
	}

	// 追加消息
	ts := now.Format("15:04:05")
	entry := fmt.Sprintf("## %s — %s\n%s\n\n", ts, role, content)
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("append session: %w", err)
	}
	defer f.Close()
	if _, err := f.WriteString(entry); err != nil {
		return fmt.Errorf("write session: %w", err)
	}

	gm.dirty = true

	// 检查是否超 50 条，超了标记待压缩（实际压缩需 LLM）
	gm.checkSessionLength(sessionID, path)

	return nil
}

// GetSession 读取完整对话内容。
func (gm *GitMemory) GetSession(sessionID string) (string, error) {
	// 先在 sessions/ 中找
	path := filepath.Join(gm.root, "sessions", sessionID+".md")
	data, err := os.ReadFile(path)
	if err == nil {
		gm.OnRecall("sessions/" + sessionID + ".md")
		return string(data), nil
	}

	// 再在 archive/sessions/ 中找
	path = filepath.Join(gm.root, "archive", "sessions", sessionID+".md")
	data, err = os.ReadFile(path)
	if err == nil {
		gm.OnRecall("archive/sessions/" + sessionID + ".md")
		return string(data), nil
	}

	return "", fmt.Errorf("session %s not found", sessionID)
}

// ListSessions 列出最近的 session。
func (gm *GitMemory) ListSessions(limit int) ([]SessionInfo, error) {
	// 搜索 sessions/ 和 archive/sessions/
	var sessions []SessionInfo
	searchDirs := []string{
		filepath.Join(gm.root, "sessions"),
		filepath.Join(gm.root, "archive", "sessions"),
	}

	for _, dir := range searchDirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		archived := strings.Contains(dir, "archive")
		for _, e := range entries {
			if !strings.HasSuffix(e.Name(), ".md") || !strings.HasPrefix(e.Name(), "session-") {
				continue
			}
			fi, err := e.Info()
			if err != nil {
				continue
			}
			id := strings.TrimSuffix(e.Name(), ".md")
			sessions = append(sessions, SessionInfo{
				ID:        id,
				CreatedAt: fi.ModTime(),
				UpdatedAt: fi.ModTime(),
				Archived:  archived,
			})
		}
	}

	// 按修改时间倒序
	sort.Slice(sessions, func(i, j int) bool {
		return sessions[i].UpdatedAt.After(sessions[j].UpdatedAt)
	})

	if limit > 0 && len(sessions) > limit {
		sessions = sessions[:limit]
	}

	// 补充消息数
	for i := range sessions {
		dir := "sessions"
		if sessions[i].Archived {
			dir = "archive/sessions"
		}
		path := filepath.Join(gm.root, dir, sessions[i].ID+".md")
		sessions[i].MessageCount = countSectionHeaders(path)
	}

	return sessions, nil
}

// ====================================================================== //
//  中期记忆：经验
// ====================================================================== //

// SaveEpisode 保存一条执行经验。
func (gm *GitMemory) SaveEpisode(task, result string, success bool, learned string) error {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	// 生成文件名
	slug := slugify(task)
	if len(slug) > 40 {
		slug = slug[:40]
	}
	filename := fmt.Sprintf("%s-%s.md", time.Now().Format("2006-01-02"), slug)
	path := filepath.Join(gm.root, "episodes", filename)

	icon := "✅"
	if !success {
		icon = "❌"
	}

	// 安全过滤
	task, _ = sanitize(task)
	result, _ = sanitize(result)
	learned, _ = sanitize(learned)

	// 强度 = 1.0（新创建）
	strengthKey := "episodes/" + filename

	content := fmt.Sprintf(`# Episode: %s
> Type: episode
> Date: %s
> Success: %s
> Strength: 1.0
> AccessCount: 0
> State: active
> Associations:

## Task
%s

## Result
%s

## Learned
%s
`, task, time.Now().Format("2006-01-02 15:04:05"), icon, task, result, learned)

	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		return fmt.Errorf("save episode: %w", err)
	}

	gm.strengths[strengthKey] = &memStrength{
		Path:     strengthKey,
		Strength: 1.0,
		State:    "active",
	}

	gm.dirty = true

	// 重要事件立即 commit
	if success {
		gm.mu.Unlock()
		gm.Commit(fmt.Sprintf("episode: %s (%s)", slug, icon))
		gm.mu.Lock()
	} else {
		gm.mu.Unlock()
		gm.Commit(fmt.Sprintf("episode: %s (%s)", slug, icon+" failed"))
		gm.mu.Lock()
	}

	return nil
}

// SearchEpisodes 按关键词搜索 episode。
// 使用文件内容直接搜索（支持中文），git grep 辅助。
func (gm *GitMemory) SearchEpisodes(query string, limit int) ([]EpisodeSummary, error) {
	if limit <= 0 {
		limit = 10
	}

	var results []EpisodeSummary
	lowerQuery := strings.ToLower(query)

	for _, dir := range []string{"episodes", "archive/episodes"} {
		fullDir := filepath.Join(gm.root, dir)
		entries, err := os.ReadDir(fullDir)
		if err != nil {
			continue
		}
		archived := strings.Contains(dir, "archive")

		for _, e := range entries {
			if !strings.HasSuffix(e.Name(), ".md") {
				continue
			}
			relPath := dir + "/" + e.Name()
			content, err := os.ReadFile(filepath.Join(fullDir, e.Name()))
			if err != nil {
				continue
			}
			if !strings.Contains(strings.ToLower(string(content)), lowerQuery) {
				continue
			}
			sum, err := gm.readEpisodeSummary(relPath)
			if err != nil {
				continue
			}
			sum.Archived = archived
			results = append(results, sum)
		}
	}

	// 按强度排序（优先返回活跃记忆）
	sort.Slice(results, func(i, j int) bool {
		return results[i].Strength > results[j].Strength
	})

	if len(results) > limit {
		results = results[:limit]
	}

	// 强化命中的记忆
	for _, r := range results {
		gm.OnRecall(r.File)
	}

	return results, nil
}

// ListRecentEpisodes 列出最近的 N 条活跃 episode。
func (gm *GitMemory) ListRecentEpisodes(limit int) ([]EpisodeSummary, error) {
	if limit <= 0 {
		limit = 10
	}

	entries, err := os.ReadDir(filepath.Join(gm.root, "episodes"))
	if err != nil {
		return nil, fmt.Errorf("read episodes dir: %w", err)
	}

	var episodes []EpisodeSummary
	for _, e := range entries {
		if !strings.HasSuffix(e.Name(), ".md") {
			continue
		}
		ep, err := gm.readEpisodeSummary("episodes/" + e.Name())
		if err != nil {
			continue
		}
		episodes = append(episodes, ep)
	}

	// 按文件名（含日期）倒序
	sort.Slice(episodes, func(i, j int) bool {
		return episodes[i].File > episodes[j].File
	})

	if len(episodes) > limit {
		episodes = episodes[:limit]
	}

	return episodes, nil
}

// ====================================================================== //
//  长期记忆：知识
// ====================================================================== //

// SaveKnowledge 保存一条验证过的知识。
func (gm *GitMemory) SaveKnowledge(topic string, content string) error {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	slug := slugify(topic)
	if len(slug) > 60 {
		slug = slug[:60]
	}
	filename := slug + ".md"
	path := filepath.Join(gm.root, "knowledge", filename)

	content, _ = sanitize(content)

	full := fmt.Sprintf(`# Knowledge: %s
> Type: knowledge
> Verified: %s
> Author: Agent

## Problem
%s

## Solution
%s

## Edge Cases
%s
`, topic, time.Now().Format("2006-01-02"), topic, content, "（待补充）")

	if err := os.WriteFile(path, []byte(full), 0644); err != nil {
		return fmt.Errorf("save knowledge: %w", err)
	}

	gm.dirty = true

	gm.mu.Unlock()
	gm.Commit(fmt.Sprintf("knowledge: %s", slug))
	gm.mu.Lock()

	return nil
}

// ListRecentKnowledge 列出最近的 N 条知识。
func (gm *GitMemory) ListRecentKnowledge(limit int) ([]KnowledgeSummary, error) {
	if limit <= 0 {
		limit = 100
	}

	var summaries []KnowledgeSummary

	// 读取 knowledge/ 目录
	files, err := os.ReadDir(filepath.Join(gm.root, "knowledge"))
	if err != nil {
		return nil, fmt.Errorf("read knowledge dir: %w", err)
	}

	for _, e := range files {
		if !strings.HasSuffix(e.Name(), ".md") {
			continue
		}
		summary, err := gm.readKnowledgeSummary("knowledge/" + e.Name())
		if err != nil {
			continue
		}
		summaries = append(summaries, summary)
	}

	// 按文件名排序（时间倒序，新文件在前）
	sort.Slice(summaries, func(i, j int) bool {
		return summaries[i].File > summaries[j].File
	})

	if len(summaries) > limit {
		summaries = summaries[:limit]
	}

	return summaries, nil
}

// readKnowledgeSummary 从 knowledge 文件路径读取摘要。
func (gm *GitMemory) readKnowledgeSummary(relPath string) (KnowledgeSummary, error) {
	data, err := os.ReadFile(filepath.Join(gm.root, relPath))
	if err != nil {
		return KnowledgeSummary{}, err
	}

	var km KnowledgeSummary
	km.File = relPath

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "# Knowledge: ") {
			km.Topic = strings.TrimPrefix(line, "# Knowledge: ")
		} else if strings.HasPrefix(line, "> Problem: ") {
			km.Problem = strings.TrimPrefix(line, "> Problem: ")
		} else if strings.HasPrefix(line, "> Verified: ") {
			km.Verified = strings.TrimPrefix(line, "> Verified: ")
		}
	}

	return km, nil
}

// SearchKnowledge 搜索知识库（文件内容搜索，支持中文）。
func (gm *GitMemory) SearchKnowledge(query string, limit int) ([]KnowledgeSummary, error) {
	if limit <= 0 {
		limit = 10
	}

	var results []KnowledgeSummary
	lowerQuery := strings.ToLower(query)

	for _, dir := range []string{"knowledge", "archive/knowledge"} {
		fullDir := filepath.Join(gm.root, dir)
		entries, err := os.ReadDir(fullDir)
		if err != nil {
			continue
		}
		for _, e := range entries {
			if !strings.HasSuffix(e.Name(), ".md") {
				continue
			}
			relPath := dir + "/" + e.Name()
			data, err := os.ReadFile(filepath.Join(fullDir, e.Name()))
			if err != nil {
				continue
			}
			if !strings.Contains(strings.ToLower(string(data)), lowerQuery) {
				continue
			}
			results = append(results, KnowledgeSummary{
				File:    relPath,
				Topic:   extractTitle(string(data)),
				Problem: extractField(string(data), "## Problem"),
			})
		}
	}

	if len(results) > limit {
		results = results[:limit]
	}

	return results, nil
}

// ====================================================================== //
//  系统状态
// ====================================================================== //

// UpdateSystemStatus 更新集群状态快照。
func (gm *GitMemory) UpdateSystemStatus(systemJSON string) error {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	path := filepath.Join(gm.root, "system", "cluster-status.md")

	var parsed map[string]interface{}
	json.Unmarshal([]byte(systemJSON), &parsed)

	content := fmt.Sprintf(`# System: Cluster Status
> Type: system
> Updated: %s

`, time.Now().Format("2006-01-02 15:04:05"))

	// 将 JSON 转为可读的 Markdown
	if parsed != nil {
		for k, v := range parsed {
			switch val := v.(type) {
			case map[string]interface{}:
				content += fmt.Sprintf("## %s\n", k)
				for sk, sv := range val {
					content += fmt.Sprintf("- %s: %v\n", sk, sv)
				}
				content += "\n"
			default:
				content += fmt.Sprintf("- %s: %v\n", k, val)
			}
		}
	} else {
		content += "```json\n" + systemJSON + "\n```\n"
	}

	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		return fmt.Errorf("update system status: %w", err)
	}

	gm.dirty = true
	return nil
}

// GetSystemStatus 读取当前集群状态。
func (gm *GitMemory) GetSystemStatus() (string, error) {
	path := filepath.Join(gm.root, "system", "cluster-status.md")
	data, err := os.ReadFile(path)
	if err != nil {
		return "", nil // 还没写状态不返回错误
	}
	return string(data), nil
}

// ====================================================================== //
//  联想网络
// ====================================================================== //

// Link 在两个记忆文件之间创建关联链接。
// 链接写入源文件的 Associations 元数据字段。
func (gm *GitMemory) Link(fromPath, toPath, linkType string) error {
	if linkType == "" {
		linkType = "relates"
	}
	validTypes := map[string]bool{"relates": true, "causes": true, "solves": true, "follows": true, "similar": true, "contradicts": true}
	if !validTypes[linkType] {
		return fmt.Errorf("invalid link type: %s", linkType)
	}

	gm.mu.Lock()
	defer gm.mu.Unlock()

	fullPath := filepath.Join(gm.root, fromPath)
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return fmt.Errorf("read source: %w", err)
	}

	content := string(data)
	linkLine := fmt.Sprintf("> Associations: %s (%s)", toPath, linkType)

	// 检查是否已经有 Associations 字段
	if strings.Contains(content, "> Associations:") {
		// 追加到已有字段
		re := regexp.MustCompile(`(> Associations:.*)`)
		existing := re.FindString(content)
		if !strings.Contains(existing, toPath) {
			content = strings.Replace(content, existing,
				existing+", "+fmt.Sprintf("%s (%s)", toPath, linkType), 1)
		} else {
			return nil // 已存在相同链接
		}
	} else {
		// 在第一个元数据行后追加
		content = strings.Replace(content, "> Type:", "> Associations:\n> Type:", 1)
		// 更稳妥：追加在文件头
		content = strings.Replace(content, "---\n", fmt.Sprintf("> %s\n---\n", linkLine), 1)
		// 兜底：直接插在标题后
		if !strings.Contains(content, "> Associations:") {
			lines := strings.SplitN(content, "\n", 3)
			if len(lines) >= 2 {
				content = lines[0] + "\n" + linkLine + "\n" + lines[1]
				if len(lines) >= 3 {
					content += "\n" + lines[2]
				}
			}
		}
	}

	if err := os.WriteFile(fullPath, []byte(content), 0644); err != nil {
		return fmt.Errorf("write link: %w", err)
	}

	gm.dirty = true
	return nil
}

// GetAssociations 获取某个记忆文件的所有关联。
func (gm *GitMemory) GetAssociations(relPath string) ([]Link, error) {
	fullPath := filepath.Join(gm.root, relPath)
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return nil, fmt.Errorf("read file: %w", err)
	}

	content := string(data)
	re := regexp.MustCompile(`> Associations:\s*(.*)`)
	match := re.FindStringSubmatch(content)
	if len(match) < 2 {
		return nil, nil
	}

	assocStr := strings.TrimSpace(match[1])
	if assocStr == "" {
		return nil, nil
	}

	var links []Link
	parts := strings.Split(assocStr, ",")
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		// 格式："path/to/file (linktype)"
		re2 := regexp.MustCompile(`(.*?)\s*\((\w+)\)`)
		m := re2.FindStringSubmatch(p)
		if len(m) >= 3 {
			links = append(links, Link{
				FromPath: relPath,
				ToPath:   strings.TrimSpace(m[1]),
				Type:     m[2],
			})
		} else {
			links = append(links, Link{
				FromPath: relPath,
				ToPath:   p,
				Type:     "relates",
			})
		}
	}
	return links, nil
}

// Recall 按场景标签 + 关键词检索记忆。
// 返回结果按强度排序，自动强化命中条目。
func (gm *GitMemory) Recall(query string, sceneTags []string, limit int) ([]MemoryItem, error) {
	if limit <= 0 {
		limit = 10
	}

	seen := make(map[string]bool)
	var items []MemoryItem

	// Step 1: 用场景标签定位（搜索 INDEX 或文件名匹配）
	for _, tag := range sceneTags {
		tagResults := gm.searchByTag(tag)
		for _, item := range tagResults {
			if !seen[item.Path] {
				seen[item.Path] = true
				items = append(items, item)
			}
		}
	}

	// Step 2: 关键词全文搜索（文件内容直接搜索，支持中文）
	if query != "" {
		lowerQuery := strings.ToLower(query)
		for _, dir := range []string{"episodes", "knowledge", "sessions", "archive/episodes", "archive/knowledge"} {
			fullDir := filepath.Join(gm.root, dir)
			entries, err := os.ReadDir(fullDir)
			if err != nil {
				continue
			}
			for _, e := range entries {
				if !strings.HasSuffix(e.Name(), ".md") {
					continue
				}
				relPath := dir + "/" + e.Name()
				if seen[relPath] {
					continue
				}
				data, err := os.ReadFile(filepath.Join(fullDir, e.Name()))
				if err != nil {
					continue
				}
				if !strings.Contains(strings.ToLower(string(data)), lowerQuery) {
					continue
				}
				seen[relPath] = true
				item, err := gm.readMemoryItem(relPath)
				if err != nil {
					continue
				}
				items = append(items, item)
			}
		}
	}

	// Step 3: 联想扩展（找到的结果的关联也带上）
	var expanded []MemoryItem
	expanded = append(expanded, items...)
	for _, item := range items {
		assocs, err := gm.GetAssociations(item.Path)
		if err != nil {
			continue
		}
		for _, link := range assocs {
			if !seen[link.ToPath] {
				seen[link.ToPath] = true
				assocItem, err := gm.readMemoryItem(link.ToPath)
				if err != nil {
					continue
				}
				expanded = append(expanded, assocItem)
			}
		}
	}
	items = expanded

	// Step 4: 按强度排序
	sort.Slice(items, func(i, j int) bool {
		return items[i].Strength > items[j].Strength
	})

	if len(items) > limit {
		items = items[:limit]
	}

	// Step 5: 强化命中的记忆
	for _, item := range items {
		gm.OnRecall(item.Path)
		for _, link := range gm.mustGetAssociations(item.Path) {
			gm.weakReinforce(link.ToPath)
		}
	}

	return items, nil
}

// ====================================================================== //
//  衰减与归档
// ====================================================================== //

// OnRecall 通知系统某条记忆被检索命中，触发强化。
func (gm *GitMemory) OnRecall(path string) {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	strengthKey := strings.TrimPrefix(path, gm.root+"/")
	s, ok := gm.strengths[strengthKey]
	if !ok {
		// 尚未在内存中，从文件读取
		s = &memStrength{
			Path:     strengthKey,
			Strength: 1.0,
			State:    "active",
		}
		gm.strengths[strengthKey] = s
	}

	s.Strength = s.Strength + gm.cfg.DirectHitReinforce
	if s.Strength > 1.0 {
		s.Strength = 1.0
	}
	s.AccessCount++
	s.LastAccess = time.Now()
}

func (gm *GitMemory) weakReinforce(path string) {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	s, ok := gm.strengths[path]
	if !ok {
		s = &memStrength{Path: path, Strength: 1.0, State: "active"}
		gm.strengths[path] = s
	}

	s.Strength = s.Strength + gm.cfg.AssocHitReinforce
	if s.Strength > 1.0 {
		s.Strength = 1.0
	}
}

// DailyDecay 对所有 episode 执行一次衰减。由 Brain 每天调用。
func (gm *GitMemory) DailyDecay() error {
	gm.mu.Lock()
	defer gm.mu.Unlock()

	now := time.Now()
	var toArchive []string

	for key, s := range gm.strengths {
		if s.State == "archived" {
			continue // 已归档不再衰减
		}
		if s.State == "summarized" {
			continue // 已摘要化继续保留
		}

		// 计算未访问天数
		daysSinceAccess := now.Sub(s.LastAccess).Hours() / 24
		if daysSinceAccess < 0 {
			daysSinceAccess = 0
		}

		// 衰减：基础衰减 + 遗忘加速
		decay := gm.cfg.DailyDecay * (1 + daysSinceAccess*gm.cfg.NeglectAccel)
		s.Strength -= decay
		if s.Strength < 0 {
			s.Strength = 0
		}

		if s.Strength < gm.cfg.ArchiveThreshold {
			s.State = "archived"
			toArchive = append(toArchive, key)
		} else if s.Strength < gm.cfg.SummarizeThreshold {
			s.State = "summarized"
		}
	}

	// 执行归档：移入 archive/
	for _, key := range toArchive {
		if err := gm.moveToArchive(key); err != nil {
			log.Printf("[Memory] ⚠️ 归档失败 %s: %v", key, err)
		}
	}

	// 保存强度数据
	gm.saveStrengths()

	gm.dirty = true

	// 归档操作 commit
	if len(toArchive) > 0 {
		gm.mu.Unlock()
		gm.Commit(fmt.Sprintf("archive: %d memories moved to archive", len(toArchive)))
		gm.mu.Lock()
	}

	return nil
}

// moveToArchive 将记忆文件从原目录移入 archive/。
func (gm *GitMemory) moveToArchive(key string) error {
	src := filepath.Join(gm.root, key)
	dst := filepath.Join(gm.root, "archive", key)

	// 确保目标目录存在
	os.MkdirAll(filepath.Dir(dst), 0755)

	if err := os.Rename(src, dst); err != nil {
		return fmt.Errorf("move %s → %s: %w", src, dst, err)
	}

	return nil
}

// ====================================================================== //
//  Git 操作
// ====================================================================== //

// Commit 提交所有未提交的改动。
func (gm *GitMemory) Commit(message string) error {
	if !gm.dirty {
		return nil
	}
	if len(message) > 72 {
		message = message[:72]
	}

	_, err := gm.git("add", "-A")
	if err != nil {
		return fmt.Errorf("git add: %w", err)
	}

	out, err := gm.git("commit", "-m", message)
	if err != nil {
		// "nothing to commit" 不是错误
		if strings.Contains(out, "nothing to commit") {
			gm.dirty = false
			return nil
		}
		return fmt.Errorf("git commit: %s: %w", out, err)
	}

	gm.dirty = false
	gm.lastCommit = time.Now()
	return nil
}

// AutoCommit 自动提交。
func (gm *GitMemory) AutoCommit() error {
	if !gm.dirty {
		return nil
	}
	return gm.Commit(fmt.Sprintf("auto: memory update at %s",
		time.Now().Format("2006-01-02 15:04")))
}

// History 查看历史 commit 列表。
func (gm *GitMemory) History(limit int) ([]CommitInfo, error) {
	if limit <= 0 {
		limit = 30
	}
	out, err := gm.git("log", fmt.Sprintf("-%d", limit),
		"--format=%H|%an|%ai|%s", "--shortstat")
	if err != nil {
		return nil, fmt.Errorf("git log: %w", err)
	}

	lines := strings.Split(out, "\n")
	var commits []CommitInfo
	for i := 0; i < len(lines); i++ {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "|", 4)
		if len(parts) < 4 {
			continue
		}
		date, _ := time.Parse("2006-01-02 15:04:05 -0700", parts[2])
		ci := CommitInfo{
			Hash:    parts[0][:8],
			Author:  parts[1],
			Date:    date,
			Message: parts[3],
		}
		// 下一行是 shortstat
		if i+1 < len(lines) {
			stat := strings.TrimSpace(lines[i+1])
			fmt.Sscanf(stat, " %d file(s) changed, %d insertion(s), %d deletion(s)",
				&ci.Files, &ci.Insertions, &ci.Deletions)
			i++
		}
		commits = append(commits, ci)
	}
	return commits, nil
}

// Diff 查看某次 commit 的改动。
func (gm *GitMemory) Diff(commitHash string) (string, error) {
	out, err := gm.git("diff", commitHash+"^.."+commitHash, "--stat", "--", "-S", ".md")
	if err != nil {
		// 可能是第一个 commit
		out, err = gm.git("show", "--stat", commitHash)
		if err != nil {
			return "", fmt.Errorf("git diff: %w", err)
		}
	}
	return out, nil
}

// ====================================================================== //
//  查询统计
// ====================================================================== //

// Stats 返回记忆仓库统计信息。
func (gm *GitMemory) Stats() (*MemoryStats, error) {
	stats := &MemoryStats{}

	// 计数
	sessions, _ := filepath.Glob(filepath.Join(gm.root, "sessions", "*.md"))
	episodes, _ := filepath.Glob(filepath.Join(gm.root, "episodes", "*.md"))
	knowledge, _ := filepath.Glob(filepath.Join(gm.root, "knowledge", "*.md"))
	archived, _ := filepath.Glob(filepath.Join(gm.root, "archive", "**", "*.md"))

	stats.SessionCount = len(sessions)
	stats.EpisodeCount = len(episodes)
	stats.KnowledgeCount = len(knowledge)
	stats.ArchivedCount = len(archived)

	// commit 数
	out, _ := gm.git("rev-list", "--count", "HEAD")
	if out != "" {
		fmt.Sscanf(strings.TrimSpace(out), "%d", &stats.TotalCommits)
	}

	// 仓库大小
	out, _ = gm.git("count-objects", "-H")
	stats.RepoSize = strings.TrimSpace(out)

	// 最后 commit
	out, _ = gm.git("log", "-1", "--format=%ai")
	if out != "" {
		stats.LastCommit = strings.TrimSpace(out)
	}

	return stats, nil
}

// ====================================================================== //
//  内部工具函数
// ====================================================================== //

// ──────── Git 命令 ────────

// gitPath 缓存 git 可执行文件路径（绕过 os/exec lookPath 在 Termux/Android 上的 SIGSYS）
var gitPath = findGit()

func findGit() string {
	known := []string{
		"/data/data/com.termux/files/usr/bin/git", // Termux/Android
		"/usr/bin/git",                             // Linux
		"/usr/local/bin/git",                       // macOS Homebrew
	}
	for _, p := range known {
		if fi, err := os.Stat(p); err == nil && !fi.IsDir() {
			return p
		}
	}
	return "git" // fallback: 让系统自己找
}

func (gm *GitMemory) git(args ...string) (string, error) {
	cmd := exec.Command(gitPath, args...)
	cmd.Dir = gm.root
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	if err != nil {
		return strings.TrimSpace(stderr.String()),
			fmt.Errorf("git %s: %v", strings.Join(args, " "), err)
	}
	return stdout.String(), nil
}

// ──────── slugify ────────

var nonSlugChars = regexp.MustCompile(`[^a-z0-9-\p{L}]`)  // \p{L} 保留非 ASCII 字母（中文等）
var multiDash = regexp.MustCompile(`-+`)

func slugify(s string) string {
	s = strings.ToLower(s)
	s = strings.ReplaceAll(s, " ", "-")
	// 保留中文和其他 Unicode 字母，只去除标点和特殊字符
	s = nonSlugChars.ReplaceAllString(s, "")
	s = multiDash.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	if s == "" {
		s = "untitled"
	}
	return s
}

// ──────── 随机 Session ID ────────

func randomSessionID() string {
	b := make([]byte, 4)
	rand.Read(b)
	return "session-" + hex.EncodeToString(b)
}

// ──────── sanitize（安全过滤）───────

var apiKeyPattern = regexp.MustCompile(`sk-[a-zA-Z0-9]{20,}`)
var bearerPattern = regexp.MustCompile(`Bearer [a-zA-Z0-9._-]+`)
var passwordPattern = regexp.MustCompile(`(?i)(password|passwd|pwd)[=:]\s*\S+`)

func sanitize(content string) (string, error) {
	if len(content) > 8192 {
		content = content[:8192] + "\n... (truncated)"
	}

	content = apiKeyPattern.ReplaceAllString(content, "sk-[REDACTED]")
	content = bearerPattern.ReplaceAllString(content, "Bearer [REDACTED]")
	content = passwordPattern.ReplaceAllString(content, "${1}=[REDACTED]")

	return content, nil
}

// ──────── 角色验证 ────────

var validRoles = map[string]bool{
	"User":              true,
	"Agent (thought)":  true,
	"Agent (result)":   true,
	"Action":           true,
}

func isValidRole(role string) bool {
	if validRoles[role] {
		return true
	}
	// 允许 Action: step_N (node_id) 格式
	if strings.HasPrefix(role, "Action: ") {
		return true
	}
	return false
}

// ──────── 文件解析工具 ────────

func extractTitle(content string) string {
	lines := strings.SplitN(content, "\n", 2)
	if len(lines) > 0 {
		return strings.TrimPrefix(lines[0], "# ")
	}
	return "untitled"
}

func extractField(content, field string) string {
	lines := strings.Split(content, "\n")
	inField := false
	var result []string
	for _, line := range lines {
		if strings.HasPrefix(line, field) {
			inField = true
			continue
		}
		if inField {
			if strings.HasPrefix(line, "#") || strings.HasPrefix(line, "##") {
				break
			}
			result = append(result, line)
		}
	}
	return strings.TrimSpace(strings.Join(result, "\n"))
}

func countSectionHeaders(path string) int {
	f, err := os.Open(path)
	if err != nil {
		return 0
	}
	defer f.Close()

	count := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "## ") {
			count++
		}
	}
	return count
}

// ──────── Episode 摘要读取 ────────

func (gm *GitMemory) readEpisodeSummary(relPath string) (EpisodeSummary, error) {
	fullPath := filepath.Join(gm.root, relPath)
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return EpisodeSummary{}, err
	}

	content := string(data)
	title := extractTitle(content)

	// 提取 Success
	success := true
	if strings.Contains(content, "> Success: ❌") {
		success = false
	}

	// 提取 Learned
	learned := extractField(content, "## Learned")

	// 提取 Task
	task := extractField(content, "## Task")

	// 提取文件名中的日期
	date := ""
	base := filepath.Base(relPath)
	if len(base) >= 10 {
		date = base[:10]
	}

	// 读取强度
	strength := 1.0
	if s, ok := gm.strengths[relPath]; ok {
		strength = s.Strength
	} else {
		// 从文件头部读取
		re := regexp.MustCompile(`> Strength:\s*([\d.]+)`)
		m := re.FindStringSubmatch(content)
		if len(m) >= 2 {
			if v, err := strconv.ParseFloat(m[1], 64); err == nil {
				strength = v
			}
		}
	}

	return EpisodeSummary{
		File:     relPath,
		Title:    title,
		Date:     date,
		Task:     task,
		Success:  success,
		Learned:  learned,
		Strength: strength,
	}, nil
}

func (gm *GitMemory) readMemoryItem(relPath string) (MemoryItem, error) {
	fullPath := filepath.Join(gm.root, relPath)
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return MemoryItem{}, err
	}

	content := string(data)
	item := MemoryItem{
		Path:  relPath,
		Title: extractTitle(content),
	}

	// 类型
	if strings.Contains(relPath, "sessions/") {
		item.Type = "session"
	} else if strings.Contains(relPath, "episodes/") {
		item.Type = "episode"
	} else if strings.Contains(relPath, "knowledge/") {
		item.Type = "knowledge"
	} else {
		item.Type = "other"
	}

	item.Archived = strings.Contains(relPath, "archive/")

	// 提取元数据
	for _, line := range strings.Split(content, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "> Strength:") {
			v := strings.TrimSpace(strings.TrimPrefix(line, "> Strength:"))
			if f, err := strconv.ParseFloat(v, 64); err == nil {
				item.Strength = f
			}
		}
		if strings.HasPrefix(line, "> Tags:") {
			item.Tags = strings.TrimSpace(strings.TrimPrefix(line, "> Tags:"))
		}
		if strings.HasPrefix(line, "> Created:") || strings.HasPrefix(line, "> Date:") {
			item.Created = strings.TrimSpace(strings.SplitN(line, ":", 2)[1])
		}
	}

	// 前 100 字符作为摘要
	item.Snippet = content
	if len(item.Snippet) > 100 {
		item.Snippet = item.Snippet[:100] + "..."
	}
	// 跳过标题行
	lines := strings.SplitN(item.Snippet, "\n", 3)
	if len(lines) >= 2 {
		item.Snippet = strings.TrimSpace(lines[len(lines)-1])
	}
	if len(item.Snippet) > 100 {
		item.Snippet = item.Snippet[:100] + "..."
	}

	return item, nil
}

func (gm *GitMemory) mustGetAssociations(path string) []Link {
	links, _ := gm.GetAssociations(path)
	return links
}

// ──────── 标签搜索（基于 INDEX.md + 关键词） ────────

func (gm *GitMemory) searchByTag(tag string) []MemoryItem {
	var items []MemoryItem

	// 先尝试在 INDEX.md 中找
	indexPath := filepath.Join(gm.root, "INDEX.md")
	if data, err := os.ReadFile(indexPath); err == nil {
		content := string(data)

		// 找到匹配标签的段落
		inSection := false
		for _, line := range strings.Split(content, "\n") {
			if strings.Contains(line, "### "+tag) {
				inSection = true
				continue
			}
			if inSection {
				if strings.HasPrefix(line, "### ") {
					break
				}
				if strings.HasPrefix(line, "- ") {
					// 格式: "- relative/path/to/file.md (date, status)"
					fileRef := strings.TrimPrefix(line, "- ")
					parts := strings.Split(fileRef, " ")
					if len(parts) > 0 {
						refPath := strings.TrimSpace(parts[0])
						item, err := gm.readMemoryItem(refPath)
						if err == nil {
							items = append(items, item)
						}
					}
				}
			}
		}
	}

	// 也直接在文件名中搜索（目录名就是标签）
	for _, dir := range []string{"episodes", "knowledge"} {
		entries, err := os.ReadDir(filepath.Join(gm.root, dir))
		if err != nil {
			continue
		}
		for _, e := range entries {
			if strings.Contains(strings.ToLower(e.Name()), strings.ToLower(tag)) {
				item, err := gm.readMemoryItem(dir + "/" + e.Name())
				if err == nil {
					items = append(items, item)
				}
			}
		}
	}

	return items
}

// ──────── Session 长度检查 ────────

func (gm *GitMemory) checkSessionLength(sessionID, path string) {
	count := countSectionHeaders(path)
	if count > 50 {
		// 标记需要压缩（实际压缩需要 LLM，由 Agent 在 think 时触发）
		data, err := os.ReadFile(path)
		if err != nil {
			return
		}
		content := string(data)
		if strings.Contains(content, "> Compacted:") {
			return // 已压缩过
		}
		content = strings.Replace(content, "> Summarized: false",
			fmt.Sprintf("> Compacted: true\n> CompactedAt: %s\n> OriginalCount: %d\n> Summarized: true",
				time.Now().Format("2006-01-02 15:04:05"), count), 1)
		os.WriteFile(path, []byte(content), 0644)
	}
}

// ──────── 强度持久化 ────────

func (gm *GitMemory) loadStrengths() {
	path := filepath.Join(gm.root, ".strengths.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	var strengths []memStrength
	if err := json.Unmarshal(data, &strengths); err != nil {
		return
	}
	for i := range strengths {
		gm.strengths[strengths[i].Path] = &strengths[i]
	}
}

func (gm *GitMemory) saveStrengths() {
	all := make([]memStrength, 0, len(gm.strengths))
	for _, s := range gm.strengths {
		all = append(all, *s)
	}
	data, err := json.Marshal(all)
	if err != nil {
		log.Printf("[Memory] ⚠️ save strengths failed: %v", err)
		return
	}
	path := filepath.Join(gm.root, ".strengths.json")
	os.WriteFile(path, data, 0644)

	// 不 commit（让 AutoCommit 统一做）
}

// ====================================================================== //
//  错误定义
// ====================================================================== //

var (
	ErrMemoryNotInit = fmt.Errorf("memory not initialized")
	ErrSessionEmpty  = fmt.Errorf("session ID cannot be empty")
	ErrInvalidRole   = fmt.Errorf("invalid role")
)
