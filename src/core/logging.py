"""日志配置"""
import logging
import sys
from datetime import datetime


class ComputeHubFormatter(logging.Formatter):
    """自定义日志格式: [timestamp] [LEVEL] message"""

    def format(self, record):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        message = record.getMessage()
        return f"[{ts}] [{level}] {message}"


def get_logger(name: str = "computehub", level: str = "INFO", log_file: str = None):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        formatter = ComputeHubFormatter()

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件输出
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


logger = get_logger()
