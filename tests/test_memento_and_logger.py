"""Tests for CalculatorMemento and the Logger class."""

import logging
from datetime import datetime
from decimal import Decimal

from app.calculation import Calculation
from app.calculator_memento import CalculatorMemento
from app.logger import LOGGER_NAME, Logger


def test_memento_copies_history():
    history = [Calculation("add", Decimal(1), Decimal(2), Decimal(3))]
    memento = CalculatorMemento(history)
    history.append(Calculation("add", Decimal(1), Decimal(1), Decimal(2)))
    assert len(memento.history) == 1


def test_memento_round_trip():
    calc = Calculation("power", Decimal(2), Decimal(3), Decimal(8), datetime(2026, 1, 1))
    memento = CalculatorMemento([calc], timestamp=datetime(2026, 1, 2))
    restored = CalculatorMemento.from_dict(memento.to_dict())
    assert restored.history == [calc]
    assert restored.timestamp == datetime(2026, 1, 2)


def test_logger_setup_writes_file(tmp_path):
    log_file = tmp_path / "nested" / "app.log"
    logger = Logger.setup(log_file)
    logger.warning("something happened")
    assert "WARNING" in log_file.read_text()
    assert "something happened" in log_file.read_text()


def test_logger_setup_replaces_handlers(tmp_path):
    Logger.setup(tmp_path / "a.log")
    Logger.setup(tmp_path / "b.log")
    handlers = logging.getLogger(LOGGER_NAME).handlers
    assert len(handlers) == 1
    Logger.get_logger().info("only in b")
    assert "only in b" in (tmp_path / "b.log").read_text()
    assert "only in b" not in (tmp_path / "a.log").read_text()


def test_get_logger_child():
    assert Logger.get_logger("history").name == "calculator.history"
    assert Logger.get_logger().name == "calculator"
