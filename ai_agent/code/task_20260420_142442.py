import os
import psutil
import threading
import time
import matplotlib.pyplot as plt

# 定义全局变量存储内存数据
memory_data = []
lock = threading.Lock()

# 内存信息收集函数
def collect_memory_info(interval, stop_event):
    while not stop_event.is_set():
        try:
            with lock:
                # 获取内存使用率
                mem_info = psutil.virtual_memory().percent
                memory_data.append((time.time(), mem_info))
        except Exception as e:
            print(f"Error occurred during data collection: {e}")
        time.sleep(interval)

# 可视化函数
def plot_memory_usage():
    times, usages = zip(*memory_data)
    start_time = times[0]
    relative_times = [t - start_time for t in times]

    plt.figure(figsize=(10, 5))
    plt.plot(relative_times, usages, label='Memory Usage')
    plt.xlabel('Time (s)')
    plt.ylabel('Usage (%)')
    plt.title('System Memory Usage Over Time')
    plt.legend()
    plt.grid(True)
    plt.show()

# 主函数，用于启动监控线程并控制其运行时间
def main():
    interval = 1  # 数据采集间隔（秒）
    duration = 60  # 监控持续时间（秒）

    # 创建停止事件，用于安全地停止线程
    stop_event = threading.Event()

    # 启动内存监控线程
    monitor_thread = threading.Thread(target=collect_memory_info, args=(interval, stop_event))
    monitor_thread.start()

    try:
        # 模拟一段时间后停止监控
        time.sleep(duration)
    except KeyboardInterrupt:
        print("Monitoring interrupted by user.")
    finally:
        # 设置停止事件，告知线程可以结束了
        stop_event.set()
        # 等待线程结束
        monitor_thread.join()

    # 绘制内存使用情况图
    if memory_data:
        plot_memory_usage()
    else:
        print("No memory data collected. Please check the monitoring setup.")

if __name__ == '__main__':
    main()