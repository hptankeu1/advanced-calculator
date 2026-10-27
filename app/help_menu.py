"""
Decorator pattern: the help menu is built by wrapping a base menu in decorators.

    menu = ColorHelpDecorator(
        CommandsHelpDecorator(
            OperationsHelpDecorator(BaseHelpMenu()),
            commands),
        colors)

Each decorator adds one section (or styling) on top of what it wraps.
`OperationsHelpDecorator` reads the OperationFactory registry every time it
renders, so a newly registered operation shows up in `help` automatically.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.colors import ColorOutput
from app.operations import OperationFactory

INDENT = "  "


class HelpMenu(ABC):
    """Component interface: something that can render help lines."""

    @abstractmethod
    def render(self) -> List[str]:
        """Return the help menu as a list of lines."""

    def __str__(self) -> str:
        return "\n".join(self.render())


class BaseHelpMenu(HelpMenu):
    """Concrete component: just the title."""

    def __init__(self, title: str = "Advanced Calculator - Help"):
        self.title = title

    def render(self) -> List[str]:
        return [self.title, "=" * len(self.title)]


class HelpMenuDecorator(HelpMenu):
    """Base decorator: delegates to the wrapped menu."""

    def __init__(self, menu: HelpMenu):
        self.menu = menu

    def render(self) -> List[str]:
        return self.menu.render()


def _section(title: str, entries: Dict[str, str]) -> List[str]:
    width = max((len(name) for name in entries), default=0) + 2
    lines = ["", f"{title}:"]
    lines += [f"{INDENT}{name:<{width}}{desc}".rstrip() for name, desc in entries.items()]
    return lines


class OperationsHelpDecorator(HelpMenuDecorator):
    """Adds every operation currently registered in the OperationFactory."""

    def __init__(self, menu: HelpMenu, factory=OperationFactory):
        super().__init__(menu)
        self.factory = factory

    def render(self) -> List[str]:
        entries = self.factory.describe_operations()
        lines = super().render() + _section("Operations", entries)
        lines.append(f"{INDENT}Usage: <operation> <a> <b>   e.g. 'power 2 8'")
        lines.append(f"{INDENT}       <operation>           to be prompted for each number")
        return lines


class CommandsHelpDecorator(HelpMenuDecorator):
    """Adds the REPL's non-arithmetic commands."""

    def __init__(self, menu: HelpMenu, commands: Dict[str, str]):
        super().__init__(menu)
        self.commands = commands

    def render(self) -> List[str]:
        return super().render() + _section("Commands", self.commands)


class ColorHelpDecorator(HelpMenuDecorator):
    """Colors the title, section headers and command names."""

    def __init__(self, menu: HelpMenu, colors: Optional[ColorOutput] = None):
        super().__init__(menu)
        self.colors = colors or ColorOutput()

    def render(self) -> List[str]:
        lines = super().render()
        styled = []
        for i, line in enumerate(lines):
            if i < 2 or (line.endswith(":") and not line.startswith(" ")):
                styled.append(self.colors.header(line))
            elif self._is_entry(line):
                name, sep, rest = line[len(INDENT):].partition(" ")
                styled.append(f"{INDENT}{self.colors.info(name)}{sep}{rest}")
            else:
                styled.append(line)
        return styled

    @staticmethod
    def _is_entry(line: str) -> bool:
        """A '  name  description' line (not a usage line or continuation)."""
        body = line[len(INDENT):]
        return line.startswith(INDENT) and body[:1] not in ("", " ") \
            and not body.startswith("Usage")


def build_help_menu(commands: Dict[str, str], colors: Optional[ColorOutput] = None) -> HelpMenu:
    """Assemble the full help menu from its decorators."""
    menu: HelpMenu = BaseHelpMenu()
    menu = OperationsHelpDecorator(menu)
    menu = CommandsHelpDecorator(menu, commands)
    return ColorHelpDecorator(menu, colors)
