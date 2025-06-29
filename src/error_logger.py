import logging
from pathlib import Path
import sys


def setup_logging():
    """Sets up a robust, file-based logging system for the application."""
    log_dir = Path.home() / ".homellmcoder" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "homellmcoder.log"

    # Configure logging to write to a file and the console
    logging.basicConfig(
        level=logging.WARNING,
        force=True, # Ensure basicConfig reconfigures if called again

        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    # Suppress httpcore debug logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info("--- Application Log Started ---")

    # Capture unhandled exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical(
            "Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception
