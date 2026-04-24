import psutil
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 存储内存使用数据的列表
memory_data = []
timestamps = []

# 定义一个类来处理多线程内存监控
class MemoryMonitor:
    def __init__(self, interval=1):
        """
        初始化MemoryMonitor对象。
        
        参数:
            interval (int): 监控间隔时间（秒）。
        """
        self.interval = interval
        self.running = False
        self.thread = None

    def start(self):
        """开始监控内存。"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor)
            self.thread.start()

    def stop(self):
        """停止监控内存。"""
        self.running = False
        if self.thread is not None:
            self.thread.join()

    def _monitor(self):
        """内部方法，用于定期收集内存信息。"""
        while self.running:
            try:
                mem_info = psutil.virtual_memory()
                memory_data.append(mem_info.percent)
                timestamps.append(datetime.now())
                print(f"Memory Usage: {mem_info.percent}%")
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error occurred during monitoring: {e}")
                break  # 如果出现错误则停止监控

def plot_memory_usage():
    """绘制内存使用情况图表。"""
    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(timestamps, memory_data, label='Memory Usage (%)')
    
    # 设置x轴格式为日期时间
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    plt.xticks(rotation=45)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Memory Usage (%)')
    ax.set_title('System Memory Usage Over Time')
    ax.legend()
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    monitor = MemoryMonitor(interval=2)  # 每2秒收集一次数据
    try:
        monitor.start()
        input("Press Enter to stop the monitoring and generate the report...")
    except KeyboardInterrupt:
        print("Monitoring interrupted.")
    finally:
        monitor.stop()
        plot_memory_usage()