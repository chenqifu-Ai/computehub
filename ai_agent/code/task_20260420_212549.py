import psutil
import time
import threading
import matplotlib.pyplot as plt
from collections import deque
import sys

# 配置参数
MONITOR_INTERVAL = 1  # 监控间隔时间（秒）
MAX_DATA_POINTS = 60  # 最大数据点数，用于限制图表显示的数据量

# 存储内存使用情况的历史数据
memory_data = deque(maxlen=MAX_DATA_POINTS)
times = deque(maxlen=MAX_DATA_POINTS)

def collect_memory_usage():
    """收集系统内存使用信息"""
    while True:
        try:
            mem_info = psutil.virtual_memory()
            memory_data.append(mem_info.percent)
            times.append(time.strftime("%H:%M:%S"))
            time.sleep(MONITOR_INTERVAL)
        except Exception as e:
            print(f"Error collecting memory usage: {e}", file=sys.stderr)

def plot_memory_usage():
    """绘制内存使用情况图"""
    plt.figure(figsize=(10,5))
    plt.plot(times, memory_data, label="Memory Usage (%)")
    plt.title("System Memory Usage Over Time")
    plt.xlabel("Time")
    plt.ylabel("Memory Usage %")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    # 创建并启动监控线程
    monitor_thread = threading.Thread(target=collect_memory_usage, daemon=True)
    monitor_thread.start()

    print("Starting system memory monitoring. Press Ctrl+C to stop and view the report.")
    
    try:
        # 主循环，保持程序运行直到用户中断
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping memory monitoring. Generating report...")
        if len(memory_data) > 0:
            plot_memory_usage()
        else:
            print("No data collected. Please run for a longer period.")

if __name__ == "__main__":
    main()