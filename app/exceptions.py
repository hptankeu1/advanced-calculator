"""Custom exception hierarchy for the calculator."""


class CalculatorError(Exception):
    """Base class for every calculator error."""


class ValidationError(CalculatorError):
    """Raised when user input is not a valid number or is out of range."""


class OperationError(CalculatorError):
    """Raised when an operation cannot be performed (e.g. divide by zero)."""


class ConfigurationError(CalculatorError):
    """Raised when configuration values are missing or invalid."""


class HistoryError(CalculatorError):
    """Raised when calculation history cannot be saved or loaded."""
