import psutil
import threading
import time
import matplotlib.pyplot as plt
from datetime import datetime

# 定义一个类来处理内存数据收集
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间（秒）
        self.memory_usage_data = []  # 存储内存使用情况的数据
        self.stop_event = threading.Event()  # 用于安全停止线程的事件

    def start_monitoring(self):
        """启动内存监控"""
        thread = threading.Thread(target=self._monitor_memory)
        thread.start()
        return thread

    def _monitor_memory(self):
        """后台线程中执行的实际内存监控逻辑"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.memory_usage_data.append((timestamp, mem_info.percent))
                print(f"Memory Usage: {mem_info.percent}% at {timestamp}")
                time.sleep(self.interval)
            except Exception as e:
                print(f"An error occurred during monitoring: {e}")
                break  # 如果出现错误，则停止监控

    def stop_monitoring(self):
        """停止内存监控"""
        self.stop_event.set()

    def plot_memory_usage(self):
        """绘制内存使用情况图"""
        if not self.memory_usage_data:
            print("No data available for plotting.")
            return
        
        times, usages = zip(*self.memory_usage_data)
        plt.figure(figsize=(10, 6))
        plt.plot(times, usages, marker='o')
        plt.title('System Memory Usage Over Time')
        plt.xlabel('Time')
        plt.ylabel('Memory Usage (%)')
        plt.xticks(rotation=45)  # 旋转x轴标签以便更好显示
        plt.tight_layout()  # 自动调整子图参数, 使之填充整个图像区域
        plt.grid(True)
        plt.show()

def main():
    monitor = MemoryMonitor(interval=2)  # 每两秒记录一次
    monitor_thread = monitor.start_monitoring()
    
    try:
        # 运行一段时间后停止监控，这里设置为30秒
        time.sleep(30)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        monitor.stop_monitoring()
        monitor_thread.join()  # 等待线程结束
    
    monitor.plot_memory_usage()  # 绘制图形

if __name__ == "__main__":
    main()