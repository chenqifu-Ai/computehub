import threading
import time
import psutil
import matplotlib.pyplot as plt
from datetime import datetime

# 全局变量，用于存储内存使用情况
memory_usage_data = []
lock = threading.Lock()

def get_memory_info():
    """获取系统当前的内存使用信息"""
    mem_info = psutil.virtual_memory()
    return mem_info.percent  # 返回内存使用百分比

def monitor_memory(interval=1):
    """
    定期监控内存使用情况，并将数据添加到全局列表中。
    :param interval: 监控间隔时间（秒）
    """
    global memory_usage_data
    while True:
        try:
            with lock:
                usage = get_memory_info()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"Memory Usage at {timestamp}: {usage}%")
                memory_usage_data.append((timestamp, usage))
        except Exception as e:
            print(f"Error occurred during monitoring: {e}")
        finally:
            time.sleep(interval)

def plot_memory_usage(data):
    """绘制内存使用情况图"""
    timestamps, usages = zip(*data)
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, usages, marker='o', linestyle='-')
    plt.title('System Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    # 启动一个线程来持续监控内存
    thread_monitor = threading.Thread(target=monitor_memory, args=(5,), daemon=True)
    thread_monitor.start()

    # 主线程等待一段时间后停止监控并生成图表
    try:
        print("Starting to monitor system memory. Press Ctrl+C to stop and generate the report.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping memory monitoring...")
    
    # 确保所有数据都被收集完毕
    thread_monitor.join()

    if memory_usage_data:
        print("Generating memory usage chart...")
        plot_memory_usage(memory_usage_data)
    else:
        print("No data collected for plotting.")

if __name__ == "__main__":
    main()