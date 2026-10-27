"""
Command pattern: every user request is an object with an `execute()` method.

The REPL turns each line of input into a Command and hands it to a
CommandInvoker. Because requests are objects they can be parameterized
(CalculateCommand holds its operation and operands), queued for later
(`queue add 2 3`, then `run`) and logged in one place.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from app.calculation import format_decimal
from app.exceptions import CalculatorError
from app.logger import Logger

if TYPE_CHECKING:  # pragma: no cover - import only for type hints
    from app.calculator import Calculator
    from app.help_menu import HelpMenu


@dataclass
class CommandResult:
    """What a command produced: a message, its status (for color) and extras."""

    message: str = ""
    status: str = "info"  # success | error | warning | info | plain
    should_exit: bool = False
    details: List["CommandResult"] = field(default_factory=list)


class Command(ABC):
    """Interface for every command."""

    #: word typed in the REPL (empty for commands not typed directly)
    name: str = ""
    #: help text shown in the help menu
    description: str = ""

    @abstractmethod
    def execute(self) -> CommandResult:
        """Carry out the request."""

    def __str__(self) -> str:
        return self.name or self.__class__.__name__


# --------------------------------------------------------------- calculations
class CalculateCommand(Command):
    """Runs one operation with two operands on the calculator."""

    def __init__(self, calculator: "Calculator", operation: str, a, b):
        self.calculator = calculator
        self.operation = operation
        self.a = a
        self.b = b

    def execute(self) -> CommandResult:
        try:
            result = self.calculator.calculate(self.operation, self.a, self.b)
        except CalculatorError as exc:
            return CommandResult(f"Error: {exc}", "error")
        return CommandResult(f"Result: {format_decimal(result)}", "success")

    def __str__(self) -> str:
        return f"{self.operation} {self.a} {self.b}"


# -------------------------------------------------------------------- history
class HistoryCommand(Command):
    name, description = "history", "Show calculation history"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        history = self.calculator.show_history()
        if not history:
            return CommandResult("No calculations in history", "warning")
        lines = ["Calculation History:"]
        lines += [f"{i}. {entry}" for i, entry in enumerate(history, 1)]
        return CommandResult("\n".join(lines), "info")


class ClearCommand(Command):
    name, description = "clear", "Clear calculation history (can be undone)"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        self.calculator.clear_history()
        return CommandResult("History cleared", "success")


class UndoCommand(Command):
    name, description = "undo", "Undo the last calculation, clear or load"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        if self.calculator.undo():
            return CommandResult("Operation undone", "success")
        return CommandResult("Nothing to undo", "warning")


class RedoCommand(Command):
    name, description = "redo", "Redo the last undone change"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        if self.calculator.redo():
            return CommandResult("Operation redone", "success")
        return CommandResult("Nothing to redo", "warning")


class SaveCommand(Command):
    name, description = "save", "Save history to CSV"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        try:
            path = self.calculator.save_history()
        except CalculatorError as exc:
            return CommandResult(f"Error saving history: {exc}", "error")
        return CommandResult(f"History saved to {path}", "success")


class LoadCommand(Command):
    name, description = "load", "Load history from CSV"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        try:
            count = self.calculator.load_history()
        except CalculatorError as exc:
            return CommandResult(f"Error loading history: {exc}", "error")
        return CommandResult(f"Loaded {count} calculation(s) from history", "success")


# ---------------------------------------------------------------------- misc
class HelpCommand(Command):
    name, description = "help", "Show this help menu"

    def __init__(self, menu: "HelpMenu"):
        self.menu = menu

    def execute(self) -> CommandResult:
        # The help menu does its own coloring, so print it as is.
        return CommandResult(str(self.menu), "plain")


class ExitCommand(Command):
    name, description = "exit", "Save history (if auto-save is on) and quit"

    def __init__(self, calculator: "Calculator"):
        self.calculator = calculator

    def execute(self) -> CommandResult:
        details = []
        if self.calculator.config.auto_save:
            try:
                self.calculator.save_history()
                details.append(CommandResult("History saved.", "success"))
            except CalculatorError as exc:
                details.append(
                    CommandResult(f"Warning: could not save history: {exc}", "warning")
                )
        details.append(CommandResult("Goodbye!", "info"))
        return CommandResult(should_exit=True, details=details)


# ------------------------------------------------------------------- queueing
class QueueCommand(Command):
    name = "queue"
    description = "queue <op> <a> <b> adds to the queue; 'queue' lists it; 'queue clear' empties it"

    def __init__(self, invoker: "CommandInvoker", command: Optional[Command] = None,
                 clear: bool = False):
        self.invoker = invoker
        self.command = command
        self.clear = clear

    def execute(self) -> CommandResult:
        if self.clear:
            count = self.invoker.clear_queue()
            return CommandResult(f"Queue cleared ({count} removed)", "success")
        if self.command is not None:
            self.invoker.enqueue(self.command)
            return CommandResult(
                f"Queued: {self.command} ({len(self.invoker.queue)} pending)", "success"
            )
        if not self.invoker.queue:
            return CommandResult("Queue is empty", "warning")
        lines = ["Queued operations:"]
        lines += [f"{i}. {cmd}" for i, cmd in enumerate(self.invoker.queue, 1)]
        return CommandResult("\n".join(lines), "info")


class RunQueueCommand(Command):
    name, description = "run", "Execute every queued operation in order"

    def __init__(self, invoker: "CommandInvoker"):
        self.invoker = invoker

    def execute(self) -> CommandResult:
        if not self.invoker.queue:
            return CommandResult("Queue is empty", "warning")
        details = []
        for command, result in self.invoker.run_queue():
            details.append(CommandResult(f"{command} -> {result.message}", result.status))
        return CommandResult(f"Ran {len(details)} queued operation(s):", "info", details=details)


# -------------------------------------------------------------------- invoker
class CommandInvoker:
    """Executes commands, keeps a queue of pending ones and a log of executed ones."""

    def __init__(self):
        self.queue: List[Command] = []
        self.executed: List[Command] = []
        self.logger = Logger.get_logger("commands")

    def execute(self, command: Command) -> CommandResult:
        self.logger.info("Executing command: %s", command)
        result = command.execute()
        self.executed.append(command)
        return result

    def enqueue(self, command: Command) -> None:
        self.queue.append(command)
        self.logger.info("Queued command: %s", command)

    def run_queue(self) -> List[tuple]:
        """Execute queued commands in order. Returns [(command, result), ...]."""
        results = []
        while self.queue:
            command = self.queue.pop(0)
            results.append((command, self.execute(command)))
        return results

    def clear_queue(self) -> int:
        count = len(self.queue)
        self.queue.clear()
        return count


#: Commands typed directly in the REPL, in help-menu order. Each entry builds
#: the command from the REPL; the class supplies its name and help text.
SIMPLE_COMMANDS: List[Type[Command]] = [
    HistoryCommand, ClearCommand, UndoCommand, RedoCommand, SaveCommand,
    LoadCommand, QueueCommand, RunQueueCommand, HelpCommand, ExitCommand,
]


def describe_commands() -> Dict[str, str]:
    """{name: description} for every REPL command, used by the help menu."""
    return {cls.name: cls.description for cls in SIMPLE_COMMANDS}
