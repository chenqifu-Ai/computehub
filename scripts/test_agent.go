// Quick test: LLM API + shell exec
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"strings"
	"time"
)

func main() {
	start := time.Now()

	// Test 1: LLM API
	fmt.Println("=== 1. LLM API 连通性 ===")
	payload := map[string]interface{}{
		"model":     "qwen3.6-35b",
		"max_tokens": 50,
		"messages": []map[string]string{
			{"role": "user", "content": "Say hello in 1 word."},
		},
	}
	body, _ := json.Marshal(payload)
	resp, err := http.Post("https://ai.zhangtuokeji.top:9090/v1/chat/completions",
		"application/json", bytes.NewReader(body))
	if err != nil {
		fmt.Printf("  FAIL: %v\n", err)
	} else {
		defer resp.Body.Close()
		data, _ := io.ReadAll(resp.Body)
		fmt.Printf("  Status: %d, Body: %s\n", resp.StatusCode, strings.TrimSpace(string(data)))
	}

	// Test 2: Shell exec
	fmt.Println("\n=== 2. Shell exec (exec_local 功能) ===")
	cmd := exec.Command("bash", "-c", "uptime && free -h | grep Mem && df -h / | grep /")
	out, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("  FAIL: %v\n", err)
	}
	fmt.Printf("  Result:\n%s\n", out)

	// Test 3: /think endpoint
	fmt.Println("=== 3. /api/v1/worker/think ===")
	type ThinkReq struct {
		Task string `json:"task"`
	}
	type ThinkResp struct {
		Thought string `json:"thought"`
		Plan    []map[string]interface{} `json:"plan"`
		Result  string `json:"result"`
		Error   string `json:"error,omitempty"`
	}

	thinkPayload, _ := json.Marshal(ThinkReq{
		Task: "请对本服务器做一次简单诊断：执行 uptime 查看负载，返回结果即可。",
	})
	thinkResp, err := http.Post("http://localhost:8383/api/v1/worker/think",
		"application/json", bytes.NewReader(thinkPayload))
	if err != nil {
		fmt.Printf("  FAIL: %v\n", err)
	} else {
		defer thinkResp.Body.Close()
		var tr ThinkResp
		json.NewDecoder(thinkResp.Body).Decode(&tr)
		fmt.Printf("  Status: %d\n", thinkResp.StatusCode)
		fmt.Printf("  Thought: %s\n", tr.Thought)
		fmt.Printf("  Plan: %v\n", tr.Plan)
		fmt.Printf("  Result: %s\n", tr.Result)
		fmt.Printf("  Error: %s\n", tr.Error)
	}

	fmt.Printf("\n总耗时: %v\n", time.Since(start))
}
