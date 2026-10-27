"""
Command-line interface (Read-Eval-Print Loop) for the calculator.

Operations can be typed on one line ("power 2 8") or as just the command name,
in which case the REPL asks for each number. Type "help" for all commands.
"""

from typing import Callable, Optional

from app.calculation import format_decimal
from app.calculator import Calculator
from app.exceptions import CalculatorError
from app.history import AutoSaveObserver, LoggingObserver
from app.logger import Logger
from app.operations import OperationFactory

OPERATION_HELP = {
    "add": "a + b",
    "subtract": "a - b",
    "multiply": "a * b",
    "divide": "a / b",
    "power": "a raised to the power b",
    "root": "the b-th root of a",
    "modulus": "remainder of a / b",
    "int_divide": "a / b with the fractional part discarded",
    "percent": "(a / b) * 100",
    "abs_diff": "|a - b|",
}

COMMAND_HELP = {
    "history": "Show calculation history",
    "clear": "Clear calculation history",
    "undo": "Undo the last change",
    "redo": "Redo the last undone change",
    "save": "Save history to CSV",
    "load": "Load history from CSV",
    "help": "Show this help",
    "exit": "Exit the calculator",
}

CANCEL_WORDS = {"cancel", "c"}


class CalculatorREPL:
    """Interactive loop around a Calculator. Input/output are injectable for tests."""

    def __init__(
        self,
        calculator: Optional[Calculator] = None,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ):
        self.calculator = calculator or Calculator()
        self.input = input_func
        self.output = output_func
        self.logger = Logger.get_logger("repl")
        self.running = False

        self.calculator.add_observer(LoggingObserver())
        self.calculator.add_observer(AutoSaveObserver(self.calculator))

        self.commands = {
            "help": self.show_help,
            "history": self.show_history,
            "clear": self.clear,
            "undo": self.undo,
            "redo": self.redo,
            "save": self.save,
            "load": self.load,
            "exit": self.exit,
            "quit": self.exit,
        }

    # ---------------------------------------------------------------- main loop
    def run(self) -> None:
        self.running = True
        self.output("Advanced Calculator. Type 'help' for commands, 'exit' to quit.")
        while self.running:
            try:
                line = self.input("\nEnter command: ")
            except KeyboardInterrupt:
                self.output("\nOperation cancelled. Type 'exit' to quit.")
                continue
            except EOFError:
                self.output("\nInput terminated.")
                self.exit()
                break
            self.handle(line)

    def handle(self, line: str) -> None:
        """Process one line of input."""
        parts = line.strip().split()
        if not parts:
            return
        command, args = parts[0].lower(), parts[1:]

        if command in self.commands:
            self.commands[command]()
        elif command in OperationFactory.available_operations():
            self.run_operation(command, args)
        else:
            self.output(f"Unknown command: '{command}'. Type 'help' for available commands.")
            self.logger.warning("Unknown command entered: %s", command)

    # --------------------------------------------------------------- operations
    def run_operation(self, name: str, args: list) -> None:
        if len(args) == 2:
            a, b = args
        elif not args:
            self.output("Enter numbers (or 'cancel' to abort):")
            a = self.input("First number: ").strip()
            if a.lower() in CANCEL_WORDS:
                self.output("Operation cancelled")
                return
            b = self.input("Second number: ").strip()
            if b.lower() in CANCEL_WORDS:
                self.output("Operation cancelled")
                return
        else:
            self.output(f"Usage: {name} <a> <b>   (or just '{name}' to be prompted)")
            return

        try:
            result = self.calculator.calculate(name, a, b)
            self.output(f"Result: {format_decimal(result)}")
        except CalculatorError as exc:
            self.output(f"Error: {exc}")

    # ----------------------------------------------------------------- commands
    def show_help(self) -> None:
        lines = ["", "Operations (type the name, or e.g. 'power 2 8'):"]
        lines += [f"  {name:<11} {desc}" for name, desc in OPERATION_HELP.items()]
        lines += ["", "Commands:"]
        lines += [f"  {name:<11} {desc}" for name, desc in COMMAND_HELP.items()]
        self.output("\n".join(lines))

    def show_history(self) -> None:
        history = self.calculator.show_history()
        if not history:
            self.output("No calculations in history")
            return
        self.output("Calculation History:")
        for i, entry in enumerate(history, 1):
            self.output(f"{i}. {entry}")

    def clear(self) -> None:
        self.calculator.clear_history()
        self.output("History cleared")

    def undo(self) -> None:
        self.output("Operation undone" if self.calculator.undo() else "Nothing to undo")

    def redo(self) -> None:
        self.output("Operation redone" if self.calculator.redo() else "Nothing to redo")

    def save(self) -> None:
        try:
            path = self.calculator.save_history()
            self.output(f"History saved to {path}")
        except CalculatorError as exc:
            self.output(f"Error saving history: {exc}")

    def load(self) -> None:
        try:
            count = self.calculator.load_history()
            self.output(f"Loaded {count} calculation(s) from history")
        except CalculatorError as exc:
            self.output(f"Error loading history: {exc}")

    def exit(self) -> None:
        if self.calculator.config.auto_save:
            try:
                self.calculator.save_history()
                self.output("History saved.")
            except CalculatorError as exc:
                self.output(f"Warning: could not save history: {exc}")
        self.output("Goodbye!")
        self.logger.info("Calculator REPL exited")
        self.running = False


def calculator_repl() -> None:  # pragma: no cover - interactive entry point
    """Start the calculator REPL with default configuration."""
    try:
        CalculatorREPL().run()
    except CalculatorError as exc:
        print(f"Fatal error: {exc}")
        raise SystemExit(1)
