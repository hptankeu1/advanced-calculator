"""The Calculation record: one operation, its two operands, result and time."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from app.exceptions import HistoryError


def format_decimal(value: Decimal) -> str:
    """Render a Decimal without exponent noise or trailing zeros (e.g. 2.50 -> 2.5)."""
    if value == value.to_integral_value() and abs(value) < Decimal("1e28"):
        return str(value.quantize(Decimal(1)))
    text = format(value.normalize(), "f")
    return text


@dataclass
class Calculation:
    """An immutable-by-convention record of a completed calculation."""

    operation: str
    operand1: Decimal
    operand2: Decimal
    result: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return (
            f"{self.operation}({format_decimal(self.operand1)}, "
            f"{format_decimal(self.operand2)}) = {format_decimal(self.result)}"
        )

    def to_dict(self) -> Dict[str, str]:
        """Serialize to plain strings (used for CSV and mementos)."""
        return {
            "operation": self.operation,
            "operand1": str(self.operand1),
            "operand2": str(self.operand2),
            "result": str(self.result),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Calculation":
        """Rebuild a Calculation from a dict produced by `to_dict` (or a CSV row)."""
        try:
            return cls(
                operation=str(data["operation"]),
                operand1=Decimal(str(data["operand1"])),
                operand2=Decimal(str(data["operand2"])),
                result=Decimal(str(data["result"])),
                timestamp=datetime.fromisoformat(str(data["timestamp"])),
            )
        except KeyError as exc:
            raise HistoryError(f"Missing field in calculation data: {exc}") from exc
        except (InvalidOperation, ValueError) as exc:
            raise HistoryError(f"Invalid calculation data: {data}") from exc
