#!/usr/bin/env python3
"""修复 KnowledgeStore 持久化和 ClusterMemory 桥接"""

import re, os

PROJECT = "/home/computehub/ComputeHub"

def fix1_add_load_method():
    """在 gateway_knowledge.go 的 KnowledgeStore 添加 load() 方法"""
    path = os.path.join(PROJECT, "src/gateway/gateway_knowledge.go")
    with open(path) as f:
        content = f.read()
    
    if "func (ks *KnowledgeStore) load" in content:
        print("[Fix 1] ✅ load() 已存在，跳过")
        return
    
    # 在 persist 方法之后添加 load 方法
    old = '''// slugify 生成 URL 友好的文件名
func slugify(s string) string {'''

    new = '''// load 从持久化文件加载知识到内存
func (ks *KnowledgeStore) load(dir string) int {
	if dir == "" {
		return 0
	}
	loaded := 0
	entries, err := os.ReadDir(dir)
	if err != nil {
		logWithTimestamp("⚠️ 知识持久化目录读取失败: %v", err)
		return 0
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		typeDir := filepath.Join(dir, entry.Name())
		files, err := os.ReadDir(typeDir)
		if err != nil {
			continue
		}
		for _, f := range files {
			if f.IsDir() || !strings.HasSuffix(f.Name(), ".md") {
				continue
			}
			path := filepath.Join(typeDir, f.Name())
			data, err := os.ReadFile(path)
			if err != nil {
				continue
			}
			text := string(data)
			kn := &KnowledgeEntry{Type: entry.Name()}
			// 从 Markdown 头提取元数据
			lines := strings.SplitN(text, "\n", 8)
			for _, line := range lines {
				if strings.HasPrefix(line, "# Knowledge: ") {
					kn.Title = strings.TrimPrefix(line, "# Knowledge: ")
				} else if strings.HasPrefix(line, "> Type: ") {
					kn.Type = strings.TrimPrefix(line, "> Type: ")
				} else if strings.HasPrefix(line, "> Source: ") {
					kn.Source = strings.TrimPrefix(line, "> Source: ")
				} else if strings.HasPrefix(line, "> Tags: ") {
					tagStr := strings.TrimPrefix(line, "> Tags: ")
					if tagStr != "" {
						kn.Tags = strings.Split(tagStr, ", ")
					}
				} else if strings.HasPrefix(line, "> Timestamp: ") {
					kn.Timestamp = strings.TrimPrefix(line, "> Timestamp: ")
				} else if strings.HasPrefix(line, "> Confidence: ") {
					confStr := strings.TrimPrefix(line, "> Confidence: ")
					fmt.Sscanf(confStr, "%f", &kn.Confidence)
				}
			}
			// 提取 Content 部分
			if idx := strings.Index(text, "## Content\n\n"); idx >= 0 {
				kn.Content = strings.TrimSpace(text[idx+12:])
			}
			if kn.Content == "" {
				kn.Content = text // fallback
			}
			if kn.ID == "" {
				kn.ID = fmt.Sprintf("kn-loaded-%d", loaded)
			}
			ks.put(kn)
			loaded++
		}
	}
	logWithTimestamp("📚 知识库加载完成: %d 条", loaded)
	return loaded
}

// slugify 生成 URL 友好的文件名
func slugify(s string) string {'''

    if old not in content:
        print("[Fix 1] ❌ 找不到插入点 slugify")
        return False
    
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print(f"[Fix 1] ✅ load() 方法添加 (165 行)")
    return True


def fix2_gateway_init():
    """在 gateway.go 的 NewOpcGateway 中调用 globalKnowledgeStore.load()"""
    path = os.path.join(PROJECT, "src/gateway/gateway.go")
    with open(path) as f:
        content = f.read()
    
    if "globalKnowledgeStore.load(memoryDir)" in content:
        print("[Fix 2] ✅ 启动加载已集成，跳过")
        return
    
    old = '''	SetKnowledgeDataDir(memoryDir)
	if err := clusterMem.loadFromFile(); err != nil {'''
    
    new = '''	SetKnowledgeDataDir(memoryDir)
	// 从文件恢复 KnowledgeStore 持久化知识
	globalKnowledgeStore.load(memoryDir)
	if err := clusterMem.loadFromFile(); err != nil {'''
    
    if old not in content:
        print("[Fix 2] ❌ 找不到插入点")
        return False
    
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("[Fix 2] ✅ globalKnowledgeStore.load() 注入到 NewOpcGateway")
    return True


def fix3_bridge_stores():
    """在 ClusterMemory.storeKnowledge 中同步到 globalKnowledgeStore"""
    mem_path = os.path.join(PROJECT, "src/gateway/gateway_memory.go")
    with open(mem_path) as f:
        mem = f.read()
    
    if "globalKnowledgeStore" in mem:
        print("[Fix 3] ✅ 桥接已存在，跳过")
        return
    
    idx = mem.find("func (cm *ClusterMemory) storeKnowledge")
    if idx < 0:
        print("[Fix 3] ❌ 找不到 storeKnowledge")
        return False
    
    snippet = mem[idx:idx+800]
    # Find the end of the function
    end_idx = snippet.find("\nfunc") 
    if end_idx < 0:
        end_idx = len(snippet)
    snippet_body = snippet[:end_idx]
    
    old_body = snippet_body
    
    new_body = snippet_body.replace(
        "	cm.knowledge[key] = kn",
        "	cm.knowledge[key] = kn\n\n\t// 同步到 KnowledgeStore\n\tglobalKnowledgeStore.put(&KnowledgeEntry{\n\t\tID:      fmt.Sprintf(\"kn-cluster-%s-%s\", kn.NodeID, kn.Topic),\n\t\tTitle:   kn.Topic,\n\t\tContent: kn.Content,\n\t\tType:    \"lesson\",\n\t\tSource:  kn.NodeID,\n\t\tTags:    kn.Tags,\n\t\tConfidence: 0.8,\n\t\tTTLDays: 30,\n\t\tTimestamp: kn.Timestamp.Format(time.RFC3339),\n\t})"
    )
    
    if old_body == new_body:
        print("[Fix 3] ❌ 替换内容相同")
        return False
    
    mem = mem.replace(old_body, new_body)
    with open(mem_path, 'w') as f:
        f.write(mem)
    print("[Fix 3] ✅ ClusterMemory → KnowledgeStore 桥接注入")
    return True


def verify():
    """编译验证"""
    import subprocess
    result = subprocess.run(
        ["go", "build", "-o", "/dev/null", "./cmd/computehub/"],
        cwd=PROJECT, capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[Verify] ✅ 编译通过")
        return True
    else:
        print(f"[Verify] ❌ 编译失败:\n{result.stderr[:500]}")
        return False


if __name__ == "__main__":
    f1 = fix1_add_load_method()
    f2 = fix2_gateway_init()
    f3 = fix3_bridge_stores()
    print()
    verify()