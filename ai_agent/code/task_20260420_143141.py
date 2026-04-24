import psutil
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 配置日志记录
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 存储内存使用数据的数据结构
memory_data = []

# 定义线程类，用于监控内存使用情况
class MemoryMonitorThread(threading.Thread):
    def __init__(self, interval=1):
        super().__init__()
        self.interval = interval  # 监控间隔时间（秒）
        self.running = True

    def run(self):
        while self.running:
            try:
                # 获取当前系统内存使用情况
                mem_info = psutil.virtual_memory()
                used_memory = mem_info.percent  # 使用百分比
                timestamp = datetime.now()  # 记录时间戳
                memory_data.append((timestamp, used_memory))
                logging.info(f"Memory usage: {used_memory}% at {timestamp}")
            except Exception as e:
                logging.error(f"Error during memory monitoring: {e}")
            finally:
                time.sleep(self.interval)

    def stop(self):
        self.running = False

def plot_memory_usage():
    """根据收集到的数据绘制内存使用图表"""
    timestamps, usages = zip(*memory_data)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(timestamps, usages, marker='o', linestyle='-')
    
    # 设置x轴为日期格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    fig.autofmt_xdate()  # 自动调整x轴标签以避免重叠
    
    ax.set_title('System Memory Usage Over Time')
    ax.set_xlabel('Time')
    ax.set_ylabel('Used Memory (%)')
    plt.grid(True)
    plt.show()

def main():
    monitor_thread = MemoryMonitorThread(interval=5)  # 每5秒检查一次
    try:
        logging.info("Starting memory monitoring...")
        monitor_thread.start()
        
        # 运行指定时间后停止监控
        time.sleep(60)  # 假设我们想运行一分钟
        monitor_thread.stop()
        monitor_thread.join()
        
        logging.info("Memory monitoring stopped. Generating report...")
        if len(memory_data) > 0:
            plot_memory_usage()
        else:
            logging.warning("No data collected for plotting.")
    except KeyboardInterrupt:
        logging.info("Interrupted by user. Stopping the script.")
        monitor_thread.stop()
        monitor_thread.join()
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()