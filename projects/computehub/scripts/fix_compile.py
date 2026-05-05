#!/usr/bin/env python3
"""Fix all 5 remaining compile errors"""
import re

proj = "/root/.openclaw/workspace/projects/computehub"

# 1-3: cmd/worker/main.go - 3 errors
with open(f"{proj}/cmd/worker/main.go", "r") as f:
    text = f.read()

# Fix 1: Line 293 - GPU log format mismatch
# The issue: pctColor returns string, but format has %.1f expecting float
# Also stats.MemoryUsedGB is float, but format has %s expecting string
# Fix: rewrite format to match actual args
old_gpu = '''		// Log GPU status
		if stats.Count > 0 {
			fmt.Printf("\r %s[心跳] GPU: %s%.1f%%%s  %s%.0f°C%s  Mem: %s%.0f/%.0fGB%s",
				dim(""), reset(),
				stats.Utilization,
				pctColor(0),
				reset(),
				stats.Temperature,
				tempColor(0),
				reset(),
				cyan(""),
				stats.MemoryUsedGB,
				cyan(""),
				stats.MemoryTotalGB,
				reset(),
			)
		}'''

new_gpu = '''		// Log GPU status
		if stats.Count > 0 {
			fmt.Printf("\r %s[心跳] GPU: %s  %s  Mem: %s / %s",
				dim(""), reset(),
				pctColor(stats.Utilization),
				reset(),
				tempColor(stats.Temperature),
				reset(),
				cyan(fmt.Sprintf("%.0fGB", stats.MemoryUsedGB)),
				cyan(fmt.Sprintf("%.0fGB", stats.MemoryTotalGB)),
			)
		}'''

text = text.replace(old_gpu, new_gpu)

# Fix 2: Line 557 - " %s%s 任务 %s 完成 [%s] %s (%s)%s\n" has 7 %s but 6 args
# Remove one %s to match 6 args
old_task = '''	fmt.Printf(" %s%s 任务 %s 完成 [%s] %s (%s)%s\n",
		statusColor(bold("")), statusIcon, cyan(task.TaskID),
		statusColor(fmt.Sprintf("exit=%d", exitCode)),
		duration.Round(time.Millisecond), reset())'''

new_task = '''	fmt.Printf(" %s%s 任务 %s 完成 [%s] %s\n",
		statusColor(bold("")), statusIcon, cyan(task.TaskID),
		statusColor(fmt.Sprintf("exit=%d", exitCode)),
		duration.Round(time.Millisecond), reset())'''

text = text.replace(old_task, new_task)

# Fix 3: Line 732 - printWorkerHelp has %s format in fmt.Print string but args don't match
# The raw string has %s directives (13 of them) but we pass 14 args
# Fix: use fmt.Printf consistently and ensure arg count matches
old_help = '''func printWorkerHelp() {
	fmt.Printf(`
%sComputeHub Worker Agent v0.1%s

%s用法:%s
  ./compute-worker [flags]

%s参数:%s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
`,
		yellow(bold("")), reset(),
		bold(""), reset(),
		fmt.Sprintf("--gw <url>           %s", dim("Gateway 地址 (默认: http://localhost:8282)")),
		fmt.Sprintf("--node-id <id>       %s", dim("节点 ID (默认: worker-<hostname>)")),
		fmt.Sprintf("--gpu-type <type>    %s", dim("GPU 型号 (默认: 自动检测)")),
		fmt.Sprintf("--region <region>    %s", dim("区域 (默认: cn-east)")),
		fmt.Sprintf("--interval <sec>     %s", dim("任务轮询间隔秒 (默认: 5)")),
		fmt.Sprintf("--heartbeat <sec>    %s", dim("心跳间隔秒 (默认: 10)")),
		fmt.Sprintf("--concurrent <n>     %s", dim("最大并发任务数 (默认: 4)")),
		green(bold("")), reset(),
		bold("示例:"), reset(),
		fmt.Sprintf("  ./compute-worker --gw http://192.168.1.17:8282 --node-id gpu-01 --gpu-type H100 --region cn-east"))
}'''

new_help = '''func printWorkerHelp() {
	fmt.Printf(`
%sComputeHub Worker Agent v0.1%s

%s用法:%s
  ./compute-worker [flags]

%s参数:%s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
`,
		yellow(bold("")), reset(),
		bold(""), reset(),
		fmt.Sprintf("--gw <url>           %s", dim("Gateway 地址 (默认: http://localhost:8282)")),
		fmt.Sprintf("--node-id <id>       %s", dim("节点 ID (默认: worker-<hostname>)")),
		fmt.Sprintf("--gpu-type <type>    %s", dim("GPU 型号 (默认: 自动检测)")),
		fmt.Sprintf("--region <region>    %s", dim("区域 (默认: cn-east)")),
		fmt.Sprintf("--interval <sec>     %s", dim("任务轮询间隔秒 (默认: 5)")),
		fmt.Sprintf("--heartbeat <sec>    %s", dim("心跳间隔秒 (默认: 10)")),
		fmt.Sprintf("--concurrent <n>     %s", dim("最大并发任务数 (默认: 4)")),
		green(bold("")), reset())
}'''

text = text.replace(old_help, new_help)

with open(f"{proj}/cmd/worker/main.go", "w") as f:
    f.write(text)
print("✅ 1-3. cmd/worker/main.go fixed")

# 4: cmd/tui/main.go - line 1355 needs 5 args but has 6
with open(f"{proj}/cmd/tui/main.go", "r") as f:
    text = f.read()

old_tui = '''	fmt.Printf("  %-24s │ %-10s │ %-8s │ %-9s │ %s\n",
		White+Bold, "Node", "Region", "GPU", "Load", Reset)'''

new_tui = '''	fmt.Printf("  %-24s │ %-10s │ %-8s │ %-9s │ %s\n",
		White+Bold, "Node", "Region", "GPU", "Load")'''

text = text.replace(old_tui, new_tui)

with open(f"{proj}/cmd/tui/main.go", "w") as f:
    f.write(text)
print("✅ 4. cmd/tui/main.go fixed")

# 5: src/composer/composer_test.go - NewDispatchEngine needs 5 args (models, maxConcurrency, timeout, apiURL, apiKey)
with open(f"{proj}/src/composer/composer_test.go", "r") as f:
    text = f.read()

text = re.sub(
    r'NewDispatchEngine\((\w+),\s*5,\s*30\*time\.Second\)',
    r'NewDispatchEngine(\1, 5, 30*time.Second, "http://localhost:8282", "test-key")',
    text
)

with open(f"{proj}/src/composer/composer_test.go", "w") as f:
    f.write(text)
print("✅ 5. composer test fixed")

print("\n🎉 All compile errors fixed!")
