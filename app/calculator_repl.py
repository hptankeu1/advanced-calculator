"""
Command-line interface (Read-Eval-Print Loop) for the calculator.

Each line of input is turned into a Command object (Command pattern) and run by
a CommandInvoker. Results are printed in color by status: green for results,
red for errors, yellow for warnings, cyan for info. The help menu is built with
the Decorator pattern from the registered operations and commands.

Operations can be typed on one line ("power 2 8") or as just the command name,
in which case the REPL asks for each number. Operations can also be queued
("queue add 2 3") and run together later ("run").
"""

from typing import Callable, Dict, List, Optional

from app.calculator import Calculator
from app.colors import ColorOutput
from app.commands import (
    CalculateCommand, ClearCommand, Command, CommandInvoker, CommandResult,
    ExitCommand, HelpCommand, HistoryCommand, LoadCommand, QueueCommand,
    RedoCommand, RunQueueCommand, SaveCommand, UndoCommand, describe_commands,
)
from app.exceptions import CalculatorError
from app.help_menu import build_help_menu
from app.history import AutoSaveObserver, LoggingObserver
from app.logger import Logger
from app.operations import OperationFactory

CANCEL_WORDS = {"cancel", "c"}


class CalculatorREPL:
    """Interactive loop around a Calculator. Input/output are injectable for tests."""

    def __init__(
        self,
        calculator: Optional[Calculator] = None,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        use_color: Optional[bool] = None,
    ):
        self.calculator = calculator or Calculator()
        self.input = input_func
        self.output = output_func
        self.colors = ColorOutput(use_color)
        self.invoker = CommandInvoker()
        self.help_menu = build_help_menu(describe_commands(), self.colors)
        self.logger = Logger.get_logger("repl")
        self.running = False

        self.calculator.add_observer(LoggingObserver())
        self.calculator.add_observer(AutoSaveObserver(self.calculator))

        # word typed -> function(args) that builds the Command to run
        calc = self.calculator
        self.command_builders: Dict[str, Callable[[List[str]], Optional[Command]]] = {
            "help": lambda args: HelpCommand(self.help_menu),
            "history": lambda args: HistoryCommand(calc),
            "clear": lambda args: ClearCommand(calc),
            "undo": lambda args: UndoCommand(calc),
            "redo": lambda args: RedoCommand(calc),
            "save": lambda args: SaveCommand(calc),
            "load": lambda args: LoadCommand(calc),
            "queue": self._build_queue_command,
            "run": lambda args: RunQueueCommand(self.invoker),
            "exit": lambda args: ExitCommand(calc),
            "quit": lambda args: ExitCommand(calc),
        }

    # ---------------------------------------------------------------- output
    def show(self, result: CommandResult) -> None:
        """Print a command result (and any nested results) in its color."""
        if result.message:
            self.output(self.colors.paint(result.message, result.status))
        for detail in result.details:
            self.show(detail)

    # ------------------------------------------------------------- main loop
    def run(self) -> None:
        self.running = True
        self.output(
            self.colors.header("Advanced Calculator")
            + self.colors.info(" - type 'help' for commands, 'exit' to quit.")
        )
        while self.running:
            try:
                line = self.input("\nEnter command: ")
            except KeyboardInterrupt:
                self.output(self.colors.warning("\nOperation cancelled. Type 'exit' to quit."))
                continue
            except EOFError:
                self.output(self.colors.warning("\nInput terminated."))
                self.show(self.invoker.execute(ExitCommand(self.calculator)))
                break
            self.handle(line)

    def handle(self, line: str) -> None:
        """Turn one line of input into a command and execute it."""
        parts = line.strip().split()
        if not parts:
            return
        command = self.build_command(parts[0].lower(), parts[1:])
        if command is None:
            return
        result = self.invoker.execute(command)
        self.show(result)
        if result.should_exit:
            self.logger.info("Calculator REPL exited")
            self.running = False

    # -------------------------------------------------------- command parsing
    def build_command(self, word: str, args: List[str]) -> Optional[Command]:
        """Return the Command for `word`, or None if there is nothing to run."""
        if word in self.command_builders:
            return self.command_builders[word](args)
        if word in OperationFactory.available_operations():
            return self._build_calculation(word, args)
        self.output(self.colors.error(
            f"Unknown command: '{word}'. Type 'help' for available commands."
        ))
        self.logger.warning("Unknown command entered: %s", word)
        return None

    def _build_calculation(self, name: str, args: List[str]) -> Optional[Command]:
        if len(args) == 2:
            return CalculateCommand(self.calculator, name, *args)
        if args:
            self.output(self.colors.warning(
                f"Usage: {name} <a> <b>   (or just '{name}' to be prompted)"
            ))
            return None

        self.output(self.colors.info("Enter numbers (or 'cancel' to abort):"))
        numbers = []
        for prompt in ("First number: ", "Second number: "):
            value = self.input(prompt).strip()
            if value.lower() in CANCEL_WORDS:
                self.output(self.colors.warning("Operation cancelled"))
                return None
            numbers.append(value)
        return CalculateCommand(self.calculator, name, *numbers)

    def _build_queue_command(self, args: List[str]) -> Optional[Command]:
        if not args:
            return QueueCommand(self.invoker)
        if args == ["clear"]:
            return QueueCommand(self.invoker, clear=True)
        operation = args[0].lower()
        if operation not in OperationFactory.available_operations() or len(args) != 3:
            self.output(self.colors.warning(
                "Usage: queue <operation> <a> <b>  |  queue  |  queue clear"
            ))
            return None
        calculation = CalculateCommand(self.calculator, operation, args[1], args[2])
        return QueueCommand(self.invoker, calculation)


def calculator_repl() -> None:  # pragma: no cover - interactive entry point
    """Start the calculator REPL with default configuration."""
    try:
        CalculatorREPL().run()
    except CalculatorError as exc:
        print(ColorOutput().error(f"Fatal error: {exc}"))
        raise SystemExit(1)
