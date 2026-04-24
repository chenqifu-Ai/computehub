import psutil
import time
import threading
import matplotlib.pyplot as plt
from datetime import datetime
import queue

# 配置
SAMPLE_INTERVAL = 5  # 采样间隔（秒）
MONITOR_DURATION = 60  # 监控时长（秒）
MAX_QUEUE_SIZE = MONITOR_DURATION // SAMPLE_INTERVAL  # 最大队列大小

# 数据队列
data_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)

def collect_memory_usage():
    """收集内存使用情况"""
    while True:
        try:
            memory_info = psutil.virtual_memory()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_queue.put((timestamp, memory_info.percent))
            time.sleep(SAMPLE_INTERVAL)
        except Exception as e:
            print(f"Error during memory collection: {e}")
            break

def plot_memory_usage(data):
    """绘制内存使用图表"""
    timestamps, percents = zip(*data)
    plt.figure(figsize=(14, 7))
    plt.plot(timestamps, percents, marker='o')
    plt.title('Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    # 启动数据收集线程
    collector_thread = threading.Thread(target=collect_memory_usage, daemon=True)
    collector_thread.start()

    # 主循环，等待监控结束或手动停止
    start_time = time.time()
    while (time.time() - start_time) < MONITOR_DURATION:
        try:
            if not collector_thread.is_alive():
                print("Collector thread has stopped unexpectedly.")
                break
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            break
    
    # 收集所有数据准备绘图
    all_data = list(data_queue.queue)
    
    # 结束后绘制图表
    if all_data:
        plot_memory_usage(all_data)
    else:
        print("No data collected.")

if __name__ == "__main__":
    main()