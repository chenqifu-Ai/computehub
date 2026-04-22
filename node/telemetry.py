import subprocess
import json
import platform
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-PhysicalTruth")

class PhysicalIdentity:
    """
    Soul-Engine: Physical Origin
    Generate a deterministic hardware fingerprint based on physical components.
    """
    @staticmethod
    def get_fingerprint():
        """
        Builds a fingerprint from:
        1. Machine ID / UUID
        2. CPU Info
        3. GPU UUID (if available)
        """
        components = []
        
        # 1. Machine UUID (Linux specific)
        try:
            with open("/etc/machine-id", "r") as f:
                components.append(f.read().strip())
        except:
            try:
                # Fallback to dmi-id
                res = subprocess.check_output(["cat", "/sys/class/dmi/id/product_uuid"], stderr=subprocess.DEVNULL)
                components.append(res.decode().strip())
            except:
                components.append(platform.node())

        # 2. CPU Info (Simplified)
        try:
            cpu_info = subprocess.check_output(["cat", "/proc/cpuinfo"], stderr=subprocess.DEVNULL).decode()
            # Take first few lines of model name
            for line in cpu_info.splitlines():
                if "model name" in line:
                    components.append(line.split(":")[1].strip())
                    break
        except:
            components.append("unknown_cpu")

        # 3. GPU UUIDs (The most critical part for ComputeHub)
        try:
            gpu_res = subprocess.check_output(["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"], stderr=subprocess.DEVNULL).decode()
            gpu_uuids = gpu_res.strip().splitlines()
            components.extend(gpu_uuids)
        except:
            components.append("no_nvidia_gpu")

        fingerprint_raw = "|".join(components)
        # We return the raw components for registration and a hash for the ID
        import hashlib
        fingerprint_hash = hashlib.sha256(fingerprint_raw.encode()).hexdigest()
        
        return {
            "hash": fingerprint_hash,
            "raw": fingerprint_raw,
            "details": {
                "node_name": platform.node(),
                "os": platform.system(),
                "gpus": components[-1] if "no_nvidia_gpu" not in components else []
            }
        }

class PhysicalTelemetry:
    """
    Soul-Engine: Real-time Physical Truth
    Collects raw hardware metrics instead of software-level summaries.
    """
    @staticmethod
    def collect_gpu_metrics():
        """
        Collects real-time GPU metrics using nvidia-smi.
        Metrics: Temp, Utilization, Memory, Power.
        """
        metrics = {}
        try:
            # Query multiple metrics in one go for efficiency
            cmd = ["nvidia-smi", "--query-gpu=index,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw", "--format=csv,noheader,nounits"]
            res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
            
            for line in res.strip().splitlines():
                parts = line.split(",")
                idx = parts[0].strip()
                metrics[f"gpu_{idx}"] = {
                    "temp": int(parts[1].strip()),
                    "utilization": int(parts[2].strip()),
                    "mem_util": int(parts[3].strip()),
                    "mem_used": int(parts[4].strip()),
                    "mem_total": int(parts[5].strip()),
                    "power": float(parts[6].strip())
                }
        except Exception as e:
            logger.error(f"GPU telemetry failed: {e}")
            metrics["error"] = "No GPU or nvidia-smi not found"
            
        return metrics

    @staticmethod
    def collect_system_metrics():
        """
        Collects OS level metrics.
        """
        import psutil
        return {
            "cpu_util": psutil.cpu_percent(interval=None),
            "ram_used": psutil.virtual_memory().used,
            "ram_total": psutil.virtual_memory().total,
            "disk_util": psutil.disk_usage('/').percent
        }

    def get_full_snapshot(self):
        """
        Returns a complete physical truth snapshot.
        """
        return {
            "timestamp": subprocess.check_output(["date", "+%s"]).decode().strip(),
            "gpu": self.collect_gpu_metrics(),
            "system": self.collect_system_metrics()
        }

if __name__ == "__main__":
    # Testing the Soul-Engine basics
    print("--- Physical Identity ---")
    print(json.dumps(PhysicalIdentity.get_fingerprint(), indent=2))
    
    print("\n--- Physical Telemetry Snapshot ---")
    telemetry = PhysicalTelemetry()
    print(json.dumps(telemetry.get_full_snapshot(), indent=2))
