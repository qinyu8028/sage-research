import logging
import os
import sys
from datetime import datetime


def setup_logging(log_dir: str = "logs", level: str = "DEBUG", enable_display: bool = True) -> None:
    logger = logging.getLogger("sage_research")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return

    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"sage_research_{timestamp}.log")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"))

    logger.addHandler(stderr_handler)
    logger.addHandler(file_handler)

    if enable_display:
        display_logger = logging.getLogger("sage_research.display")
        display_logger.propagate = False

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(logging.Formatter("%(message)s"))

        display_log_file = os.path.join(log_dir, f"display_{timestamp}.log")
        display_file_handler = logging.FileHandler(display_log_file, encoding="utf-8")
        display_file_handler.setLevel(logging.INFO)
        display_file_handler.setFormatter(logging.Formatter("%(message)s"))

        display_logger.addHandler(stdout_handler)
        display_logger.addHandler(display_file_handler)