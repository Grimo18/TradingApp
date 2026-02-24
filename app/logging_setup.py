"""
Centralized logging configuration for the trading application.

Configures dual output: file-based persistent logging for auditing and
console output for real-time monitoring. All timestamps are recorded for
trade reconstruction and compliance purposes.
"""

import logging
import os
from pathlib import Path


def configure_logging(log_dir="logs", log_file="app.log"):
    """
    Initialize application-wide logging to file and console.
    
    This function sets up dual handlers:
    - FileHandler: Persistent audit trail of all operations (required for compliance)
    - StreamHandler: Real-time console output for live monitoring
    
    Args:
        log_dir (str): Directory where log files are stored. Created if non-existent.
        log_file (str): Filename for the main application log.
    
    Returns:
        None: Modifies the root logger in-place.
    """

    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    # Configure root logger with ISO 8601 timestamps for compliance
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),  # Persistent audit trail
            logging.StreamHandler(),  # Real-time console output
        ],
    )
