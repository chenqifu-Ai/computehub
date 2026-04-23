# ComputeHub Core - Configuration
# Inherited from OpenPC System config-driven architecture pattern

import os
import yaml
from pathlib import Path
from typing import Optional

# Log with timestamp (OpenPC System pattern)
def log_with_timestamp(msg: str, level: str = "INFO"):
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


class Config:
    """Configuration loader - YAML config, overrides via environment variables."""
    
    _instance = None
    _data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, config_path: Optional[str] = None):
        """Load configuration from YAML file."""
        if self._loaded:
            return self._data

        if config_path is None:
            config_path = os.getenv(
                "COMPUTEHUB_CONFIG",
                str(Path(__file__).parent.parent.parent / "config.yaml")
            )

        path = Path(config_path)
        if not path.exists():
            log_with_timestamp(f"⚠️  Config file not found: {config_path}, using defaults")
            self._data = self._defaults()
        else:
            with open(path, "r") as f:
                self._data = yaml.safe_load(f) or {}

        # Environment variable overrides
        if port := os.getenv("COMPUTEHUB_PORT"):
            self._data.setdefault("gateway", {})["port"] = int(port)
        if db := os.getenv("COMPUTEHUB_DATABASE_URL"):
            self._data["database"]["url"] = db
        if secret := os.getenv("COMPUTEHUB_SECRET_KEY"):
            self._data["auth"]["secret_key"] = secret

        self._loaded = True
        log_with_timestamp(f"✅ Config loaded: {config_path}")
        return self._data

    @property
    def data(self):
        if not self._loaded:
            self.load()
        return self._data

    @property
    def database_url(self) -> str:
        return self.data.get("database", {}).get("url", "sqlite:///./computehub.db")

    @property
    def gateway_host(self) -> str:
        return self.data.get("gateway", {}).get("host", "0.0.0.0")

    @property
    def gateway_port(self) -> int:
        return self.data.get("gateway", {}).get("port", 8000)

    @property
    def gateway_workers(self) -> int:
        return self.data.get("gateway", {}).get("workers", 4)

    @property
    def auth_secret_key(self) -> str:
        return self.data.get("auth", {}).get("secret_key", "change-me-in-production")

    @property
    def auth_algorithm(self) -> str:
        return self.data.get("auth", {}).get("algorithm", "HS256")

    @property
    def kernel_queue_size(self) -> int:
        return self.data.get("kernel", {}).get("queue_size", 1000)

    @property
    def kernel_max_states(self) -> int:
        return self.data.get("kernel", {}).get("max_states", 10000)

    @property
    def executor_sandbox_path(self) -> str:
        return self.data.get("executor", {}).get("sandbox_path", "/tmp/computehub-sandbox")

    @property
    def executor_default_framework(self) -> str:
        return self.data.get("executor", {}).get("default_framework", "pytorch")

    @property
    def executor_default_image(self) -> str:
        return self.data.get("executor", {}).get("default_image", "python:3.11-slim")

    @property
    def learning_store_path(self) -> str:
        return self.data.get("learning", {}).get("store_path", "./genes.json")

    @property
    def learning_recall_threshold(self) -> float:
        return self.data.get("learning", {}).get("recall_threshold", 0.8)

    @staticmethod
    def _defaults():
        return {
            "database": {"url": "sqlite:///./computehub.db"},
            "gateway": {"host": "0.0.0.0", "port": 8000, "workers": 4},
            "auth": {"secret_key": "change-me-in-production", "algorithm": "HS256"},
            "kernel": {"queue_size": 1000, "max_states": 10000},
            "executor": {"sandbox_path": "/tmp/computehub-sandbox"},
            "learning": {"store_path": "./genes.json", "recall_threshold": 0.8},
        }


# Global config singleton
config = Config()
