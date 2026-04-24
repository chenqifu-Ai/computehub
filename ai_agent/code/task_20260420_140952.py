import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 全局变量存储内存使用数据
memory_usage_data = []
time_points = []

# 定义一个线程类，用于持续监控内存使用情况
class MemoryMonitorThread(threading.Thread):
    def __init__(self, interval=1):
        super().__init__()
        self.interval = interval  # 监控间隔时间（秒）
        self.running = True

    def run(self):
        global memory_usage_data, time_points
        while self.running:
            try:
                # 获取当前内存使用百分比
                mem_info = psutil.virtual_memory()
                memory_usage_data.append(mem_info.percent)
                time_points.append(time.strftime("%H:%M:%S"))
                print(f"Memory Usage: {mem_info.percent}% at {time_points[-1]}")
                time.sleep(self.interval)
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    def stop(self):
        self.running = False

# 初始化图形界面
def init_plot():
    fig, ax = plt.subplots()
    line, = ax.plot([], [], lw=2)
    ax.set_xlim(0, 60)  # 假设最多显示60个点
    ax.set_ylim(0, 100)  # 内存使用率范围
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Memory Usage (%)')
    ax.set_title('Real-time Memory Usage Monitor')
    return fig, ax, line

# 更新图形数据
def update(frame, line):
    if len(memory_usage_data) > 0:
        line.set_data(range(len(memory_usage_data)), memory_usage_data)
        if len(memory_usage_data) > 60:
            del memory_usage_data[0]
            del time_points[0]
    return line,

# 主函数
if __name__ == "__main__":
    monitor_thread = MemoryMonitorThread(interval=5)  # 每5秒采集一次
    try:
        # 启动内存监控线程
        monitor_thread.start()

        # 准备并启动实时更新的图表
        fig, ax, line = init_plot()
        ani = FuncAnimation(fig, update, fargs=(line,), interval=1000, blit=True)

        # 显示图表
        plt.show()
    except KeyboardInterrupt:
        print("Stopping the program.")
    finally:
        # 确保线程正确关闭
        monitor_thread.stop()
        monitor_thread.join()
        print("Program has been terminated gracefully.")