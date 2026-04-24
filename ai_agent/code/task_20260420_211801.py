import psutil
import time
import threading
import matplotlib.pyplot as plt
from datetime import datetime

# 全局变量，用于存储内存使用数据
memory_usage_data = []

# 定义一个函数来获取系统当前的内存使用情况
def get_memory_info():
    memory = psutil.virtual_memory()
    return memory.percent  # 返回内存使用百分比

# 定义多线程任务，定期收集内存使用信息
class MemoryMonitorThread(threading.Thread):
    def __init__(self, interval=1):
        super().__init__()
        self.interval = interval  # 设置检查间隔时间（秒）
        self.running = True  # 线程运行标志

    def run(self):
        global memory_usage_data
        try:
            while self.running:
                # 获取当前时间和内存使用率
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                mem_usage = get_memory_info()
                print(f"Memory usage at {current_time}: {mem_usage}%")
                
                # 将数据添加到列表中
                memory_usage_data.append((current_time, mem_usage))
                
                # 每隔指定的时间间隔执行一次
                time.sleep(self.interval)
        except Exception as e:
            print(f"An error occurred: {e}")

    def stop(self):
        self.running = False

# 函数用于绘制内存使用趋势图
def plot_memory_usage(data):
    times, usages = zip(*data)  # 解压数据
    plt.figure(figsize=(10,5))
    plt.plot(times, usages, marker='o')
    plt.title('System Memory Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (%)')
    plt.xticks(rotation=45)  # 旋转x轴标签以便阅读
    plt.tight_layout()  # 自动调整子图参数, 使之填充整个图像区域
    plt.show()

# 主函数
def main():
    monitor_thread = MemoryMonitorThread(interval=2)  # 创建监控线程，每2秒检查一次
    monitor_thread.start()  # 启动线程
    
    try:
        input("Press Enter to stop monitoring and display the chart...\n")
    except KeyboardInterrupt:
        print("Monitoring stopped.")
    
    monitor_thread.stop()  # 停止线程
    monitor_thread.join()  # 等待线程结束
    
    if memory_usage_data:
        plot_memory_usage(memory_usage_data)  # 绘制图表
    else:
        print("No data collected.")

if __name__ == "__main__":
    main()