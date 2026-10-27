"""
Logger class: configures Python's logging module for the calculator.

All calculator modules log through the "calculator" logger, which writes to
the file named by CALCULATOR_LOG_FILE (see calculator_config.py).
"""

import logging
from pathlib import Path
from typing import Union

LOGGER_NAME = "calculator"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class Logger:
    """Sets up and hands out the application logger."""

    @staticmethod
    def setup(log_file: Union[str, Path], encoding: str = "utf-8",
              level: int = logging.INFO) -> logging.Logger:
        """
        Configure the calculator logger to write to `log_file`.

        Safe to call more than once: previous handlers are closed and replaced,
        so a new configuration (e.g. in tests) never writes to an old file.
        """
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger(LOGGER_NAME)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

        file_handler = logging.FileHandler(log_file, encoding=encoding)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)
        logger.setLevel(level)
        logger.propagate = True  # let pytest's caplog see the records
        logger.info("Logging initialized at %s", log_file)
        return logger

    @staticmethod
    def get_logger(name: str = "") -> logging.Logger:
        """Return the calculator logger, or a child of it (e.g. 'calculator.history')."""
        return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)
