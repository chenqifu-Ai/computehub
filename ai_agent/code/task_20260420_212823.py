import psutil
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 存储内存使用情况的数据
memory_data = []

# 定义一个类来处理数据采集
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间（秒）
        self.running = True  # 控制线程运行状态

    def start_monitoring(self):
        while self.running:
            try:
                # 获取当前系统内存使用信息
                mem_info = psutil.virtual_memory()
                used_memory = mem_info.percent  # 百分比形式的已用内存
                timestamp = datetime.now()  # 当前时间戳
                memory_data.append((timestamp, used_memory))
                print(f"Memory Usage: {used_memory}% at {timestamp}")
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error during monitoring: {e}")
                break  # 如果遇到错误则停止监控

    def stop_monitoring(self):
        self.running = False

# 绘制图表函数
def plot_memory_usage(data):
    timestamps, usages = zip(*data)
    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(timestamps, usages, marker='o')
    
    # 设置x轴格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    fig.autofmt_xdate()

    plt.title('System Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.grid(True)
    plt.show()

# 异常处理装饰器
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"An error occurred in {func.__name__}: {str(e)}")
    return wrapper

@handle_exceptions
def main():
    monitor = MemoryMonitor(interval=2)  # 每两秒检查一次
    monitor_thread = threading.Thread(target=monitor.start_monitoring)
    
    try:
        monitor_thread.start()
        print("Monitoring started. Press Ctrl+C to stop.")
        
        # 让主线程等待一段时间后停止监控并绘制图表
        time.sleep(30)  # 假设我们希望在30秒后自动停止
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    finally:
        monitor.stop_monitoring()
        monitor_thread.join()
        if memory_data:
            plot_memory_usage(memory_data)

if __name__ == "__main__":
    main()