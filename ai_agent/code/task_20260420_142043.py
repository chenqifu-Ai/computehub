import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# 配置matplotlib以支持中文显示（如果需要的话）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间
        self.memory_usage_history = []  # 存储内存使用历史数据
        self.max_data_points = 60  # 最多存储的数据点数量
        self.lock = threading.Lock()  # 线程锁，保证数据访问安全
        self.stop_event = threading.Event()  # 用于停止监控的事件

    def start_monitoring(self):
        """启动内存监控线程"""
        monitor_thread = threading.Thread(target=self._monitor_memory)
        monitor_thread.daemon = True  # 设置为守护线程
        monitor_thread.start()

    def _monitor_memory(self):
        """持续监控系统内存使用情况"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                with self.lock:
                    if len(self.memory_usage_history) >= self.max_data_points:
                        self.memory_usage_history.pop(0)
                    self.memory_usage_history.append(mem_info.percent)
            except Exception as e:
                print(f"内存监控时发生错误: {e}")
            finally:
                time.sleep(self.interval)

    def stop_monitoring(self):
        """停止内存监控"""
        self.stop_event.set()

    def plot_memory_usage(self):
        """绘制内存使用情况图"""
        fig, ax = plt.subplots()
        
        def update(frame):
            with self.lock:
                y = self.memory_usage_history[-self.max_data_points:]
                x = range(len(y))
            ax.clear()
            ax.plot(x, y, label='内存使用率 (%)')
            ax.set_ylim(0, 100)
            ax.legend(loc='upper left')
            ax.set_title('系统内存使用情况')
            ax.set_xlabel('时间 (秒)')
            ax.set_ylabel('内存使用率 (%)')

        ani = FuncAnimation(fig, update, interval=200, blit=False)
        plt.show()

def main():
    monitor = MemoryMonitor(interval=1)
    try:
        monitor.start_monitoring()
        print("开始监控内存使用情况...")
        # 模拟长时间运行
        time.sleep(30)  # 可根据需要调整监控时长
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止监控...")
    finally:
        monitor.stop_monitoring()
        print("监控已停止。")
        monitor.plot_memory_usage()

if __name__ == "__main__":
    main()