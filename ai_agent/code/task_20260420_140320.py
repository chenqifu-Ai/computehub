import psutil
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk
import sys

# 定义全局变量用于存储内存使用数据
memory_usage = []

# 用于更新内存使用的线程函数
def update_memory_usage():
    global memory_usage
    while True:
        try:
            # 获取当前内存使用百分比
            mem_percent = psutil.virtual_memory().percent
            memory_usage.append(mem_percent)
            # 保持列表长度不超过100，以控制图表显示的数据量
            if len(memory_usage) > 100:
                memory_usage.pop(0)
            time.sleep(1)  # 每秒更新一次
        except Exception as e:
            print(f"Error updating memory usage: {e}", file=sys.stderr)

# 创建一个简单的GUI窗口来显示内存使用情况
class MemoryMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("System Memory Monitor")
        self.geometry("800x600")
        
        # 创建一个Frame来容纳Matplotlib图表
        self.frame = ttk.Frame(self, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 初始化图表
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Memory Usage (%)')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 设置动画
        self.ani = FuncAnimation(self.fig, self.update_plot, interval=500)
    
    def update_plot(self, frame):
        self.line.set_data(range(len(memory_usage)), memory_usage)
        self.ax.relim()
        self.ax.autoscale_view(True,True,True)
        return self.line,

if __name__ == "__main__":
    # 启动内存监控线程
    t = threading.Thread(target=update_memory_usage, daemon=True)
    t.start()

    # 启动GUI应用程序
    app = MemoryMonitorApp()
    app.mainloop()