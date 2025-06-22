# util/logging_util.py
import logging
import logging.config
import os
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE  = LOG_DIR / "app.log"

_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    # -------- 格式 --------
    "formatters": {
        # 彩色终端（开发用）
        "console": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(asctime)s %(levelname)-8s "
                      "[%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        },
        # 生产环境：标准单行
        "plain": {
            "format": "%(asctime)s %(levelname)-8s "
                      "[%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        # （可选）JSON，方便 Loki / Elasticsearch 收集
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },

    # -------- Handler --------
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": LOG_LEVEL,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_FILE),
            "maxBytes": 5 * 1024 * 1024,   # 5 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "plain",
            "level": LOG_LEVEL,
        },
        # "json_file":  ← 如需 JSON 文件，把下方 root.handlers 改掉即可
    },

    # -------- Logger --------
    "root": {           # 第三方库也一起管
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },

    # 例：爬虫想要更详细的日志
    "loggers": {
        "website_crawler": {"level": os.getenv("CRAWLER_LOG_LEVEL", "DEBUG")},
        # FastAPI/Uvicorn 自带日志等级可以按需覆盖
        "uvicorn.access":  {"level": "INFO"},
    },
}

def init_logging() -> None:
    """在项目入口调用；幂等。"""
    logging.config.dictConfig(_CONFIG)
