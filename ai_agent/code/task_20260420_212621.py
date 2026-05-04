import threading
import time
import psutil
import matplotlib.pyplot as plt
from datetime import datetime

# 定义一个全局变量来存储内存使用数据
memory_usage_data = []

# 锁对象，用于线程同步访问共享资源
lock = threading.Lock()

def monitor_memory(interval, stop_event):
    """
    监控系统内存使用情况。
    
    :param interval: 采样间隔时间（秒）
    :param stop_event: 用于停止监控的事件
    """
    while not stop_event.is_set():
        try:
            # 获取当前内存使用百分比
            memory_percent = psutil.virtual_memory().percent
            timestamp = datetime.now()
            
            # 加锁后更新内存使用数据
            with lock:
                memory_usage_data.append((timestamp, memory_percent))
                
            # 按照指定间隔暂停
            time.sleep(interval)
        except Exception as e:
            print(f"Error during monitoring: {e}")
            break

def plot_memory_usage(data):
    """
    绘制内存使用情况图表。
    
    :param data: 包含时间戳和内存使用百分比的数据列表
    """
    timestamps, percents = zip(*data)
    plt.figure(figsize=(10,5))
    plt.plot(timestamps, percents, label='Memory Usage %')
    plt.title('System Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    # 创建一个事件，用于控制监控线程何时停止
    stop_event = threading.Event()
    
    # 设置监控间隔为1秒
    interval = 1
    
    # 启动监控线程
    monitor_thread = threading.Thread(target=monitor_memory, args=(interval, stop_event,))
    monitor_thread.start()
    
    try:
        # 主线程等待一段时间，让子线程有足够的机会收集数据
        time.sleep(20)  # 可根据需要调整监控时长
        
        # 停止监控
        stop_event.set()
        
        # 等待监控线程结束
        monitor_thread.join()
        
        # 如果收集到了数据，则绘制图表
        if memory_usage_data:
            plot_memory_usage(memory_usage_data)
        else:
            print("No memory usage data collected.")
    except KeyboardInterrupt:
        print("Interrupted by user. Stopping...")
        stop_event.set()
    finally:
        # 无论是否发生异常，都确保线程被正确关闭
        if monitor_thread.is_alive():
            monitor_thread.join()
        print("Monitoring stopped.")

if __name__ == "__main__":
    main()