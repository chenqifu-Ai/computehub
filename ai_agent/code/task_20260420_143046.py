import psutil
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 全局变量，用于存储内存使用数据
memory_data = []
lock = threading.Lock()

def collect_memory_usage():
    """收集系统内存使用情况"""
    while True:
        try:
            # 获取当前时间
            current_time = datetime.now()
            # 获取内存信息
            mem_info = psutil.virtual_memory()
            with lock:
                memory_data.append((current_time, mem_info.percent))
        except Exception as e:
            print(f"Error collecting memory usage: {e}")
        finally:
            # 每隔一段时间采样一次
            time.sleep(5)

def plot_memory_usage():
    """绘制内存使用图表"""
    try:
        if not memory_data:
            return
        
        dates, usages = zip(*memory_data)
        
        fig, ax = plt.subplots()
        ax.plot(dates, usages, label='Memory Usage %')
        
        # 设置日期格式
        date_format = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
        ax.xaxis.set_major_formatter(date_format)
        fig.autofmt_xdate()
        
        plt.title('System Memory Usage Over Time')
        plt.xlabel('Time')
        plt.ylabel('Usage (%)')
        plt.legend()
        plt.show()
    except Exception as e:
        print(f"Error plotting memory usage: {e}")

def main():
    # 启动内存监控线程
    collector_thread = threading.Thread(target=collect_memory_usage, daemon=True)
    collector_thread.start()
    
    # 等待一段时间后生成图表
    time.sleep(60)  # 可以根据需要调整等待时间
    
    # 停止线程并绘制图表
    plot_memory_usage()

if __name__ == "__main__":
    main()