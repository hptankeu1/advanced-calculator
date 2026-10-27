"""
Color-coded terminal output using colorama.

Colors are turned on automatically when output goes to a terminal, and off
when it is piped/redirected or when NO_COLOR is set (https://no-color.org).
CALCULATOR_COLOR=true/false forces them on or off.
"""

import os
import sys
from typing import Optional

import colorama
from colorama import Fore, Style

colorama.just_fix_windows_console()

STATUS_COLORS = {
    "success": Fore.GREEN,
    "error": Fore.RED,
    "warning": Fore.YELLOW,
    "info": Fore.CYAN,
    "header": Fore.MAGENTA + Style.BRIGHT,
    "highlight": Fore.YELLOW + Style.BRIGHT,
    "muted": Style.DIM,
    "plain": "",
}


def colors_supported() -> bool:
    """Decide whether to use colors for this session."""
    forced = os.getenv("CALCULATOR_COLOR", "").strip().lower()
    if forced in {"true", "1", "yes", "on"}:
        return True
    if forced in {"false", "0", "no", "off"}:
        return False
    if os.getenv("NO_COLOR"):
        return False
    return sys.stdout.isatty()


class ColorOutput:
    """Wraps text in ANSI color codes according to its status."""

    def __init__(self, enabled: Optional[bool] = None):
        self.enabled = colors_supported() if enabled is None else enabled

    def paint(self, text: str, status: str = "plain") -> str:
        color = STATUS_COLORS.get(status, "")
        if not self.enabled or not color:
            return text
        return f"{color}{text}{Style.RESET_ALL}"

    def success(self, text: str) -> str:
        return self.paint(text, "success")

    def error(self, text: str) -> str:
        return self.paint(text, "error")

    def warning(self, text: str) -> str:
        return self.paint(text, "warning")

    def info(self, text: str) -> str:
        return self.paint(text, "info")

    def header(self, text: str) -> str:
        return self.paint(text, "header")

    def highlight(self, text: str) -> str:
        return self.paint(text, "highlight")
