"""Shared fixtures: every test gets its own temporary log and history files."""

import pytest

from app.calculator import Calculator
from app.calculator_config import CalculatorConfig


@pytest.fixture
def config(tmp_path):
    return CalculatorConfig(
        base_dir=tmp_path,
        log_dir=tmp_path / "logs",
        history_dir=tmp_path / "history",
        log_file="calculator.log",
        history_file="calculator_history.csv",
        max_history_size=100,
        auto_save=False,
        precision=10,
        max_input_value=1e10,
        default_encoding="utf-8",
    )


@pytest.fixture
def calculator(config):
    return Calculator(config)
