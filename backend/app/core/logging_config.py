"""
统一的日志配置。

使用 Python logging 模块替代 print()，提供：
- 按日期轮转的日志文件
- 控制台输出（开发环境）
- 结构化日志格式
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from app.config import settings


def setup_logging() -> None:
    """初始化应用日志系统。"""
    # 创建日志目录
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # 清除已有的 handler，避免重复
    root_logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件 handler（按日期轮转，保留 30 天）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "livecalc.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 错误日志单独记录
    error_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "error.log",
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    root_logger.addHandler(error_file_handler)

    # 设置第三方库日志级别，避免过于冗长
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger.info("日志系统初始化完成")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger。"""
    return logging.getLogger(name)
