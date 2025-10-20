"""
日志系统配置
提供统一的日志记录功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# ANSI 颜色码


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    FORMATS = {
        logging.DEBUG: f"{Colors.CYAN}%(levelname)-8s{Colors.RESET} | %(asctime)s | %(name)s | %(message)s",
        logging.INFO: f"{Colors.GREEN}%(levelname)-8s{Colors.RESET} | %(asctime)s | %(name)s | %(message)s",
        logging.WARNING: f"{Colors.YELLOW}%(levelname)-8s{Colors.RESET} | %(asctime)s | %(name)s | %(message)s",
        logging.ERROR: f"{Colors.RED}%(levelname)-8s{Colors.RESET} | %(asctime)s | %(name)s | %(message)s",
        logging.CRITICAL: f"{Colors.MAGENTA}{Colors.BOLD}%(levelname)-8s{Colors.RESET} | %(asctime)s | %(name)s | %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置并返回一个配置好的logger

    Args:
        name: logger名称
        level: 日志级别
        log_file: 日志文件路径（可选）

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 防止重复添加handler
    if logger.handlers:
        return logger

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(levelname)-8s | %(asctime)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# 预定义的logger
app_logger = setup_logger('app', level=logging.INFO)
websocket_logger = setup_logger(
    'websocket', level=logging.DEBUG, log_file='logs/websocket.log')
api_logger = setup_logger('api', level=logging.INFO)
db_logger = setup_logger('database', level=logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取或创建logger

    Args:
        name: logger名称

    Returns:
        Logger实例
    """
    return setup_logger(name)
