"""
Observer pattern: observers that react whenever a new calculation is made.

- LoggingObserver logs the operation, operands and result.
- AutoSaveObserver saves the full history to CSV (via pandas) when auto-save is on.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.calculation import Calculation, format_decimal
from app.exceptions import HistoryError
from app.logger import Logger

if TYPE_CHECKING:  # pragma: no cover - import only for type hints
    from app.calculator import Calculator


class HistoryObserver(ABC):
    """Interface for objects notified about new calculations."""

    @abstractmethod
    def update(self, calculation: Calculation) -> None:
        """Called by the Calculator after each successful calculation."""


class LoggingObserver(HistoryObserver):
    """Writes every calculation to the log file."""

    def __init__(self):
        self.logger = Logger.get_logger("observer")

    def update(self, calculation: Calculation) -> None:
        if calculation is None:
            raise AttributeError("Calculation cannot be None")
        self.logger.info(
            "Calculation performed: %s (%s, %s) = %s",
            calculation.operation,
            format_decimal(calculation.operand1),
            format_decimal(calculation.operand2),
            format_decimal(calculation.result),
        )


class AutoSaveObserver(HistoryObserver):
    """Saves the calculator's history to CSV after each calculation."""

    def __init__(self, calculator: "Calculator"):
        if not hasattr(calculator, "config") or not hasattr(calculator, "save_history"):
            raise TypeError("AutoSaveObserver requires a Calculator instance")
        self.calculator = calculator
        self.logger = Logger.get_logger("observer")

    def update(self, calculation: Calculation) -> None:
        if calculation is None:
            raise AttributeError("Calculation cannot be None")
        if not self.calculator.config.auto_save:
            return
        try:
            self.calculator.save_history()
            self.logger.info("History auto-saved")
        except HistoryError as exc:
            # Auto-save must never crash a calculation; log and continue.
            self.logger.error("Auto-save failed: %s", exc)
