"""Tests for color-coded output."""

import pytest
from colorama import Fore, Style

from app.colors import ColorOutput, colors_supported


@pytest.fixture
def no_color_env(monkeypatch):
    monkeypatch.delenv("CALCULATOR_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    return monkeypatch


@pytest.mark.parametrize(
    "method, color",
    [
        ("success", Fore.GREEN),
        ("error", Fore.RED),
        ("warning", Fore.YELLOW),
        ("info", Fore.CYAN),
        ("header", Fore.MAGENTA + Style.BRIGHT),
        ("highlight", Fore.YELLOW + Style.BRIGHT),
    ],
)
def test_colors_applied_when_enabled(method, color):
    text = getattr(ColorOutput(enabled=True), method)("hi")
    assert text == f"{color}hi{Style.RESET_ALL}"


def test_plain_and_unknown_status_not_colored():
    colors = ColorOutput(enabled=True)
    assert colors.paint("hi", "plain") == "hi"
    assert colors.paint("hi", "nonsense") == "hi"


def test_disabled_returns_plain_text():
    assert ColorOutput(enabled=False).error("hi") == "hi"


@pytest.mark.parametrize("value, expected", [("true", True), ("1", True), ("off", False), ("no", False)])
def test_calculator_color_env_forces_setting(no_color_env, value, expected):
    no_color_env.setenv("CALCULATOR_COLOR", value)
    assert colors_supported() is expected


def test_no_color_env_disables(no_color_env):
    no_color_env.setenv("NO_COLOR", "1")
    assert colors_supported() is False


@pytest.mark.parametrize("is_tty", [True, False])
def test_auto_detects_terminal(no_color_env, monkeypatch, is_tty):
    monkeypatch.setattr("sys.stdout.isatty", lambda: is_tty)
    assert colors_supported() is is_tty
    assert ColorOutput().enabled is is_tty
