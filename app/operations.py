"""
Arithmetic operations and the Factory that creates them.

Every operation is a subclass of `Operation`, takes exactly two Decimal
operands and returns a Decimal. Each class registers itself with the
`@OperationFactory.register(...)` decorator, which records its command name
and help text. The REPL builds its help menu from that registry, so adding a
new decorated class makes it appear in `help` with no other changes.
"""

from abc import ABC, abstractmethod
from decimal import Decimal, DecimalException
from typing import Callable, Dict, List, Type

from app.exceptions import OperationError


class Operation(ABC):
    """Base class for all two-operand operations."""

    #: command name used by the factory and the REPL
    name: str = ""
    #: short symbol used when displaying a calculation
    symbol: str = ""
    #: one-line description shown in the help menu
    description: str = ""

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


class OperationFactory:
    """Factory that creates operation instances from their command names."""

    _operations: Dict[str, Type[Operation]] = {}

    @classmethod
    def register(cls, name: str, description: str = "", symbol: str = "") -> Callable:
        """
        Class decorator that registers an operation with the factory.

            @OperationFactory.register("max", "the larger of a and b")
            class Maximum(Operation): ...
        """

        def decorator(operation_class: Type[Operation]) -> Type[Operation]:
            operation_class.name = name.lower()
            if description:
                operation_class.description = description
            if symbol:
                operation_class.symbol = symbol
            cls.register_operation(name, operation_class)
            return operation_class

        return decorator

    @classmethod
    def register_operation(cls, name: str, operation_class: Type[Operation]) -> None:
        """Add a new operation type so it can be created by name."""
        if not (isinstance(operation_class, type) and issubclass(operation_class, Operation)):
            raise TypeError("Operation class must inherit from Operation")
        cls._operations[name.lower()] = operation_class

    @classmethod
    def unregister_operation(cls, name: str) -> None:
        """Remove an operation (mainly useful in tests and plugins)."""
        cls._operations.pop(name.lower(), None)

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

    @classmethod
    def describe_operations(cls) -> Dict[str, str]:
        """Return {command name: description} for every registered operation."""
        return {name: op.description for name, op in cls._operations.items()}


def _is_integer(value: Decimal) -> bool:
    return value == value.to_integral_value()


@OperationFactory.register("add", "a + b", "+")
class Addition(Operation):
    def _compute(self, a, b):
        return a + b


@OperationFactory.register("subtract", "a - b", "-")
class Subtraction(Operation):
    def _compute(self, a, b):
        return a - b


@OperationFactory.register("multiply", "a * b", "*")
class Multiplication(Operation):
    def _compute(self, a, b):
        return a * b


@OperationFactory.register("divide", "a / b", "/")
class Division(Operation):
    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Division by zero is not allowed")

    def _compute(self, a, b):
        return a / b


@OperationFactory.register("power", "a raised to the power b", "^")
class Power(Operation):
    """Negative exponents are allowed."""

    def validate_operands(self, a, b):
        if a == 0 and b < 0:
            raise OperationError("Zero cannot be raised to a negative power")
        if a < 0 and not _is_integer(b):
            raise OperationError("A negative base requires an integer exponent")

    def _compute(self, a, b):
        if _is_integer(b):
            return a ** int(b)
        return a ** b


@OperationFactory.register("root", "the b-th root of a", "√")
class Root(Operation):
    """Odd roots of negative numbers are supported."""

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


@OperationFactory.register("modulus", "remainder of a / b", "%")
class Modulus(Operation):
    """The sign of the result follows the dividend a."""

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Modulus by zero is not allowed")

    def _compute(self, a, b):
        return a % b


@OperationFactory.register("int_divide", "a / b with the fractional part discarded", "//")
class IntegerDivision(Operation):
    """Truncates toward zero."""

    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Integer division by zero is not allowed")

    def _compute(self, a, b):
        return a // b


@OperationFactory.register("percent", "(a / b) * 100", "%of")
class Percentage(Operation):
    def validate_operands(self, a, b):
        if b == 0:
            raise OperationError("Cannot calculate a percentage of zero")

    def _compute(self, a, b):
        return (a / b) * 100


@OperationFactory.register("abs_diff", "|a - b|", "|-|")
class AbsoluteDifference(Operation):
    def _compute(self, a, b):
        return abs(a - b)
