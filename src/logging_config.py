import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "errors.log")


def setup_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("rennes_traffic")
    logger.setLevel(logging.ERROR)

    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.propagate = False

    return logger