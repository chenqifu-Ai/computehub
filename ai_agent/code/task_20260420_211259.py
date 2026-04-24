import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 定义一个类来封装内存监控逻辑
class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval  # 监控间隔时间
        self.memory_data = []  # 存储内存使用数据
        self.stop_event = threading.Event()  # 用于停止线程的事件

    def start_monitoring(self):
        """启动内存监控"""
        self.thread = threading.Thread(target=self._monitor_memory)
        self.thread.start()

    def _monitor_memory(self):
        """后台线程中执行的内存监控函数"""
        try:
            while not self.stop_event.is_set():
                mem_info = psutil.virtual_memory()
                self.memory_data.append(mem_info.percent)  # 记录内存百分比
                time.sleep(self.interval)
        except Exception as e:
            print(f"内存监控遇到错误: {e}")

    def stop_monitoring(self):
        """停止内存监控"""
        self.stop_event.set()
        self.thread.join()

    def get_memory_data(self):
        """获取当前收集到的所有内存数据"""
        return self.memory_data

def update(frame, *fargs):
    """更新图表的数据"""
    ax = fargs[0]
    monitor = fargs[1]
    ax.clear()
    data = monitor.get_memory_data()
    ax.plot(data, label='Memory Usage %')
    ax.set_title('System Memory Usage Over Time')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Usage (%)')
    ax.legend(loc='upper right')

if __name__ == "__main__":
    # 创建内存监控对象
    monitor = MemoryMonitor(interval=2)  # 每两秒采集一次
    monitor.start_monitoring()

    # 设置图形界面
    fig, ax = plt.subplots()
    ani = FuncAnimation(fig, update, fargs=(ax, monitor), interval=500)

    plt.tight_layout()
    plt.show()

    # 当用户关闭窗口时，停止监控
    monitor.stop_monitoring()
    
    # 异常处理示例
    try:
        # 这里可以添加更多的异常测试代码
        pass
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        
    print("内存监控已结束。")