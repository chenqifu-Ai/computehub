import psutil
import time
import threading
from queue import Queue, Empty
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime

# 配置项
UPDATE_INTERVAL = 1  # 内存数据更新间隔（秒）
PLOT_REFRESH_RATE = 500  # 图表刷新率（毫秒）

# 数据队列
data_queue = Queue()

def fetch_memory_info():
    """获取系统内存信息"""
    mem_info = psutil.virtual_memory()
    return mem_info.percent, mem_info.available / (1024 ** 3)  # 百分比, 可用GB数

def memory_monitor():
    """后台线程，持续监控内存使用情况"""
    while True:
        try:
            percent, available_gb = fetch_memory_info()
            data_queue.put((datetime.now(), percent, available_gb))
        except Exception as e:
            print(f"Error in memory monitoring: {e}")
        finally:
            time.sleep(UPDATE_INTERVAL)

def plot_memory_usage(i):
    """用于matplotlib的动画函数，绘制内存使用图表"""
    xs, ys_percent, ys_available = [], [], []
    try:
        while not data_queue.empty():
            timestamp, percent, available = data_queue.get_nowait()
            xs.append(timestamp)
            ys_percent.append(percent)
            ys_available.append(available)
    except Empty:
        pass
    
    ax.clear()
    ax.plot(xs, ys_percent, label='Memory Usage %')
    ax.plot(xs, ys_available, label='Available Memory (GB)')
    ax.legend(loc="upper left")
    ax.set_title('System Memory Usage Over Time')
    ax.set_xlabel('Time')
    ax.set_ylabel('Memory Usage (%) / Available Memory (GB)')
    plt.xticks(rotation=45)
    plt.tight_layout()

if __name__ == "__main__":
    fig, ax = plt.subplots(figsize=(14, 7))

    # 启动内存监控线程
    monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
    monitor_thread.start()

    # 创建动画对象并开始显示
    ani = animation.FuncAnimation(fig, plot_memory_usage, interval=PLOT_REFRESH_RATE)
    
    try:
        plt.show()
    except KeyboardInterrupt:
        print("程序被用户中断。")
    except Exception as e:
        print(f"遇到未知错误: {e}")
    finally:
        print("清理资源...")
        # 在这里可以添加额外的清理工作，如关闭文件、数据库连接等。
        
    print("程序结束。")