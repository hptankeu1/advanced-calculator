"""Validation of user-supplied numbers."""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.calculator_config import CalculatorConfig
from app.exceptions import ValidationError


class InputValidator:
    """Turns raw input into a Decimal, or raises ValidationError explaining why not."""

    @staticmethod
    def validate_number(value: Any, config: CalculatorConfig) -> Decimal:
        if isinstance(value, bool):
            raise ValidationError("Booleans are not valid numbers")

        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValidationError("Input cannot be empty")

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"Invalid number: '{value}'") from None

        if not number.is_finite():
            raise ValidationError(f"Number must be finite, got '{value}'")

        if abs(number) > config.max_input_value:
            raise ValidationError(
                f"Value {value} exceeds the maximum allowed magnitude "
                f"({config.max_input_value})"
            )
        return number
