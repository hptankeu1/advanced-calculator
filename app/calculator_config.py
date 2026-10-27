"""
Configuration management.

Settings are read from environment variables, which python-dotenv loads from
the .env file in the project root. Every setting has a default, and values
are validated when the configuration is created.
"""

import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.exceptions import ConfigurationError

# Project root = folder that contains the app/ package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DEFAULTS = {
    "CALCULATOR_LOG_DIR": "logs",
    "CALCULATOR_HISTORY_DIR": "history",
    "CALCULATOR_LOG_FILE": "calculator.log",
    "CALCULATOR_HISTORY_FILE": "calculator_history.csv",
    "CALCULATOR_MAX_HISTORY_SIZE": "1000",
    "CALCULATOR_AUTO_SAVE": "true",
    "CALCULATOR_PRECISION": "10",
    "CALCULATOR_MAX_INPUT_VALUE": "1e10",
    "CALCULATOR_DEFAULT_ENCODING": "utf-8",
}

TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off"}


def _env(name: str) -> str:
    """Return an environment variable, falling back to its default."""
    return os.getenv(name, DEFAULTS[name]).strip()


def _parse_bool(name: str, raw: str) -> bool:
    value = raw.lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name} must be true or false, got '{raw}'")


def _parse_int(name: str, raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be an integer, got '{raw}'") from None


def _parse_decimal(name: str, raw: str) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ConfigurationError(f"{name} must be a number, got '{raw}'") from None


def _resolve(base: Path, path: str) -> Path:
    """Make a path absolute, relative to `base` when it is not already."""
    p = Path(path)
    return p if p.is_absolute() else base / p


@dataclass
class CalculatorConfig:
    """
    All calculator settings.

    Any argument left as None is read from the environment (or its default).
    """

    base_dir: Optional[Path] = None
    log_dir: Optional[Path] = None
    history_dir: Optional[Path] = None
    log_file: Optional[Path] = None
    history_file: Optional[Path] = None
    max_history_size: Optional[int] = None
    auto_save: Optional[bool] = None
    precision: Optional[int] = None
    max_input_value: Optional[Decimal] = None
    default_encoding: Optional[str] = None
    _validated: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        self.base_dir = Path(self.base_dir) if self.base_dir else PROJECT_ROOT

        self.log_dir = _resolve(self.base_dir, str(self.log_dir or _env("CALCULATOR_LOG_DIR")))
        self.history_dir = _resolve(
            self.base_dir, str(self.history_dir or _env("CALCULATOR_HISTORY_DIR"))
        )
        self.log_file = _resolve(self.log_dir, str(self.log_file or _env("CALCULATOR_LOG_FILE")))
        self.history_file = _resolve(
            self.history_dir, str(self.history_file or _env("CALCULATOR_HISTORY_FILE"))
        )

        if self.max_history_size is None:
            self.max_history_size = _parse_int(
                "CALCULATOR_MAX_HISTORY_SIZE", _env("CALCULATOR_MAX_HISTORY_SIZE")
            )
        if self.auto_save is None:
            self.auto_save = _parse_bool("CALCULATOR_AUTO_SAVE", _env("CALCULATOR_AUTO_SAVE"))
        if self.precision is None:
            self.precision = _parse_int("CALCULATOR_PRECISION", _env("CALCULATOR_PRECISION"))
        if self.max_input_value is None:
            self.max_input_value = _parse_decimal(
                "CALCULATOR_MAX_INPUT_VALUE", _env("CALCULATOR_MAX_INPUT_VALUE")
            )
        else:
            self.max_input_value = Decimal(str(self.max_input_value))
        if self.default_encoding is None:
            self.default_encoding = _env("CALCULATOR_DEFAULT_ENCODING")

        self.validate()

    def validate(self) -> None:
        """Check that every setting is within an acceptable range."""
        if self.max_history_size <= 0:
            raise ConfigurationError("CALCULATOR_MAX_HISTORY_SIZE must be positive")
        if self.precision < 0:
            raise ConfigurationError("CALCULATOR_PRECISION must be zero or positive")
        if self.max_input_value <= 0:
            raise ConfigurationError("CALCULATOR_MAX_INPUT_VALUE must be positive")
        try:
            "test".encode(self.default_encoding)
        except LookupError:
            raise ConfigurationError(
                f"Unknown encoding: {self.default_encoding}"
            ) from None
        self._validated = True

    def ensure_directories(self) -> None:
        """Create the log and history directories if they do not exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
