import psutil
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# 全局变量定义
memory_data = []
lock = threading.Lock()
stop_threads = False

def get_memory_info():
    """获取系统内存使用情况"""
    try:
        mem_info = psutil.virtual_memory()
        return {
            'total': mem_info.total,
            'available': mem_info.available,
            'percent': mem_info.percent,
            'used': mem_info.used,
            'free': mem_info.free,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Error getting memory info: {e}")
        return None

def monitor_memory(interval=5):
    """定期检查系统内存状态"""
    global stop_threads
    while not stop_threads:
        data_point = get_memory_info()
        if data_point is not None:
            with lock:
                memory_data.append(data_point)
        time.sleep(interval)

def plot_memory_usage():
    """绘制内存使用图表"""
    if not memory_data:
        print("No data to plot.")
        return
    
    # 准备数据
    times = [entry['timestamp'] for entry in memory_data]
    percents = [entry['percent'] for entry in memory_data]

    # 绘图
    plt.figure(figsize=(14, 7))
    sns.lineplot(x=times, y=percents, marker='o')
    plt.title('Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def start_monitoring():
    """启动监控线程"""
    global stop_threads
    stop_threads = False
    thread = threading.Thread(target=monitor_memory)
    thread.start()
    return thread

def stop_monitoring(thread):
    """停止监控并等待线程结束"""
    global stop_threads
    stop_threads = True
    thread.join()

def main():
    print("Starting memory monitoring...")
    monitoring_thread = start_monitoring()
    
    # 监控一段时间后停止
    time.sleep(60)  # 假设我们希望监控1分钟
    stop_monitoring(monitoring_thread)
    print("Monitoring stopped. Plotting results now.")
    
    # 绘制结果
    plot_memory_usage()

if __name__ == "__main__":
    main()