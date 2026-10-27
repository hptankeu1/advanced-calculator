"""
Arithmetic operations and the Factory that creates them.

Every operation is a subclass of `Operation`, takes exactly two Decimal
operands and returns a Decimal. `OperationFactory` maps command names such as
"power" or "int_divide" to the class that implements them.
"""

from abc import ABC, abstractmethod
from decimal import Decimal, DecimalException
from typing import Dict, List, Type

from app.exceptions import OperationError


class Operation(ABC):
    """Base class for all two-operand operations."""

    #: command name used by the factory and the REPL
    name: str = ""
    #: short symbol used when displaying a calculation
    symbol: str = ""

    def validate_operands(self, a: Decimal, b: Decimal) -> None:
        """Hook for subclasses: raise OperationError if the operands are invalid."""

    @abstractmethod
    def _compute(self, a: Decimal, b: Decimal) -> Decimal:
        """Perform the actual calculation."""

    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Validate the operands, compute the result and wrap math errors."""
        a, b = Decimal(a), Decimal(b)
        self.validate_operands(a, b)
        try:
            return self._compute(a, b)
        except DecimalException as exc:
            raise OperationError(f"{self.name} failed: {exc.__class__.__name__}") from exc

    def __str__(self) -> str:
        return self.__class__.__name__


def _is_integer(value: Decimal) -> bool:
    return value == value.to_integral_value()


class Addition(Operation):
    name, symbol = "add", "+"

    def _compute(self, a, b):
        return a + b


class Subtraction(Operation):
    name, symbol = "subtract", "-"

    def _compute(self, a, b):
        return a - b


class Multiplication(Operation):
    name, symbol = "multiply", "*"

    def _compute(self, a, b):
        return a * b


class Division(Operation):
    name, symbol = "divide", "/"

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Division by zero is not allowed")

    def _compute(self, a, b):
        return a / b


class Power(Operation):
    """a raised to the power b. Negative exponents are allowed."""

    name, symbol = "power", "^"

    def validate_operands(self, a, b):
        if a == 0 and b < 0:
            raise OperationError("Zero cannot be raised to a negative power")
        if a < 0 and not _is_integer(b):
            raise OperationError("A negative base requires an integer exponent")

    def _compute(self, a, b):
        if _is_integer(b):
            return a ** int(b)
        return a ** b


class Root(Operation):
    """The b-th root of a. Odd roots of negative numbers are supported."""

    name, symbol = "root", "√"

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Root degree cannot be zero")
        if a == 0 and b < 0:
            raise OperationError("Cannot take a negative root of zero")
        if a < 0:
            if not _is_integer(b):
                raise OperationError("Cannot take a fractional root of a negative number")
            if int(b) % 2 == 0:
                raise OperationError("Cannot take an even root of a negative number")

    def _compute(self, a, b):
        if a == 0:
            return Decimal(0)
        result = abs(a) ** (Decimal(1) / b)
        return -result if a < 0 else result


class Modulus(Operation):
    """Remainder of a / b. The sign of the result follows the dividend a."""

    name, symbol = "modulus", "%"

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Modulus by zero is not allowed")

    def _compute(self, a, b):
        return a % b


class IntegerDivision(Operation):
    """Quotient of a / b with the fractional part discarded (truncated toward zero)."""

    name, symbol = "int_divide", "//"

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Integer division by zero is not allowed")

    def _compute(self, a, b):
        return a // b


class Percentage(Operation):
    """What percentage a is of b: (a / b) * 100."""

    name, symbol = "percent", "%of"

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Cannot calculate a percentage of zero")

    def _compute(self, a, b):
        return (a / b) * 100


class AbsoluteDifference(Operation):
    name, symbol = "abs_diff", "|-|"

    def _compute(self, a, b):
        return abs(a - b)


class OperationFactory:
    """Factory that creates operation instances from their command names."""

    _operations: Dict[str, Type[Operation]] = {
        cls.name: cls
        for cls in (
            Addition, Subtraction, Multiplication, Division, Power, Root,
            Modulus, IntegerDivision, Percentage, AbsoluteDifference,
        )
    }

    @classmethod
    def register_operation(cls, name: str, operation_class: Type[Operation]) -> None:
        """Add a new operation type so it can be created by name."""
        if not (isinstance(operation_class, type) and issubclass(operation_class, Operation)):
            raise TypeError("Operation class must inherit from Operation")
        cls._operations[name.lower()] = operation_class

    @classmethod
    def create_operation(cls, name: str) -> Operation:
        """Return a new instance of the operation called `name`."""
        operation_class = cls._operations.get(str(name).strip().lower())
        if operation_class is None:
            raise OperationError(
                f"Unknown operation: '{name}'. "
                f"Available: {', '.join(cls.available_operations())}"
            )
        return operation_class()

    @classmethod
    def available_operations(cls) -> List[str]:
        return list(cls._operations)
