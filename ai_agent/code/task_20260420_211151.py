import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# 全局变量，用于存储内存使用情况数据
memory_usage_data = []
max_points = 100  # 最多显示的数据点数
update_interval = 1  # 更新频率（秒）

def collect_memory_usage():
    """收集内存使用情况"""
    global memory_usage_data
    while True:
        try:
            # 获取当前系统内存使用率
            mem_info = psutil.virtual_memory()
            used_percent = mem_info.percent
            memory_usage_data.append(used_percent)
            
            # 如果数据点超过最大限制，则移除最早的一个
            if len(memory_usage_data) > max_points:
                memory_usage_data.pop(0)
                
            time.sleep(update_interval)
        except Exception as e:
            print(f"Error collecting memory usage: {e}")

def animate(i, ax):
    """动画函数，更新图表"""
    ax.clear()
    x = np.arange(len(memory_usage_data))
    y = memory_usage_data
    ax.plot(x, y, label='Memory Usage %')
    ax.set_title('System Memory Usage Over Time')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Usage (%)')
    ax.legend(loc='upper left')

def main():
    # 创建一个新的线程来持续收集内存信息
    thread = threading.Thread(target=collect_memory_usage, daemon=True)
    thread.start()

    # 设置matplotlib图形
    fig, ax = plt.subplots()
    ani = FuncAnimation(fig, animate, fargs=(ax,), interval=update_interval*1000)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"未处理的异常: {e}")
    finally:
        print("清理资源并退出...")