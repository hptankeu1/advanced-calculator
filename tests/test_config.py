"""Tests for configuration loading and validation."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.calculator_config import CalculatorConfig
from app.exceptions import ConfigurationError

ENV_VARS = [
    "CALCULATOR_LOG_DIR",
    "CALCULATOR_HISTORY_DIR",
    "CALCULATOR_LOG_FILE",
    "CALCULATOR_HISTORY_FILE",
    "CALCULATOR_MAX_HISTORY_SIZE",
    "CALCULATOR_AUTO_SAVE",
    "CALCULATOR_PRECISION",
    "CALCULATOR_MAX_INPUT_VALUE",
    "CALCULATOR_DEFAULT_ENCODING",
]


@pytest.fixture
def clean_env(monkeypatch):
    """Remove calculator variables so defaults are used."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_when_env_missing(clean_env, tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    assert config.log_dir == tmp_path / "logs"
    assert config.history_dir == tmp_path / "history"
    assert config.log_file == tmp_path / "logs" / "calculator.log"
    assert config.history_file == tmp_path / "history" / "calculator_history.csv"
    assert config.max_history_size == 1000
    assert config.auto_save is True
    assert config.precision == 10
    assert config.max_input_value == Decimal("1e10")
    assert config.default_encoding == "utf-8"


def test_values_read_from_environment(clean_env, tmp_path):
    clean_env.setenv("CALCULATOR_LOG_DIR", "mylogs")
    clean_env.setenv("CALCULATOR_MAX_HISTORY_SIZE", "50")
    clean_env.setenv("CALCULATOR_AUTO_SAVE", "false")
    clean_env.setenv("CALCULATOR_PRECISION", "4")
    clean_env.setenv("CALCULATOR_MAX_INPUT_VALUE", "500")
    clean_env.setenv("CALCULATOR_DEFAULT_ENCODING", "latin-1")
    config = CalculatorConfig(base_dir=tmp_path)
    assert config.log_dir == tmp_path / "mylogs"
    assert config.max_history_size == 50
    assert config.auto_save is False
    assert config.precision == 4
    assert config.max_input_value == Decimal("500")
    assert config.default_encoding == "latin-1"


def test_explicit_arguments_override_environment(clean_env, tmp_path):
    clean_env.setenv("CALCULATOR_PRECISION", "4")
    config = CalculatorConfig(
        base_dir=tmp_path, precision=2, max_input_value=100, auto_save=False,
        max_history_size=5, default_encoding="ascii",
    )
    assert config.precision == 2
    assert config.max_input_value == Decimal("100")
    assert config.auto_save is False


def test_absolute_paths_kept(clean_env, tmp_path):
    abs_dir = tmp_path / "absolute"
    config = CalculatorConfig(base_dir=Path("/unused"), log_dir=abs_dir)
    assert config.log_dir == abs_dir


@pytest.mark.parametrize("value, expected", [("YES", True), ("1", True), ("off", False), ("No", False)])
def test_bool_parsing(clean_env, tmp_path, value, expected):
    clean_env.setenv("CALCULATOR_AUTO_SAVE", value)
    assert CalculatorConfig(base_dir=tmp_path).auto_save is expected


@pytest.mark.parametrize(
    "name, value",
    [
        ("CALCULATOR_AUTO_SAVE", "maybe"),
        ("CALCULATOR_MAX_HISTORY_SIZE", "lots"),
        ("CALCULATOR_PRECISION", "1.5"),
        ("CALCULATOR_MAX_INPUT_VALUE", "big"),
        ("CALCULATOR_MAX_HISTORY_SIZE", "0"),
        ("CALCULATOR_PRECISION", "-1"),
        ("CALCULATOR_MAX_INPUT_VALUE", "-10"),
        ("CALCULATOR_DEFAULT_ENCODING", "not-an-encoding"),
    ],
)
def test_invalid_values_raise(clean_env, tmp_path, name, value):
    clean_env.setenv(name, value)
    with pytest.raises(ConfigurationError):
        CalculatorConfig(base_dir=tmp_path)


def test_ensure_directories(clean_env, tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    config.ensure_directories()
    assert config.log_dir.is_dir()
    assert config.history_dir.is_dir()
