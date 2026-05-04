import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import logging
import configparser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

try:
    INTERVAL = int(config['DEFAULT']['Interval'])
except (KeyError, ValueError):
    INTERVAL = 5  # 默认每5秒采集一次数据
    logger.warning("未能正确读取配置文件中的间隔时间，使用默认值5秒。")

# 共享变量用于存储内存信息
memory_usage_history = []
lock = threading.Lock()

def collect_memory_data():
    """收集系统内存使用情况"""
    global memory_usage_history
    while True:
        try:
            mem_info = psutil.virtual_memory()
            with lock:
                memory_usage_history.append((time.time(), mem_info.percent))
                if len(memory_usage_history) > 100:  # 限制历史记录长度
                    memory_usage_history.pop(0)
            time.sleep(INTERVAL)
        except Exception as e:
            logger.error(f"内存数据收集过程中发生错误：{e}")

def plot_memory_usage(i):
    """绘制内存使用率图表"""
    with lock:
        times, percents = zip(*memory_usage_history)
    plt.cla()  # 清除当前轴
    plt.plot(times, percents, label='Memory Usage %')
    plt.title('System Memory Usage Over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Usage (%)')
    plt.legend(loc='upper left')
    plt.tight_layout()

def main():
    # 创建并启动线程
    thread = threading.Thread(target=collect_memory_data, daemon=True)
    thread.start()

    # 设置图形界面
    fig, ax = plt.subplots()
    ani = FuncAnimation(fig, plot_memory_usage, interval=500)
    
    plt.show()

if __name__ == "__main__":
    main()