"""Tests for every operation and the OperationFactory."""

from decimal import Decimal

import pytest

from app.exceptions import OperationError
from app.operations import (
    AbsoluteDifference, Addition, Division, IntegerDivision, Modulus,
    Multiplication, Operation, OperationFactory, Percentage, Power, Root,
    Subtraction,
)


def D(x):
    return Decimal(str(x))


@pytest.mark.parametrize(
    "op_class, a, b, expected",
    [
        (Addition, 2, 3, 5),
        (Addition, -2.5, 1.5, -1),
        (Subtraction, 10, 4, 6),
        (Subtraction, 4, 10, -6),
        (Multiplication, 3, -4, -12),
        (Multiplication, 0.5, 0.5, 0.25),
        (Division, 10, 4, 2.5),
        (Division, -9, 3, -3),
        (Power, 2, 3, 8),
        (Power, 2, -2, 0.25),
        (Power, -2, 3, -8),
        (Power, 9, 0.5, 3),
        (Power, 5, 0, 1),
        (Root, 27, 3, 3),
        (Root, 16, 2, 4),
        (Root, -8, 3, -2),
        (Root, 0, 5, 0),
        (Root, 4, -2, 0.5),
        (Modulus, 10, 3, 1),
        (Modulus, 5.5, 2, 1.5),
        (Modulus, -7, 3, -1),
        (IntegerDivision, 7, 2, 3),
        (IntegerDivision, -7, 2, -3),
        (IntegerDivision, 9.9, 3, 3),
        (Percentage, 25, 200, 12.5),
        (Percentage, 50, 50, 100),
        (Percentage, -1, 4, -25),
        (AbsoluteDifference, 3, 10, 7),
        (AbsoluteDifference, 10, 3, 7),
        (AbsoluteDifference, -5, 5, 10),
    ],
)
def test_operation_results(op_class, a, b, expected):
    result = op_class().execute(D(a), D(b))
    assert result == pytest.approx(D(expected), rel=Decimal("1e-20"))


@pytest.mark.parametrize(
    "op_class, a, b, message",
    [
        (Division, 1, 0, "Division by zero"),
        (Modulus, 1, 0, "Modulus by zero"),
        (IntegerDivision, 1, 0, "Integer division by zero"),
        (Percentage, 1, 0, "percentage of zero"),
        (Power, 0, -1, "negative power"),
        (Power, -8, 0.5, "integer exponent"),
        (Root, 9, 0, "cannot be zero"),
        (Root, -16, 2, "even root"),
        (Root, -16, 2.5, "fractional root"),
        (Root, 0, -2, "negative root of zero"),
    ],
)
def test_operation_errors(op_class, a, b, message):
    with pytest.raises(OperationError, match=message):
        op_class().execute(D(a), D(b))


def test_overflow_is_wrapped_as_operation_error():
    with pytest.raises(OperationError, match="power failed"):
        Power().execute(D("1e10"), D("1e10"))


def test_execute_accepts_plain_numbers():
    assert Addition().execute(1, 2) == Decimal(3)


def test_str_returns_class_name():
    assert str(Addition()) == "Addition"


# --- Factory ---------------------------------------------------------------
@pytest.mark.parametrize(
    "name, op_class",
    [
        ("add", Addition), ("subtract", Subtraction), ("multiply", Multiplication),
        ("divide", Division), ("power", Power), ("root", Root), ("modulus", Modulus),
        ("int_divide", IntegerDivision), ("percent", Percentage),
        ("abs_diff", AbsoluteDifference), ("  ADD  ", Addition),
    ],
)
def test_factory_creates_operations(name, op_class):
    assert isinstance(OperationFactory.create_operation(name), op_class)


def test_factory_unknown_operation():
    with pytest.raises(OperationError, match="Unknown operation"):
        OperationFactory.create_operation("sqrt")


def test_factory_lists_all_ten_operations():
    assert len(OperationFactory.available_operations()) >= 10


def test_factory_register_new_operation():
    class Maximum(Operation):
        name, symbol = "max", "max"

        def _compute(self, a, b):
            return max(a, b)

    OperationFactory.register_operation("max", Maximum)
    try:
        assert OperationFactory.create_operation("max").execute(D(2), D(9)) == 9
    finally:
        OperationFactory._operations.pop("max")


def test_factory_register_rejects_non_operation():
    with pytest.raises(TypeError):
        OperationFactory.register_operation("bad", str)
