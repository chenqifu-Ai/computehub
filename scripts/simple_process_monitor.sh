#!/bin/bash
# 简单进程监控脚本

echo "🔍 异常进程监控系统"
echo "📊 检查时间: $(date)"
echo "-"*50

# 定义已知正常进程
known_processes=(
    "systemd" "init" "kthreadd" "ksoftirqd" "rcu_sched"
    "sshd" "bash" "python" "node" "java" "nginx" "apache"
    "mysql" "redis" "docker" "containerd" "openclaw"
    "adb" "curl" "wget" "ssh" "scp" "top" "htop" "ps"
    "grep" "awk" "sed" "find" "cat" "ls" "proot"
)

# 定义可疑模式
suspicious_patterns=(
    "miner" "backdoor" "reverse_shell" "keylogger"
    "crypto" "ransom" "botnet" "trojan" "worm"
    "rootkit" "spyware" "adware" "malware"
    "hidden" "stealth" "obfuscated" "packed"
)

echo "📈 当前运行进程检查..."
suspicious_count=0

# 检查所有进程
while read -r pid user cmd; do
    # 跳过表头和空行
    [[ "$pid" == "PID" ]] && continue
    [[ -z "$pid" ]] && continue
    
    # 提取进程名
    process_name=$(echo "$cmd" | awk '{print $1}' | xargs basename 2>/dev/null)
    
    # 检查是否已知进程
    is_known=0
    for known in "${known_processes[@]}"; do
        if [[ "$process_name" == *"$known"* ]] || [[ "$cmd" == *"$known"* ]]; then
            is_known=1
            break
        fi
    done
    
    # 检查可疑模式
    is_suspicious=0
    alerts=()
    for pattern in "${suspicious_patterns[@]}"; do
        if [[ "$process_name" == *"$pattern"* ]] || [[ "$cmd" == *"$pattern"* ]]; then
            is_suspicious=1
            alerts+=("包含$pattern")
        fi
    done
    
    # 检查异常用户
    if [[ "$user" != "root" ]] && [[ "$user" != "u0_a355" ]] && [[ "$user" != "u0_a207" ]] && [[ "$user" != "u0_a46" ]] && [[ ! "$user" =~ ^u0_a ]]; then
        is_suspicious=1
        alerts+=("异常用户:$user")
    fi
    
    # 如果是未知进程也标记
    if [[ $is_known -eq 0 ]] && [[ -n "$process_name" ]]; then
        is_suspicious=1
        alerts+=("未知进程")
    fi
    
    # 输出可疑进程
    if [[ $is_suspicious -eq 1 ]]; then
        suspicious_count=$((suspicious_count + 1))
        echo ""
        echo "⚠️  可疑进程 detected!"
        echo "   PID: $pid"
        echo "   用户: $user"
        echo "   进程: $process_name"
        echo "   警报: ${alerts[*]}"
        echo "   命令行: ${cmd:0:100}..."
    fi

done < <(ps aux | tail -n +2)

echo ""
echo "-"*50
if [[ $suspicious_count -eq 0 ]]; then
    echo "✅ 系统干净，未发现可疑进程"
else
    echo "🔴 发现 $suspicious_count 个可疑进程!"
fi

echo ""
echo "📊 总进程数: $(ps aux | wc -l)"
echo "🕐 检查完成: $(date)"