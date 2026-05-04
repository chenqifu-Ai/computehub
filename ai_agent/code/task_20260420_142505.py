import psutil
import matplotlib.pyplot as plt
from threading import Thread, Event
import time
import logging

# 设置日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.stop_event = Event()
        self.memory_data = []

    def start(self):
        """启动内存监控线程"""
        logging.info("Starting memory monitor.")
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _run(self):
        """内部运行方法，用于收集内存使用数据"""
        while not self.stop_event.is_set():
            try:
                mem_info = psutil.virtual_memory()
                self.memory_data.append(mem_info.percent)
                logging.debug(f"Memory usage: {mem_info.percent}%")
                time.sleep(self.interval)
            except Exception as e:
                logging.error(f"Error occurred during monitoring: {e}")
    
    def stop(self):
        """停止监控线程并等待其结束"""
        logging.info("Stopping memory monitor.")
        self.stop_event.set()
        self.thread.join()

    def plot_memory_usage(self):
        """绘制内存使用情况图表"""
        if not self.memory_data:
            logging.warning("No data to plot. Please ensure the monitor has been started and stopped properly.")
            return
        
        plt.figure(figsize=(10, 6))
        plt.plot(self.memory_data, label="Memory Usage (%)", color="blue")
        plt.title("System Memory Usage Over Time")
        plt.xlabel("Time (s)")
        plt.ylabel("Usage (%)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

def main():
    # 创建内存监控实例
    monitor = MemoryMonitor(interval=5)  # 每5秒记录一次
    try:
        # 启动监控
        monitor.start()
        # 运行一段时间后停止
        time.sleep(30)  # 监控30秒
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt detected. Stopping...")
    finally:
        # 停止监控
        monitor.stop()
        # 绘制图表
        monitor.plot_memory_usage()

if __name__ == "__main__":
    main()