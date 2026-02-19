"""Setup logging applicativo."""

import logging
import os
from pathlib import Path


def configure_logging(log_dir="logs", log_file="app.log"):
    """Configura logging su file e console."""

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
