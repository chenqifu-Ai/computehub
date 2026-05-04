import psutil
import time
import threading
from queue import Queue
import matplotlib.pyplot as plt
from datetime import datetime

# 配置
UPDATE_INTERVAL = 5  # 每隔多少秒更新一次数据
MAX_DATA_POINTS = 120  # 最多保留的数据点数，基于每5秒一个点，这将覆盖大约1小时的数据

class MemoryMonitor:
    def __init__(self):
        self.data_queue = Queue()
        self.stop_event = threading.Event()

    def start_monitoring(self):
        """启动内存监控线程"""
        monitor_thread = threading.Thread(target=self._monitor_memory)
        monitor_thread.start()

    def _monitor_memory(self):
        """后台线程中执行的内存监控逻辑"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                current_time = datetime.now().strftime("%H:%M:%S")
                self.data_queue.put((current_time, mem_info.percent))
                if self.data_queue.qsize() > MAX_DATA_POINTS:
                    self.data_queue.get()  # 移除最旧的数据点
                time.sleep(UPDATE_INTERVAL)
            except Exception as e:
                print(f"内存监控遇到错误: {e}")
                time.sleep(UPDATE_INTERVAL)  # 出现异常时暂停一段时间后重试

    def stop_monitoring(self):
        """停止内存监控"""
        self.stop_event.set()

    def plot_memory_usage(self):
        """绘制内存使用情况图表"""
        times, usages = [], []
        while not self.data_queue.empty():
            time, usage = self.data_queue.get()
            times.append(time)
            usages.append(usage)

        plt.figure(figsize=(14, 7))
        plt.plot(times, usages, marker='o')
        plt.title('系统内存使用率随时间变化')
        plt.xlabel('时间')
        plt.ylabel('内存使用率 (%)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

def main():
    monitor = MemoryMonitor()
    try:
        monitor.start_monitoring()
        input("按 Enter 键停止监控并查看结果...")
    except KeyboardInterrupt:
        print("检测到中断，正在准备关闭...")
    finally:
        monitor.stop_monitoring()
        monitor.plot_memory_usage()

if __name__ == "__main__":
    main()