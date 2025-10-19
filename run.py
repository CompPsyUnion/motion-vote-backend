#!/usr/bin/env python3

from src.utils.logger import app_logger
from src.main import socket_app
import uvicorn
import os
from pathlib import Path

# 确保日志目录存在
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


if __name__ == "__main__":
    app_logger.info("=" * 80)
    app_logger.info("🚀 Starting Motion Vote API Server")
    app_logger.info("=" * 80)

    uvicorn.run(
        "src.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
