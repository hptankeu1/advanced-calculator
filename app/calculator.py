"""
The Calculator: performs operations, keeps history and notifies observers.

Design patterns used here:
- Factory  (OperationFactory) creates the operation for a command name.
- Memento  (CalculatorMemento) snapshots history so it can be undone/redone.
- Observer (HistoryObserver) lets logging and auto-save react to new calculations.
"""

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, List, Optional, Union

import pandas as pd

from app.calculation import Calculation
from app.calculator_config import CalculatorConfig
from app.calculator_memento import CalculatorMemento
from app.exceptions import HistoryError, OperationError, ValidationError
from app.history import HistoryObserver
from app.input_validators import InputValidator
from app.logger import Logger
from app.operations import Operation, OperationFactory

CSV_COLUMNS = ["operation", "operand1", "operand2", "result", "timestamp"]


class Calculator:
    """Calculator with history, undo/redo, observers and CSV persistence."""

    def __init__(self, config: Optional[CalculatorConfig] = None, load_existing: bool = True):
        self.config = config or CalculatorConfig()
        self.config.ensure_directories()
        self.logger = Logger.setup(self.config.log_file, self.config.default_encoding)

        self.history: List[Calculation] = []
        self.undo_stack: List[CalculatorMemento] = []
        self.redo_stack: List[CalculatorMemento] = []
        self.observers: List[HistoryObserver] = []
        self.operation_strategy: Optional[Operation] = None

        if load_existing and self.config.history_file.exists():
            try:
                self.load_history()
            except HistoryError as exc:
                self.logger.warning("Could not load existing history: %s", exc)

        self.logger.info("Calculator initialized")

    # ------------------------------------------------------------------ observers
    def add_observer(self, observer: HistoryObserver) -> None:
        self.observers.append(observer)
        self.logger.info("Added observer: %s", observer.__class__.__name__)

    def remove_observer(self, observer: HistoryObserver) -> None:
        if observer in self.observers:
            self.observers.remove(observer)
            self.logger.info("Removed observer: %s", observer.__class__.__name__)

    def notify_observers(self, calculation: Calculation) -> None:
        for observer in self.observers:
            observer.update(calculation)

    # ---------------------------------------------------------------- operations
    def set_operation(self, operation: Union[Operation, str]) -> None:
        """Choose the operation to use, either an instance or a command name."""
        if isinstance(operation, str):
            operation = OperationFactory.create_operation(operation)
        self.operation_strategy = operation
        self.logger.info("Set operation: %s", operation.name)

    def perform_operation(self, a: Any, b: Any) -> Decimal:
        """Validate inputs, run the current operation and record the result."""
        if self.operation_strategy is None:
            raise OperationError("No operation set")
        try:
            num_a = InputValidator.validate_number(a, self.config)
            num_b = InputValidator.validate_number(b, self.config)
            result = self._round(self.operation_strategy.execute(num_a, num_b))
        except (ValidationError, OperationError) as exc:
            self.logger.error("Calculation failed: %s", exc)
            raise

        calculation = Calculation(self.operation_strategy.name, num_a, num_b, result)
        self._save_state()
        self.history.append(calculation)
        self._trim_history()
        self.notify_observers(calculation)
        return result

    def calculate(self, operation_name: str, a: Any, b: Any) -> Decimal:
        """Convenience: set the operation by name and perform it in one call."""
        self.set_operation(operation_name)
        return self.perform_operation(a, b)

    def _round(self, value: Decimal) -> Decimal:
        """Round to CALCULATOR_PRECISION decimal places when possible."""
        try:
            return value.quantize(Decimal(1).scaleb(-self.config.precision))
        except InvalidOperation:
            # Too many digits to quantize (very large numbers): keep as is.
            return value

    def _trim_history(self) -> None:
        overflow = len(self.history) - self.config.max_history_size
        if overflow > 0:
            del self.history[:overflow]
            self.logger.warning("History limit reached; removed %d oldest entries", overflow)

    # ------------------------------------------------------------- undo / redo
    def _save_state(self) -> None:
        """Push a snapshot onto the undo stack; any new change clears redo."""
        self.undo_stack.append(CalculatorMemento(self.history))
        self.redo_stack.clear()

    def undo(self) -> bool:
        """Restore the history to before the last change. Returns False if nothing to undo."""
        if not self.undo_stack:
            return False
        self.redo_stack.append(CalculatorMemento(self.history))
        self.history = list(self.undo_stack.pop().history)
        self.logger.info("Undo performed")
        return True

    def redo(self) -> bool:
        """Re-apply the last undone change. Returns False if nothing to redo."""
        if not self.redo_stack:
            return False
        self.undo_stack.append(CalculatorMemento(self.history))
        self.history = list(self.redo_stack.pop().history)
        self.logger.info("Redo performed")
        return True

    # ------------------------------------------------------------------ history
    def clear_history(self) -> None:
        """Remove all calculations (can be undone)."""
        self._save_state()
        self.history.clear()
        self.logger.info("History cleared")

    def show_history(self) -> List[str]:
        return [str(calc) for calc in self.history]

    def get_history_dataframe(self) -> pd.DataFrame:
        """Return the history as a pandas DataFrame."""
        return pd.DataFrame([calc.to_dict() for calc in self.history], columns=CSV_COLUMNS)

    def save_history(self, path: Optional[Union[str, Path]] = None) -> Path:
        """Write the history to CSV using pandas. Returns the file path."""
        path = Path(path) if path else self.config.history_file
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.get_history_dataframe().to_csv(
                path, index=False, encoding=self.config.default_encoding
            )
        except OSError as exc:
            self.logger.error("Failed to save history: %s", exc)
            raise HistoryError(f"Failed to save history to {path}: {exc}") from exc
        self.logger.info("History saved to %s (%d entries)", path, len(self.history))
        return path

    def load_history(self, path: Optional[Union[str, Path]] = None) -> int:
        """Replace the history with the contents of a CSV file. Returns the number loaded."""
        path = Path(path) if path else self.config.history_file
        if not path.exists():
            raise HistoryError(f"History file not found: {path}")
        try:
            df = pd.read_csv(path, dtype=str, encoding=self.config.default_encoding)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=CSV_COLUMNS)
        except (pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
            self.logger.error("Failed to read history file: %s", exc)
            raise HistoryError(f"Could not read history file {path}: {exc}") from exc

        missing = [col for col in CSV_COLUMNS if col not in df.columns]
        if missing:
            raise HistoryError(f"History file is missing columns: {', '.join(missing)}")

        loaded = [Calculation.from_dict(row) for row in df.to_dict("records")]

        self._save_state()
        self.history = loaded
        self._trim_history()
        self.logger.info("Loaded %d calculations from %s", len(self.history), path)
        return len(self.history)
