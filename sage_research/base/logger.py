import logging
import os
import sys
from datetime import datetime


def setup_logging(log_dir: str = "logs", level: str = "DEBUG") -> None:
    logger = logging.getLogger("sage_research")
    logger.setLevel(logging.DEBUG)

    # already set up
    if logger.handlers:
        return

    os.makedirs(log_dir, exist_ok=True)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.INFO)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"sage_research_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    simple_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    stream_handler.setFormatter(simple_fmt)

    debug_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(debug_fmt)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)