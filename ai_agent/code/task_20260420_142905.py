import psutil
import time
import threading
import matplotlib.pyplot as plt
from datetime import datetime

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.memory_usage_data = []
        self.timestamps = []
        self.running = True

    def collect_memory_usage(self):
        """Collects memory usage percentage and timestamp."""
        while self.running:
            try:
                mem_info = psutil.virtual_memory()
                current_time = datetime.now().strftime('%H:%M:%S')
                self.memory_usage_data.append(mem_info.percent)
                self.timestamps.append(current_time)
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error collecting memory data: {e}")
                break

    def plot_memory_usage(self):
        """Plots the collected memory usage over time."""
        try:
            plt.figure(figsize=(10, 6))
            plt.plot(self.timestamps, self.memory_usage_data, marker='o')
            plt.title('Memory Usage Over Time')
            plt.xlabel('Time (HH:MM:SS)')
            plt.ylabel('Memory Usage (%)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Error plotting graph: {e}")

def main():
    monitor = MemoryMonitor(interval=2)  # Set the interval to 2 seconds
    try:
        # Start the thread for monitoring memory
        monitor_thread = threading.Thread(target=monitor.collect_memory_usage)
        monitor_thread.start()

        # Let it run for 30 seconds
        time.sleep(30)

        # Stop the monitoring
        monitor.running = False
        monitor_thread.join()

        # Plot the results
        monitor.plot_memory_usage()
    except KeyboardInterrupt:
        print("Monitoring stopped by user.")
        monitor.running = False
        monitor_thread.join()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()