import logging
import os
from pathlib import Path


def setup_logging(level=logging.DEBUG):
    base_dir = Path(__file__).parent.parent
    log_dir = base_dir / 'logs'
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / 'bot.log'

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger(__name__)
