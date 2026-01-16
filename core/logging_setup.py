import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import sys
import os

# Use executable path for frozen apps or script path
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(sys.argv[0]).parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

handler = RotatingFileHandler(
    LOG_DIR / "app.log",
    maxBytes=1_000_000,
    backupCount=5,
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[handler, logging.StreamHandler()]
)

def get_logger(name):
    return logging.getLogger(name)

# Startup diagnostics
root = get_logger("startup")
root.info(f"OS: {platform.platform()}")
root.info(f"Python: {sys.version}")
