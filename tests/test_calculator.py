"""Tests for the Calculator: operations, undo/redo, observers and persistence."""

from decimal import Decimal

import pandas as pd
import pytest

from app.calculator import Calculator
from app.calculator_config import CalculatorConfig
from app.exceptions import HistoryError, OperationError, ValidationError
from app.history import AutoSaveObserver, HistoryObserver, LoggingObserver
from app.operations import Addition


# ------------------------------------------------------------------ operations
@pytest.mark.parametrize(
    "op, a, b, expected",
    [
        ("add", "2", "3", "5"),
        ("subtract", "2", "3", "-1"),
        ("multiply", "2.5", "4", "10"),
        ("divide", "1", "3", "0.3333333333"),
        ("power", "2", "-1", "0.5"),
        ("root", "81", "4", "3"),
        ("modulus", "17", "5", "2"),
        ("int_divide", "17", "5", "3"),
        ("percent", "30", "120", "25"),
        ("abs_diff", "-4", "6", "10"),
    ],
)
def test_calculate_all_operations(calculator, op, a, b, expected):
    assert calculator.calculate(op, a, b) == Decimal(expected)
    assert calculator.history[-1].operation == op


def test_precision_applied(config):
    config.precision = 2
    calc = Calculator(config)
    assert calc.calculate("divide", 2, 3) == Decimal("0.67")


def test_huge_result_not_quantized(config):
    config.max_input_value = Decimal("1e30")
    calc = Calculator(config)
    result = calc.calculate("power", "1e20", "2")
    assert result == Decimal("1e40")


def test_set_operation_with_instance(calculator):
    calculator.set_operation(Addition())
    assert calculator.perform_operation(1, 1) == 2


def test_perform_without_operation(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(1, 2)


def test_invalid_input_raises_and_not_recorded(calculator):
    with pytest.raises(ValidationError):
        calculator.calculate("add", "abc", 1)
    assert calculator.history == []


def test_input_above_max_rejected(calculator):
    with pytest.raises(ValidationError, match="exceeds"):
        calculator.calculate("add", "1e11", 1)


def test_operation_error_not_recorded(calculator):
    with pytest.raises(OperationError):
        calculator.calculate("divide", 1, 0)
    assert calculator.history == []
    assert calculator.undo_stack == []


def test_unknown_operation(calculator):
    with pytest.raises(OperationError, match="Unknown operation"):
        calculator.calculate("cube", 1, 2)


def test_history_size_limit(config):
    config.max_history_size = 3
    calc = Calculator(config)
    for i in range(5):
        calc.calculate("add", i, 0)
    assert [c.operand1 for c in calc.history] == [2, 3, 4]


# ----------------------------------------------------------------- undo / redo
def test_undo_redo(calculator):
    calculator.calculate("add", 1, 1)
    calculator.calculate("add", 2, 2)
    assert calculator.undo() is True
    assert len(calculator.history) == 1
    assert calculator.undo() is True
    assert calculator.history == []
    assert calculator.undo() is False
    assert calculator.redo() is True
    assert len(calculator.history) == 1
    assert calculator.redo() is True
    assert calculator.history[-1].result == 4
    assert calculator.redo() is False


def test_new_calculation_clears_redo(calculator):
    calculator.calculate("add", 1, 1)
    calculator.undo()
    calculator.calculate("multiply", 3, 3)
    assert calculator.redo() is False
    assert calculator.show_history() == ["multiply(3, 3) = 9"]


def test_clear_history_is_undoable(calculator):
    calculator.calculate("add", 1, 1)
    calculator.clear_history()
    assert calculator.history == []
    calculator.undo()
    assert calculator.show_history() == ["add(1, 1) = 2"]


def test_memento_is_a_snapshot(calculator):
    calculator.calculate("add", 1, 1)
    snapshot = calculator.undo_stack[-1]
    calculator.calculate("add", 2, 2)
    assert snapshot.history == []


# ------------------------------------------------------------------- observers
class RecordingObserver(HistoryObserver):
    def __init__(self):
        self.seen = []

    def update(self, calculation):
        self.seen.append(calculation)


def test_observers_notified(calculator):
    observer = RecordingObserver()
    calculator.add_observer(observer)
    calculator.calculate("add", 1, 2)
    assert len(observer.seen) == 1
    calculator.remove_observer(observer)
    calculator.remove_observer(observer)  # removing twice is harmless
    calculator.calculate("add", 1, 2)
    assert len(observer.seen) == 1


def test_logging_observer_writes_log(calculator, config):
    calculator.add_observer(LoggingObserver())
    calculator.calculate("power", 2, 10)
    log_text = config.log_file.read_text()
    assert "Calculation performed: power (2, 10) = 1024" in log_text


def test_logging_observer_rejects_none():
    with pytest.raises(AttributeError):
        LoggingObserver().update(None)


def test_auto_save_observer_saves_csv(config):
    config.auto_save = True
    calc = Calculator(config)
    calc.add_observer(AutoSaveObserver(calc))
    calc.calculate("add", 2, 3)
    df = pd.read_csv(config.history_file)
    assert list(df.columns) == ["operation", "operand1", "operand2", "result", "timestamp"]
    assert df.iloc[0]["result"] == 5


def test_auto_save_disabled(calculator, config):
    calculator.add_observer(AutoSaveObserver(calculator))
    calculator.calculate("add", 2, 3)
    assert not config.history_file.exists()


def test_auto_save_failure_is_logged_not_raised(config, monkeypatch):
    config.auto_save = True
    calc = Calculator(config)
    calc.add_observer(AutoSaveObserver(calc))

    def broken_save(*args, **kwargs):
        raise HistoryError("disk full")

    monkeypatch.setattr(calc, "save_history", broken_save)
    calc.calculate("add", 1, 1)  # must not raise
    assert "Auto-save failed: disk full" in config.log_file.read_text()


def test_auto_save_observer_requires_calculator():
    with pytest.raises(TypeError):
        AutoSaveObserver(object())


def test_auto_save_observer_rejects_none(calculator):
    with pytest.raises(AttributeError):
        AutoSaveObserver(calculator).update(None)


# ----------------------------------------------------------------- persistence
def test_save_and_load_round_trip(calculator, config):
    calculator.calculate("add", "1.5", "2")
    calculator.calculate("root", "27", "3")
    calculator.save_history()

    fresh = Calculator(config, load_existing=False)
    assert fresh.load_history() == 2
    assert fresh.show_history() == calculator.show_history()


def test_history_loaded_on_startup(calculator, config):
    calculator.calculate("multiply", 6, 7)
    calculator.save_history()
    assert Calculator(config).show_history() == ["multiply(6, 7) = 42"]


def test_save_to_custom_path(calculator, tmp_path):
    calculator.calculate("add", 1, 1)
    path = calculator.save_history(tmp_path / "custom" / "h.csv")
    assert path.exists()


def test_save_failure_raises_history_error(calculator, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(HistoryError, match="Failed to save"):
        calculator.save_history(blocker / "h.csv")


def test_load_missing_file(calculator):
    with pytest.raises(HistoryError, match="not found"):
        calculator.load_history()


def test_load_empty_file(calculator, config):
    config.history_file.write_text("")
    assert calculator.load_history() == 0


def test_load_missing_columns(calculator, config):
    config.history_file.write_text("operation,result\nadd,3\n")
    with pytest.raises(HistoryError, match="missing columns"):
        calculator.load_history()


def test_load_bad_values(calculator, config):
    config.history_file.write_text(
        "operation,operand1,operand2,result,timestamp\nadd,one,2,3,2026-01-01T00:00:00\n"
    )
    with pytest.raises(HistoryError, match="Invalid calculation data"):
        calculator.load_history()


def test_load_blank_cell(calculator, config):
    config.history_file.write_text(
        "operation,operand1,operand2,result,timestamp\nadd,,2,3,2026-01-01T00:00:00\n"
    )
    with pytest.raises(HistoryError):
        calculator.load_history()


def test_load_unparseable_csv(calculator, config):
    config.history_file.write_text('operation,operand1\n"unterminated,1\n')
    with pytest.raises(HistoryError, match="Could not read"):
        calculator.load_history()


def test_load_is_undoable(calculator, config):
    calculator.calculate("add", 1, 1)
    calculator.save_history()
    calculator.clear_history()
    calculator.load_history()
    assert len(calculator.history) == 1
    calculator.undo()
    assert calculator.history == []


def test_corrupt_file_on_startup_is_logged(config):
    config.ensure_directories()
    config.history_file.write_text("garbage\n1\n")
    calc = Calculator(config)
    assert calc.history == []
    assert "Could not load existing history" in config.log_file.read_text()


def test_default_config_used(monkeypatch, tmp_path):
    monkeypatch.setenv("CALCULATOR_LOG_DIR", str(tmp_path / "l"))
    monkeypatch.setenv("CALCULATOR_HISTORY_DIR", str(tmp_path / "h"))
    calc = Calculator()
    assert isinstance(calc.config, CalculatorConfig)
    assert calc.config.log_dir == tmp_path / "l"


def test_dataframe_columns(calculator):
    calculator.calculate("abs_diff", 3, 8)
    df = calculator.get_history_dataframe()
    assert df.to_dict("records")[0]["result"] == "5"
