"""Tests for the Command pattern: commands, invoker and queue."""

import pytest

from app.colors import ColorOutput
from app.commands import (
    SIMPLE_COMMANDS, CalculateCommand, ClearCommand, Command, CommandInvoker,
    CommandResult, ExitCommand, HelpCommand, HistoryCommand, LoadCommand,
    QueueCommand, RedoCommand, RunQueueCommand, SaveCommand, UndoCommand,
    describe_commands,
)
from app.exceptions import HistoryError
from app.help_menu import BaseHelpMenu


@pytest.fixture
def invoker():
    return CommandInvoker()


def test_calculate_command_success(calculator):
    result = CalculateCommand(calculator, "power", "2", "5").execute()
    assert result == CommandResult("Result: 32", "success")
    assert str(CalculateCommand(calculator, "power", "2", "5")) == "power 2 5"


def test_calculate_command_error(calculator):
    result = CalculateCommand(calculator, "divide", "1", "0").execute()
    assert result.status == "error"
    assert result.message.startswith("Error: Division by zero")


def test_history_command(calculator):
    assert HistoryCommand(calculator).execute().status == "warning"
    calculator.calculate("add", 1, 2)
    result = HistoryCommand(calculator).execute()
    assert result.message == "Calculation History:\n1. add(1, 2) = 3"


def test_clear_undo_redo_commands(calculator):
    calculator.calculate("add", 1, 2)
    assert ClearCommand(calculator).execute().message == "History cleared"
    assert UndoCommand(calculator).execute().message == "Operation undone"
    assert len(calculator.history) == 1
    assert RedoCommand(calculator).execute().message == "Operation redone"
    assert calculator.history == []


def test_undo_redo_nothing(calculator):
    assert UndoCommand(calculator).execute().status == "warning"
    assert RedoCommand(calculator).execute().status == "warning"


def test_save_and_load_commands(calculator, config):
    calculator.calculate("add", 1, 2)
    assert SaveCommand(calculator).execute().status == "success"
    assert config.history_file.exists()
    result = LoadCommand(calculator).execute()
    assert result.message == "Loaded 1 calculation(s) from history"


def test_save_and_load_errors(calculator, monkeypatch):
    def broken(*a, **k):
        raise HistoryError("boom")

    monkeypatch.setattr(calculator, "save_history", broken)
    assert SaveCommand(calculator).execute().status == "error"
    assert LoadCommand(calculator).execute().status == "error"  # no file yet


def test_help_command():
    result = HelpCommand(BaseHelpMenu("Hi")).execute()
    assert result.message == "Hi\n=="
    assert result.status == "plain"


def test_exit_command_without_auto_save(calculator):
    result = ExitCommand(calculator).execute()
    assert result.should_exit is True
    assert [d.message for d in result.details] == ["Goodbye!"]


def test_exit_command_with_auto_save(config):
    from app.calculator import Calculator

    config.auto_save = True
    calc = Calculator(config)
    result = ExitCommand(calc).execute()
    assert [d.message for d in result.details] == ["History saved.", "Goodbye!"]


def test_exit_command_save_failure(config, monkeypatch):
    from app.calculator import Calculator

    config.auto_save = True
    calc = Calculator(config)

    def broken(*a, **k):
        raise HistoryError("read-only")

    monkeypatch.setattr(calc, "save_history", broken)
    first = ExitCommand(calc).execute().details[0]
    assert first.status == "warning"
    assert "read-only" in first.message


# ------------------------------------------------------------------- invoker
def test_invoker_executes_and_records(calculator, invoker):
    command = CalculateCommand(calculator, "add", 2, 2)
    assert invoker.execute(command).message == "Result: 4"
    assert invoker.executed == [command]


def test_invoker_queue_runs_in_order(calculator, invoker):
    invoker.enqueue(CalculateCommand(calculator, "add", 1, 1))
    invoker.enqueue(CalculateCommand(calculator, "multiply", 3, 3))
    assert calculator.history == []  # nothing runs until run_queue
    results = invoker.run_queue()
    assert [r.message for _, r in results] == ["Result: 2", "Result: 9"]
    assert invoker.queue == []
    assert calculator.show_history() == ["add(1, 1) = 2", "multiply(3, 3) = 9"]


def test_invoker_clear_queue(calculator, invoker):
    invoker.enqueue(CalculateCommand(calculator, "add", 1, 1))
    assert invoker.clear_queue() == 1
    assert invoker.queue == []


def test_queue_command_add_list_clear(calculator, invoker):
    assert QueueCommand(invoker).execute().message == "Queue is empty"
    result = QueueCommand(invoker, CalculateCommand(calculator, "add", 1, 2)).execute()
    assert result.message == "Queued: add 1 2 (1 pending)"
    assert QueueCommand(invoker).execute().message == "Queued operations:\n1. add 1 2"
    assert QueueCommand(invoker, clear=True).execute().message == "Queue cleared (1 removed)"


def test_run_queue_command(calculator, invoker):
    assert RunQueueCommand(invoker).execute().status == "warning"
    invoker.enqueue(CalculateCommand(calculator, "add", 1, 2))
    invoker.enqueue(CalculateCommand(calculator, "divide", 1, 0))
    result = RunQueueCommand(invoker).execute()
    assert result.message == "Ran 2 queued operation(s):"
    assert result.details[0] == CommandResult("add 1 2 -> Result: 3", "success")
    assert result.details[1].status == "error"


def test_command_default_str():
    class Ping(Command):
        def execute(self):
            return CommandResult("pong")

    assert str(Ping()) == "Ping"
    assert str(UndoCommand(None)) == "undo"


def test_describe_commands_covers_all_simple_commands():
    descriptions = describe_commands()
    assert list(descriptions) == [cls.name for cls in SIMPLE_COMMANDS]
    assert all(descriptions.values())
