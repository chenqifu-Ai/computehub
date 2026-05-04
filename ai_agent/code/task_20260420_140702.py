import psutil
import matplotlib.pyplot as plt
from threading import Thread, Event
import time
import json
import os

class MemoryMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.memory_usage_data = []
        self.stop_event = Event()
        self.thread = None

    def start_monitoring(self):
        if self.thread and self.thread.is_alive():
            print("Monitoring is already in progress.")
            return
        self.thread = Thread(target=self._monitor_memory)
        self.thread.start()

    def _monitor_memory(self):
        while not self.stop_event.is_set():
            memory_info = psutil.virtual_memory()
            self.memory_usage_data.append({
                'timestamp': time.time(),
                'total': memory_info.total,
                'available': memory_info.available,
                'used': memory_info.used,
                'free': memory_info.free,
                'percent': memory_info.percent
            })
            time.sleep(self.interval)

    def stop_monitoring(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    def plot_memory_usage(self):
        timestamps = [entry['timestamp'] for entry in self.memory_usage_data]
        used_memory = [entry['used'] / (1024 ** 3) for entry in self.memory_usage_data]  # Convert to GB
        available_memory = [entry['available'] / (1024 ** 3) for entry in self.memory_usage_data]  # Convert to GB

        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, used_memory, label='Used Memory (GB)', color='r')
        plt.plot(timestamps, available_memory, label='Available Memory (GB)', color='g')
        plt.title('Memory Usage Over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Memory (GB)')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def save_to_json(self, filename="memory_usage.json"):
        with open(filename, 'w') as f:
            json.dump(self.memory_usage_data, f, indent=4)

def main():
    try:
        monitor = MemoryMonitor(interval=5)
        print("Starting memory monitoring. Press Ctrl+C to stop.")
        monitor.start_monitoring()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping memory monitoring...")
        monitor.stop_monitoring()
        print("Generating memory usage report...")
        monitor.plot_memory_usage()
        monitor.save_to_json()
        print("Report saved to memory_usage.json")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()