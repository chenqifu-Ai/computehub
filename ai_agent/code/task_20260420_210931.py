import threading
import time
import psutil
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import datetime

# 配置日志记录
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MemoryMonitor:
    def __init__(self):
        self.memory_data = []
        self.timestamps = []
        self.running = True

    def collect_memory_info(self):
        """收集内存信息"""
        try:
            while self.running:
                mem_info = psutil.virtual_memory()
                self.memory_data.append(mem_info.percent)
                self.timestamps.append(datetime.datetime.now())
                time.sleep(1)  # 每秒收集一次数据
        except Exception as e:
            logging.error(f"Error in collecting memory info: {e}")

    def start_monitoring(self):
        """启动监控线程"""
        self.monitor_thread = threading.Thread(target=self.collect_memory_info)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止监控并等待线程结束"""
        self.running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()

    def plot_live_graph(self, i):
        """绘制实时图表"""
        plt.cla()  # 清除当前图形
        plt.plot(self.timestamps, self.memory_data, label="Memory Usage %")
        plt.title("System Memory Usage Over Time")
        plt.xlabel("Time")
        plt.ylabel("Memory Usage (%)")
        plt.legend(loc="upper left")
        plt.tight_layout()

def main():
    monitor = MemoryMonitor()
    
    # 启动内存监控
    monitor.start_monitoring()
    
    # 创建一个动态更新的图表
    fig, ax = plt.subplots()
    ani = FuncAnimation(fig, monitor.plot_live_graph, interval=1000)  # 每秒刷新一次
    
    # 显示图表
    plt.show()
    
    # 结束后停止监控
    monitor.stop_monitoring()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("程序被用户中断。")
    except Exception as e:
        logging.error(f"未知错误: {e}")