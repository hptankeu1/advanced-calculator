"""Tests for InputValidator."""

from decimal import Decimal

import pytest

from app.calculator_config import CalculatorConfig
from app.exceptions import ValidationError
from app.input_validators import InputValidator


@pytest.fixture
def config(tmp_path):
    return CalculatorConfig(base_dir=tmp_path, max_input_value=1000)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("42", Decimal("42")),
        ("  -3.5 ", Decimal("-3.5")),
        (7, Decimal("7")),
        (2.5, Decimal("2.5")),
        (Decimal("1000"), Decimal("1000")),
        ("1e2", Decimal("100")),
    ],
)
def test_valid_numbers(config, value, expected):
    assert InputValidator.validate_number(value, config) == expected


@pytest.mark.parametrize(
    "value, message",
    [
        ("", "cannot be empty"),
        ("   ", "cannot be empty"),
        ("abc", "Invalid number"),
        ("1.2.3", "Invalid number"),
        (None, "Invalid number"),
        ([1], "Invalid number"),
        (True, "Booleans"),
        ("nan", "finite"),
        ("inf", "finite"),
        ("1001", "exceeds"),
        ("-5000", "exceeds"),
    ],
)
def test_invalid_numbers(config, value, message):
    with pytest.raises(ValidationError, match=message):
        InputValidator.validate_number(value, config)
