import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# 配置matplotlib以适应中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔，单位为秒
        self.memory_usage_data = []
        self.running = True
        self.lock = threading.Lock()

    def collect_memory_usage(self):
        """收集内存使用情况"""
        while self.running:
            with self.lock:
                mem_info = psutil.virtual_memory()
                self.memory_usage_data.append(mem_info.percent)
            time.sleep(self.interval)

    def start_monitoring(self):
        """开始监控线程"""
        self.thread = threading.Thread(target=self.collect_memory_usage)
        self.thread.start()

    def stop_monitoring(self):
        """停止监控并等待线程结束"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join()

def update(frame, *fargs):
    """更新图表数据"""
    monitor, ax = fargs
    with monitor.lock:
        data = monitor.memory_usage_data[-50:]  # 只显示最近50个点
    ax.clear()
    ax.plot(data, label='内存使用率(%)')
    ax.set_title('系统内存使用情况')
    ax.set_xlabel('时间 (采样点)')
    ax.set_ylabel('使用率 (%)')
    ax.legend(loc="upper left")
    ax.grid(True)

def main():
    try:
        monitor = MemoryMonitor(interval=1)  # 每秒采集一次
        fig, ax = plt.subplots()
        ani = FuncAnimation(fig, update, fargs=(monitor, ax), interval=1000)
        
        print("开始监控内存使用情况...")
        monitor.start_monitoring()
        plt.show()
    except Exception as e:
        print(f"遇到错误: {e}")
    finally:
        monitor.stop_monitoring()
        print("监控已停止。")

if __name__ == "__main__":
    main()