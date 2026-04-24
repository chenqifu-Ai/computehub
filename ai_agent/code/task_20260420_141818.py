import psutil
import time
import threading
from queue import Queue
import matplotlib.pyplot as plt
from datetime import datetime

# 配置日志记录
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔秒数
        self.data_queue = Queue()  # 存储内存数据
        self.running = False
    
    def start(self):
        """启动监控"""
        if not self.running:
            self.running = True
            t = threading.Thread(target=self._monitor)
            t.start()
    
    def stop(self):
        """停止监控"""
        self.running = False
    
    def _monitor(self):
        """后台线程执行的内存监控逻辑"""
        try:
            while self.running:
                memory_info = psutil.virtual_memory()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.data_queue.put((timestamp, memory_info.total, memory_info.available, memory_info.percent))
                time.sleep(self.interval)
        except Exception as e:
            logging.error(f"Error in monitoring: {e}")
    
    def get_data(self):
        """获取所有已收集的数据"""
        data = []
        while not self.data_queue.empty():
            data.append(self.data_queue.get())
        return data
    
def plot_memory_usage(data):
    """绘制内存使用情况图"""
    timestamps, totals, availables, percents = zip(*data)
    fig, ax1 = plt.subplots()

    color = 'tab:blue'
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Memory (GB)', color=color)
    ax1.plot(timestamps, [x / (1024**3) for x in totals], label="Total", color=color)
    ax1.plot(timestamps, [x / (1024**3) for x in availables], label="Available", color='green')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Usage (%)', color=color)
    ax2.plot(timestamps, percents, label="Used %", color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()
    plt.title("System Memory Usage Over Time")
    plt.legend(loc='best')
    plt.show()

if __name__ == "__main__":
    monitor = MemoryMonitor(interval=5)  # 每5秒检查一次
    try:
        monitor.start()
        print("Monitoring started. Press Ctrl+C to stop.")
        while True:  # 无限循环，直到用户中断
            pass
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop()
        collected_data = monitor.get_data()
        if collected_data:
            plot_memory_usage(collected_data)
        else:
            print("No data collected.")