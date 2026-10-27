# Advanced Calculator

![CI](https://github.com/hptankeu1/advanced-calculator/actions/workflows/python-app.yml/badge.svg)

A command-line calculator written in Python. It supports ten arithmetic operations, undo/redo, persistent history saved with pandas, configurable logging, and settings loaded from a `.env` file. The code is organized around three design patterns:

| Pattern  | Where                       | Purpose                                                    |
|----------|-----------------------------|------------------------------------------------------------|
| Factory  | `app/operations.py`         | `OperationFactory` creates the right operation from its name |
| Memento  | `app/calculator_memento.py` | Snapshots of history that make undo/redo possible          |
| Observer | `app/history.py`            | `LoggingObserver` and `AutoSaveObserver` react to each new calculation |

## Features

- **Operations:** add, subtract, multiply, divide, power, root, modulus, int_divide, percent, abs_diff
- **Undo / redo** of calculations and of `clear` / `load`
- **History** saved to and loaded from CSV with pandas (columns: `operation`, `operand1`, `operand2`, `result`, `timestamp`)
- **Auto-save** after every calculation (can be turned off)
- **Logging** of every calculation, warning and error to a log file
- **Validation** with clear messages: non-numeric input, values over the configured maximum, division by zero, even roots of negative numbers, etc.
- **Precise math** using Python's `Decimal`, rounded to a configurable number of places

## Project structure

```
advanced-calculator/
├── app/
│   ├── calculator.py           # Calculator: operations, history, undo/redo, save/load
│   ├── calculation.py          # Calculation record (operation, operands, result, timestamp)
│   ├── calculator_config.py    # Loads and validates .env settings
│   ├── calculator_memento.py   # Memento for undo/redo
│   ├── calculator_repl.py      # Command-line interface (REPL)
│   ├── exceptions.py           # CalculatorError, ValidationError, OperationError, ...
│   ├── history.py              # LoggingObserver, AutoSaveObserver
│   ├── input_validators.py     # Number validation
│   ├── logger.py               # Logger class
│   └── operations.py           # Operation classes + OperationFactory
├── tests/                      # pytest suite (100% coverage)
├── main.py                     # Entry point
├── .env                        # Configuration
├── requirements.txt
└── .github/workflows/python-app.yml
```

## Installation

```bash
git clone https://github.com/hptankeu1/advanced-calculator.git
cd advanced-calculator
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Settings are read from `.env` in the project root using `python-dotenv`. Every setting has a default, so the file is optional; invalid values stop the program with a `ConfigurationError` explaining which setting is wrong.

```ini
# Base directories (relative to the project root unless absolute)
CALCULATOR_LOG_DIR=logs
CALCULATOR_HISTORY_DIR=history

# File names (placed inside the directories above unless absolute)
CALCULATOR_LOG_FILE=calculator.log
CALCULATOR_HISTORY_FILE=calculator_history.csv

# History settings
CALCULATOR_MAX_HISTORY_SIZE=1000     # oldest entries are dropped past this size
CALCULATOR_AUTO_SAVE=true            # true/false, yes/no, 1/0

# Calculation settings
CALCULATOR_PRECISION=10              # decimal places kept in results
CALCULATOR_MAX_INPUT_VALUE=1e10      # largest allowed absolute input
CALCULATOR_DEFAULT_ENCODING=utf-8    # encoding for log and CSV files
```

| Variable | Default | Description |
|---|---|---|
| `CALCULATOR_LOG_DIR` | `logs` | Directory for log files |
| `CALCULATOR_HISTORY_DIR` | `history` | Directory for history files |
| `CALCULATOR_LOG_FILE` | `calculator.log` | Log file name |
| `CALCULATOR_HISTORY_FILE` | `calculator_history.csv` | History CSV file name |
| `CALCULATOR_MAX_HISTORY_SIZE` | `1000` | Maximum history entries |
| `CALCULATOR_AUTO_SAVE` | `true` | Save history after each calculation |
| `CALCULATOR_PRECISION` | `10` | Decimal places in results |
| `CALCULATOR_MAX_INPUT_VALUE` | `1e10` | Maximum absolute input value |
| `CALCULATOR_DEFAULT_ENCODING` | `utf-8` | Encoding for file operations |

### Logging

Logs are written to `CALCULATOR_LOG_DIR/CALCULATOR_LOG_FILE` (by default `logs/calculator.log`) using Python's `logging` module:

- **INFO**: each calculation, undo/redo, save/load, startup and exit
- **WARNING**: unknown commands, history trimmed, unreadable history at startup
- **ERROR**: failed calculations, failed saves or loads

```
2026-10-26 22:31:09 | INFO     | calculator.observer | Calculation performed: power (2, -2) = 0.25
```

## Usage

```bash
python main.py
```

Type an operation with both numbers on one line, or just the operation name to be prompted for each number (type `cancel` to abort).

```
Enter command: power 2 -2
Result: 0.25

Enter command: root
Enter numbers (or 'cancel' to abort):
First number: -27
Second number: 3
Result: -3

Enter command: divide 5 0
Error: Division by zero is not allowed
```

### Operations

| Command | Result | Example |
|---|---|---|
| `add` | a + b | `add 2 3` → 5 |
| `subtract` | a − b | `subtract 2 3` → -1 |
| `multiply` | a × b | `multiply 4 2.5` → 10 |
| `divide` | a ÷ b | `divide 7 2` → 3.5 |
| `power` | a raised to b (negative exponents allowed) | `power 2 -2` → 0.25 |
| `root` | b-th root of a (odd roots of negatives allowed) | `root 27 3` → 3 |
| `modulus` | remainder of a ÷ b (sign follows a) | `modulus 10 4` → 2 |
| `int_divide` | a ÷ b with fractional part discarded | `int_divide 7 2` → 3 |
| `percent` | (a ÷ b) × 100 | `percent 1 8` → 12.5 |
| `abs_diff` | \|a − b\| | `abs_diff 2 9` → 7 |

### Other commands

| Command | Description |
|---|---|
| `history` | Show calculation history |
| `clear` | Clear history (can be undone) |
| `undo` | Undo the last calculation, clear or load |
| `redo` | Redo the last undone change |
| `save` | Save history to the CSV file |
| `load` | Load history from the CSV file |
| `help` | Show available commands |
| `exit` | Save (if auto-save is on) and quit |

## Testing

```bash
pytest                                        # run all tests
pytest --cov=app --cov-report=term-missing    # with coverage report
pytest --cov=app --cov-fail-under=90          # fail if coverage < 90%
```

The suite uses parameterized tests to cover normal cases and edge cases (division by zero, negative exponents, even roots of negative numbers, malformed CSV files, invalid configuration, and REPL input). Lines intentionally excluded from coverage (interactive entry points and type-checking imports) are marked `# pragma: no cover`.

## CI/CD

`.github/workflows/python-app.yml` runs on every push and pull request to `main`. It checks out the code, sets up Python 3.12, installs `requirements.txt`, and runs pytest with coverage. The job fails if coverage drops below 90%.
