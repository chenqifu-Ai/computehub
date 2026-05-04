import psutil
import time
import threading
from queue import Queue
import matplotlib.pyplot as plt
import datetime

# 定义一个队列来存储内存使用数据
data_queue = Queue()

def get_memory_info():
    """获取系统内存信息"""
    mem = psutil.virtual_memory()
    return mem.percent  # 返回内存使用百分比

def worker(interval, stop_event):
    """工作线程，定期收集内存使用情况"""
    while not stop_event.is_set():
        try:
            memory_usage = get_memory_info()
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_queue.put((current_time, memory_usage))
            print(f"Memory usage: {memory_usage}% at {current_time}")
        except Exception as e:
            print(f"Error in worker: {e}")
        finally:
            time.sleep(interval)

def plot_memory_usage(data):
    """绘制内存使用情况图"""
    times, usages = zip(*data)
    plt.figure(figsize=(10,5))
    plt.plot(times, usages, marker='o')
    plt.title('System Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    monitoring_interval = 2  # 监控间隔时间（秒）
    monitoring_duration = 60  # 总监控时长（秒）

    stop_event = threading.Event()
    thread = threading.Thread(target=worker, args=(monitoring_interval, stop_event))

    try:
        print("Starting memory monitoring...")
        thread.start()
        time.sleep(monitoring_duration)  # 主线程等待一段时间后停止监测
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user.")
    finally:
        stop_event.set()  # 设置事件以停止子线程
        thread.join()  # 等待子线程完成
        print("Memory monitoring stopped.")

    # 从队列中收集所有数据点
    all_data = []
    while not data_queue.empty():
        all_data.append(data_queue.get())

    if all_data:
        plot_memory_usage(all_data)
    else:
        print("No data collected for plotting.")

if __name__ == "__main__":
    main()