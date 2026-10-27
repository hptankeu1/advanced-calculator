"""Tests for the REPL, driving it with scripted input."""

import pytest

from app.calculator import Calculator
from app.calculator_repl import CalculatorREPL
from app.exceptions import HistoryError


def run_repl(calculator, lines):
    """Run the REPL with the given input lines; return everything it printed."""
    inputs = iter(lines)
    output = []

    def fake_input(prompt=""):
        item = next(inputs)
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item()
        return item

    CalculatorREPL(calculator, fake_input, output.append).run()
    return "\n".join(output)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("add 2 3", "Result: 5"),
        ("subtract 2 3", "Result: -1"),
        ("multiply 4 2.5", "Result: 10"),
        ("divide 7 2", "Result: 3.5"),
        ("power 2 10", "Result: 1024"),
        ("root 125 3", "Result: 5"),
        ("modulus 10 4", "Result: 2"),
        ("int_divide 10 4", "Result: 2"),
        ("percent 1 8", "Result: 12.5"),
        ("abs_diff 2 9", "Result: 7"),
        ("ADD 1 1", "Result: 2"),
    ],
)
def test_inline_operations(calculator, line, expected):
    assert expected in run_repl(calculator, [line, "exit"])


def test_prompted_operation(calculator):
    out = run_repl(calculator, ["multiply", "6", "7", "exit"])
    assert "Result: 42" in out


@pytest.mark.parametrize("script", [["add", "cancel"], ["add", "5", "C"]])
def test_cancel_operation(calculator, script):
    out = run_repl(calculator, script + ["exit"])
    assert "Operation cancelled" in out
    assert calculator.history == []


@pytest.mark.parametrize(
    "line, message",
    [
        ("divide 1 0", "Error: Division by zero"),
        ("add one 2", "Error: Invalid number"),
        ("root -4 2", "Error: Cannot take an even root"),
        ("add 1e20 1", "Error: Value 1e20 exceeds"),
    ],
)
def test_operation_errors_are_reported(calculator, line, message):
    assert message in run_repl(calculator, [line, "exit"])


def test_wrong_argument_count(calculator):
    assert "Usage: add <a> <b>" in run_repl(calculator, ["add 1", "exit"])


def test_unknown_command(calculator):
    assert "Unknown command: 'sqrt'" in run_repl(calculator, ["sqrt 4", "exit"])


def test_blank_line_ignored(calculator):
    assert "Goodbye!" in run_repl(calculator, ["   ", "exit"])


def test_help_lists_everything(calculator):
    out = run_repl(calculator, ["help", "exit"])
    for word in ["add", "power", "root", "int_divide", "percent", "abs_diff",
                 "history", "clear", "undo", "redo", "save", "load", "exit"]:
        assert word in out


def test_history_undo_redo_clear(calculator):
    out = run_repl(calculator, [
        "history",
        "add 1 2", "multiply 2 3", "history",
        "undo", "redo", "undo", "undo", "undo", "redo",
        "clear", "history",
        "exit",
    ])
    assert "No calculations in history" in out
    assert "1. add(1, 2) = 3" in out
    assert "2. multiply(2, 3) = 6" in out
    assert "Operation undone" in out
    assert "Operation redone" in out
    assert "Nothing to undo" in out
    assert "History cleared" in out
    assert calculator.history == []


def test_nothing_to_redo(calculator):
    assert "Nothing to redo" in run_repl(calculator, ["redo", "exit"])


def test_save_and_load(calculator, config):
    out = run_repl(calculator, ["add 4 4", "save", "clear", "load", "history", "exit"])
    assert f"History saved to {config.history_file}" in out
    assert "Loaded 1 calculation(s)" in out
    assert "1. add(4, 4) = 8" in out


def test_load_missing_file(calculator):
    assert "Error loading history: History file not found" in run_repl(
        calculator, ["load", "exit"]
    )


def test_save_error(calculator, monkeypatch):
    def broken(*a, **k):
        raise HistoryError("disk full")

    monkeypatch.setattr(calculator, "save_history", broken)
    assert "Error saving history: disk full" in run_repl(calculator, ["save", "exit"])


def test_exit_auto_saves(config):
    config.auto_save = True
    calc = Calculator(config)
    out = run_repl(calc, ["add 1 1", "quit"])
    assert "History saved." in out
    assert config.history_file.exists()


def test_exit_save_failure_warns(config, monkeypatch):
    config.auto_save = True
    calc = Calculator(config)

    def broken(*a, **k):
        raise HistoryError("read-only")

    monkeypatch.setattr(calc, "save_history", broken)
    assert "Warning: could not save history: read-only" in run_repl(calc, ["exit"])


def test_keyboard_interrupt_continues(calculator):
    out = run_repl(calculator, [KeyboardInterrupt, "add 1 1", "exit"])
    assert "Operation cancelled. Type 'exit' to quit." in out
    assert "Result: 2" in out


def test_eof_exits(calculator):
    out = run_repl(calculator, [EOFError])
    assert "Input terminated." in out
    assert "Goodbye!" in out


def test_observers_registered(calculator):
    repl = CalculatorREPL(calculator, lambda p="": "exit", lambda s: None)
    names = {type(o).__name__ for o in repl.calculator.observers}
    assert names == {"LoggingObserver", "AutoSaveObserver"}


def test_default_calculator_created(monkeypatch, tmp_path):
    monkeypatch.setenv("CALCULATOR_LOG_DIR", str(tmp_path / "l"))
    monkeypatch.setenv("CALCULATOR_HISTORY_DIR", str(tmp_path / "h"))
    repl = CalculatorREPL(input_func=lambda p="": "exit", output_func=lambda s: None)
    assert isinstance(repl.calculator, Calculator)
