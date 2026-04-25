"""配置管理 - YAML + 环境变量覆盖"""
import os
import yaml
from pathlib import Path
from functools import lru_cache

class Config:
    """单例配置，加载 YAML，环境变量覆盖，12-Factor App 风格"""

    _instance = None
    _data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, config_path: str = None):
        if self._loaded:
            return self._data

        # 自动查找 config.yaml
        if not config_path:
            config_path = os.getenv("COMPUTEHUB_CONFIG")
            if not config_path:
                config_path = str(Path(__file__).parent.parent.parent / "config.yaml")

        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                self._data = yaml.safe_load(f) or {}
        else:
            print(f"⚠️  Config not found: {config_path}, using defaults")
            self._data = self._defaults()

        # 环境变量覆盖
        if os.getenv("COMPUTEHUB_DATABASE_URL"):
            self._data.setdefault("database", {})["url"] = os.getenv("COMPUTEHUB_DATABASE_URL")
        if os.getenv("COMPUTEHUB_PORT"):
            self._data.setdefault("gateway", {})["port"] = int(os.getenv("COMPUTEHUB_PORT"))
        if os.getenv("COMPUTEHUB_SECRET_KEY"):
            self._data.setdefault("auth", {})["secret_key"] = os.getenv("COMPUTEHUB_SECRET_KEY")

        self._loaded = True
        return self._data

    @property
    def data(self):
        if not self._loaded:
            self.load()
        return self._data

    @property
    def database_url(self) -> str:
        return self.data.get("database", {}).get("url", "sqlite+aiosqlite:///./computehub.db")

    @property
    def gateway_host(self) -> str:
        return self.data.get("gateway", {}).get("host", "0.0.0.0")

    @property
    def gateway_port(self) -> int:
        return self.data.get("gateway", {}).get("port", 8000)

    @property
    def auth_secret_key(self) -> str:
        return self.data.get("auth", {}).get("secret_key", "change-me-in-production")

    @property
    def auth_algorithm(self) -> str:
        return self.data.get("auth", {}).get("algorithm", "HS256")

    @property
    def auth_token_expire_minutes(self) -> int:
        return self.data.get("auth", {}).get("access_token_expire_minutes", 1440)

    @property
    def executor_timeout(self) -> int:
        return self.data.get("executor", {}).get("timeout_seconds", 300)

    @property
    def executor_sandbox(self) -> str:
        return self.data.get("executor", {}).get("sandbox_path", "/tmp/computehub")

    @staticmethod
    def _defaults():
        return {
            "database": {"url": "sqlite+aiosqlite:///./computehub.db"},
            "gateway": {"host": "0.0.0.0", "port": 8000, "workers": 4},
            "auth": {"secret_key": "change-me-in-production", "algorithm": "HS256", "access_token_expire_minutes": 1440},
            "executor": {"timeout_seconds": 300, "sandbox_path": "/tmp/computehub"},
        }

config = Config()
