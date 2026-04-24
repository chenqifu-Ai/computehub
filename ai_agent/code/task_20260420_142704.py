import psutil
import time
import threading
import matplotlib.pyplot as plt
from datetime import datetime

# 定义一个类来处理内存数据收集
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间（秒）
        self.memory_data = []  # 存储内存使用情况的数据列表
        self.stop_flag = threading.Event()  # 用于控制线程停止的标志

    def start_monitoring(self):
        """启动内存监控线程"""
        self.thread = threading.Thread(target=self._monitor_memory)
        self.thread.start()

    def _monitor_memory(self):
        """后台线程中执行的实际监控逻辑"""
        while not self.stop_flag.is_set():
            try:
                mem_info = psutil.virtual_memory()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.memory_data.append((current_time, mem_info.percent))
                print(f"Memory Usage: {mem_info.percent}% at {current_time}")
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error occurred during monitoring: {e}")
                break

    def stop_monitoring(self):
        """停止内存监控并等待线程结束"""
        self.stop_flag.set()
        if self.thread and self.thread.is_alive():
            self.thread.join()

    def plot_memory_usage(self):
        """绘制内存使用情况图表"""
        times, usages = zip(*self.memory_data)  # 解包数据
        plt.figure(figsize=(10, 5))
        plt.plot(times, usages, marker='o', linestyle='-')
        plt.title('System Memory Usage Over Time')
        plt.xlabel('Time')
        plt.ylabel('Memory Usage (%)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

def main():
    monitor = MemoryMonitor(interval=2)  # 每两秒检查一次
    try:
        monitor.start_monitoring()
        # 监控持续进行，这里设置为60秒后停止
        time.sleep(60)
    except KeyboardInterrupt:
        print("Monitoring interrupted by user.")
    finally:
        monitor.stop_monitoring()
        monitor.plot_memory_usage()

if __name__ == "__main__":
    main()

# 测试用例部分
def test_memory_monitor():
    monitor = MemoryMonitor(interval=1)
    monitor.start_monitoring()
    time.sleep(5)  # 运行5秒钟
    monitor.stop_monitoring()
    assert len(monitor.memory_data) > 0, "No memory data collected."
    print("Test passed. Data collection successful.")

test_memory_monitor()