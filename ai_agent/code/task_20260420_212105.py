import psutil
import matplotlib.pyplot as plt
from threading import Thread, Event
import time
import sys

# 定义一个类来处理内存监控
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间
        self.data = []  # 存储内存使用数据
        self.stop_event = Event()  # 用于停止线程的事件

    def start_monitoring(self):
        """启动监控"""
        thread = Thread(target=self._monitor_memory)
        thread.start()
        return thread

    def _monitor_memory(self):
        """实际执行监控的方法"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                used = mem_info.used / (1024.0 ** 3)  # 转换为GB
                self.data.append(used)
                print(f"Memory Usage: {used:.2f} GB")
            except Exception as e:
                print(f"Error during monitoring: {e}", file=sys.stderr)
            finally:
                time.sleep(self.interval)

    def stop_monitoring(self):
        """停止监控"""
        self.stop_event.set()

    def plot_data(self):
        """绘制内存使用情况图表"""
        if not self.data:
            print("No data to plot.")
            return
        plt.figure(figsize=(10, 5))
        plt.plot(self.data, label='Memory Usage (GB)')
        plt.title('System Memory Usage Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Memory Used (GB)')
        plt.legend()
        plt.grid(True)
        plt.show()

def main():
    monitor = MemoryMonitor(interval=2)  # 每两秒采集一次
    print("Starting memory monitoring. Press Ctrl+C to stop and view the report.")
    
    try:
        monitor_thread = monitor.start_monitoring()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop_monitoring()
        monitor_thread.join()
        monitor.plot_data()

if __name__ == "__main__":
    main()