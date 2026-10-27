"""Tests for the Calculation record and number formatting."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.calculation import Calculation, format_decimal
from app.exceptions import HistoryError


@pytest.fixture
def calc():
    return Calculation(
        operation="add",
        operand1=Decimal("2"),
        operand2=Decimal("3.5"),
        result=Decimal("5.5"),
        timestamp=datetime(2026, 10, 26, 12, 0, 0),
    )


def test_str(calc):
    assert str(calc) == "add(2, 3.5) = 5.5"


def test_timestamp_defaults_to_now():
    c = Calculation("add", Decimal(1), Decimal(1), Decimal(2))
    assert isinstance(c.timestamp, datetime)


def test_round_trip(calc):
    data = calc.to_dict()
    assert data == {
        "operation": "add",
        "operand1": "2",
        "operand2": "3.5",
        "result": "5.5",
        "timestamp": "2026-10-26T12:00:00",
    }
    assert Calculation.from_dict(data) == calc


def test_from_dict_missing_field():
    with pytest.raises(HistoryError, match="Missing field"):
        Calculation.from_dict({"operation": "add"})


@pytest.mark.parametrize(
    "bad",
    [
        {"operation": "add", "operand1": "x", "operand2": "1", "result": "1", "timestamp": "2026-01-01"},
        {"operation": "add", "operand1": "1", "operand2": "1", "result": "2", "timestamp": "not a date"},
        {"operation": "add", "operand1": "nan", "operand2": "1", "result": "2", "timestamp": "2026-01-01"},
    ],
)
def test_from_dict_invalid_values(bad):
    with pytest.raises(HistoryError, match="Invalid calculation data"):
        Calculation.from_dict(bad)


@pytest.mark.parametrize(
    "value, expected",
    [
        (Decimal("5"), "5"),
        (Decimal("-0"), "0"),
        (Decimal("5.000"), "5"),
        (Decimal("2.50"), "2.5"),
        (Decimal("-0.125"), "-0.125"),
        (Decimal("1E+3"), "1000"),
        (Decimal("1E+30"), "1000000000000000000000000000000"),
    ],
)
def test_format_decimal(value, expected):
    assert format_decimal(value) == expected
