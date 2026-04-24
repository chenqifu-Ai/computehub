import psutil
import time
import threading
from queue import Queue
import matplotlib.pyplot as plt
import numpy as np

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.running = False
        self.data_queue = Queue()
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_memory)
        self.thread.start()
    
    def stop(self):
        self.running = False
        self.thread.join()
    
    def _monitor_memory(self):
        while self.running:
            try:
                mem_info = psutil.virtual_memory()
                self.data_queue.put(mem_info.percent)
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error in monitoring: {e}")
                break

class DataProcessor:
    def process_data(self, data_queue, max_samples=60):
        samples = []
        while not data_queue.empty():
            sample = data_queue.get()
            if len(samples) >= max_samples:
                samples.pop(0)
            samples.append(sample)
        return samples

class Plotter:
    def plot_memory_usage(self, memory_usage):
        x = np.arange(len(memory_usage))
        y = np.array(memory_usage)

        plt.figure(figsize=(10, 5))
        plt.plot(x, y, label='Memory Usage (%)')
        plt.title('System Memory Usage Over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Usage %')
        plt.legend()
        plt.grid(True)
        plt.show()

def main():
    monitor = MemoryMonitor(interval=1)
    processor = DataProcessor()
    plotter = Plotter()

    try:
        # Start monitoring
        monitor.start()
        
        # Run for a certain period or until interrupted
        run_time = 60  # seconds
        end_time = time.time() + run_time
        while time.time() < end_time:
            time.sleep(1)
            
        # Stop the monitor and process the collected data
        monitor.stop()
        memory_usage = processor.process_data(monitor.data_queue)
        
        # Generate and display the plot
        plotter.plot_memory_usage(memory_usage)
        
    except KeyboardInterrupt:
        print("Monitoring stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the monitor is stopped
        if monitor.running:
            monitor.stop()

if __name__ == "__main__":
    main()