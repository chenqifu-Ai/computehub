import psutil
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 定义一个类来处理内存监控
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔（秒）
        self.data = []  # 存储监控数据
        self.lock = threading.Lock()  # 线程锁
        self.stop_event = threading.Event()  # 停止标志

    def start_monitoring(self):
        """启动内存监控线程"""
        self.thread = threading.Thread(target=self._monitor_memory)
        self.thread.start()

    def _monitor_memory(self):
        """实际执行的内存监控函数"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                with self.lock:
                    self.data.append((datetime.now(), mem_info.percent))
            except Exception as e:
                print(f"Error occurred: {e}")
            finally:
                time.sleep(self.interval)

    def stop_monitoring(self):
        """停止内存监控"""
        self.stop_event.set()
        self.thread.join()

    def plot_data(self):
        """绘制内存使用情况图表"""
        dates, values = zip(*self.data) if self.data else ([], [])
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(dates, values, label='Memory Usage %')
        
        # 设置日期格式
        date_format = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
        ax.xaxis.set_major_formatter(date_format)
        fig.autofmt_xdate()

        ax.set_xlabel('Time')
        ax.set_ylabel('Memory Usage (%)')
        ax.legend()
        plt.title('System Memory Usage Over Time')
        plt.show()

def main():
    monitor = MemoryMonitor(interval=2)  # 每两秒收集一次数据
    try:
        monitor.start_monitoring()
        print("Monitoring started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop_monitoring()
        monitor.plot_data()

if __name__ == "__main__":
    main()

# 测试用例示例
def test_memory_monitor():
    monitor = MemoryMonitor(interval=0.5)
    monitor.start_monitoring()
    time.sleep(5)  # 收集5秒的数据
    monitor.stop_monitoring()
    assert len(monitor.data) > 0, "No data collected"
    print("Test passed, data collected successfully.")

test_memory_monitor()