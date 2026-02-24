"""统一日志模块"""
import logging
import os
import sys
from datetime import datetime


_initialized = False


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """初始化日志配置，只执行一次"""
    global _initialized
    if _initialized:
        return
    _initialized = True

    level = getattr(logging, log_level.upper(), logging.INFO)
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "tanwei-bot.log")

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    # file handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger("tanwei")
    root.setLevel(level)
    root.addHandler(stdout_handler)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    return logging.getLogger(f"tanwei.{name}")
