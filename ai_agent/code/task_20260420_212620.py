import psutil
import time
import threading
import matplotlib.pyplot as plt
from datetime import datetime

# 定义一个类来封装内存监控逻辑
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间（秒）
        self.memory_data = []  # 存储每次采集的内存使用情况
        self.timestamps = []  # 存储每次采集的时间戳
        self.stop_event = threading.Event()  # 线程停止事件

    def start_monitoring(self):
        """启动内存监控线程"""
        monitor_thread = threading.Thread(target=self._monitor_memory)
        monitor_thread.start()
        return monitor_thread

    def _monitor_memory(self):
        """内部方法，用于定期收集内存信息"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"Time: {current_time}, Memory Usage: {mem_info.percent}%")
                self.memory_data.append(mem_info.percent)
                self.timestamps.append(current_time)
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error occurred during memory monitoring: {e}")
                break  # 如果发生错误，则停止监控

    def stop_monitoring(self):
        """停止内存监控"""
        self.stop_event.set()

    def plot_memory_usage(self):
        """绘制内存使用情况图"""
        if len(self.memory_data) > 0:
            plt.figure(figsize=(10,5))
            plt.plot(self.timestamps, self.memory_data, marker='o')
            plt.title('Memory Usage Over Time')
            plt.xlabel('Timestamp')
            plt.ylabel('Memory Usage (%)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        else:
            print("No data available for plotting.")

def main():
    # 初始化内存监控器
    monitor = MemoryMonitor(interval=2)  # 每2秒检查一次
    # 开始监控
    monitor_thread = monitor.start_monitoring()
    
    try:
        # 让主线程等待一段时间后结束监控
        time.sleep(30)  # 监控30秒
    except KeyboardInterrupt:
        print("Monitoring interrupted by user.")
    finally:
        # 停止监控
        monitor.stop_monitoring()
        # 等待监控线程完全退出
        monitor_thread.join()
        # 显示内存使用情况图表
        monitor.plot_memory_usage()

if __name__ == "__main__":
    main()