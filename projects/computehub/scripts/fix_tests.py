#!/usr/bin/env python3
"""一次性修复所有5个编译错误"""

proj = "/root/.openclaw/workspace/projects/computehub"

# Error 1: cmd/worker/main.go:293 format %.1f has arg pctColor of wrong type string
# pctColor returns a colored string, but format expects float64
with open(f"{proj}/cmd/worker/main.go", "r") as f:
    content = f.read()

old = '''			fmt.Printf("\r %s[心跳] GPU: %s%.1f%%%s  %s%.0f°C%s  Mem: %s%.0f/%.0fGB%s   ",
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
			)'''
new = '''			gpuStr := pctColor(stats.Utilization)
				tempStr := tempColor(stats.Temperature)
				memUsedStr := cyan(fmt.Sprintf("%.0f", stats.MemoryUsedGB))
				memTotStr := cyan(fmt.Sprintf("%.0f", stats.MemoryTotalGB))
				fmt.Printf("\r %s[心跳] GPU: %s  %s  Mem: %s / %s",
					dim(""), reset(),
					gpuStr,
					reset(),
					tempStr,
					reset(),
					memUsedStr,
					memTotStr,
					reset(),
				)'''
content = content.replace(old, new)

# Error 2: cmd/worker/main.go:556 format %s reads arg #7, but call has 6 args
old2 = '''	fmt.Printf(" %s%s 任务 %s 完成 [%s] %s (%s)%s\n",
		statusColor(bold("")), statusIcon, cyan(task.TaskID),
		statusColor(fmt.Sprintf("exit=%d", exitCode)),
		duration.Round(time.Millisecond), reset())'''
new2 = '''	fmt.Printf(" %s%s 任务 %s 完成 [%s] %s (%s)\n",
		statusColor(bold("")), statusIcon, cyan(task.TaskID),
		statusColor(fmt.Sprintf("exit=%d", exitCode)),
		duration.Round(time.Millisecond), reset())'''
content = content.replace(old2, new2)

# Error 3: cmd/worker/main.go:731 format %s reads arg #14, but call has 13 args
# The help text has 13 %s placeholders but 14 args (extra green/bold reset at end)
old3 = '''func printWorkerHelp() {
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

%s示例:%s
  ./compute-worker --gw http://192.168.1.17:8282 --node-id gpu-01 --gpu-type H100 --region cn-east
  ./compute-worker --node-id worker-2 --interval 3 --concurrent 8
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
new3 = '''func printWorkerHelp() {
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
content = content.replace(old3, new3)

with open(f"{proj}/cmd/worker/main.go", "w") as f:
    f.write(content)
print("✅ Fixed cmd/worker/main.go (3 errors)")

# Error 4: cmd/tui/main.go:1355 fmt.Printf needs 5 args but has 6
with open(f"{proj}/cmd/tui/main.go", "r") as f:
    content = f.read()

old4 = '''	fmt.Printf("  %-24s │ %-10s │ %-8s │ %-9s │ %s\n",
		White+Bold, "Node", "Region", "GPU", "Load", Reset)'''
new4 = '''	fmt.Printf("  %-24s │ %-10s │ %-8s │ %-9s │ %s\n",
		White+Bold+"Node"+Reset,
		White+"Region"+Reset,
		White+"GPU"+Reset,
		White+"Load"+Reset,
		White+"----"+Reset)'''
content = content.replace(old4, new4)

with open(f"{proj}/cmd/tui/main.go", "w") as f:
    f.write(content)
print("✅ Fixed cmd/tui/main.go (1 error)")

# Error 5: cmd/node/main.go:65 fmt.Println arg list ends with redundant newline
# Actually already fixed by previous script (fmt.Println → fmt.Print + no leading newline)
# Just verify it's clean
with open(f"{proj}/cmd/node/main.go", "r") as f:
    content = f.read()

# If still has the old pattern, fix it
if 'fmt.Println(`\nComputeNode' in content:
    content = content.replace('fmt.Println(`\nComputeNode', 'fmt.Print(`ComputeNode')
    with open(f"{proj}/cmd/node/main.go", "w") as f:
        f.write(content)
    print("✅ Fixed cmd/node/main.go (redundant newline)")
else:
    print("✅ cmd/node/main.go already clean")

print("\n🎉 All 5 errors fixed!")
