"""Tests for the decorator-built help menu."""

from colorama import Fore, Style

from app.colors import ColorOutput
from app.commands import describe_commands
from app.help_menu import (
    BaseHelpMenu, ColorHelpDecorator, CommandsHelpDecorator, HelpMenuDecorator,
    OperationsHelpDecorator, build_help_menu,
)
from app.operations import Operation, OperationFactory


def test_base_menu_has_title():
    assert BaseHelpMenu("Title").render() == ["Title", "====="]


def test_plain_decorator_delegates():
    base = BaseHelpMenu()
    assert HelpMenuDecorator(base).render() == base.render()


def test_operations_section_lists_every_registered_operation():
    text = str(OperationsHelpDecorator(BaseHelpMenu()))
    for name, description in OperationFactory.describe_operations().items():
        assert name in text
        assert description in text
    assert "Usage: <operation> <a> <b>" in text


def test_new_operation_appears_in_help_automatically():
    menu = OperationsHelpDecorator(BaseHelpMenu())
    assert "cube_sum" not in str(menu)

    @OperationFactory.register("cube_sum", "a^3 + b^3")
    class CubeSum(Operation):
        def _compute(self, a, b):
            return a ** 3 + b ** 3

    try:
        # Same menu object, no manual change: the new operation is listed.
        assert "cube_sum" in str(menu)
        assert "a^3 + b^3" in str(menu)
    finally:
        OperationFactory.unregister_operation("cube_sum")
    assert "cube_sum" not in str(menu)


def test_commands_section():
    text = str(CommandsHelpDecorator(BaseHelpMenu(), {"undo": "Undo it"}))
    assert "Commands:" in text
    assert "  undo  Undo it" in text


def test_commands_section_handles_empty_dict():
    assert str(CommandsHelpDecorator(BaseHelpMenu(), {})).endswith("Commands:")


def test_decorators_stack_in_order():
    menu = CommandsHelpDecorator(OperationsHelpDecorator(BaseHelpMenu()), {"x": "y"})
    text = str(menu)
    assert text.index("Operations:") < text.index("Commands:")


def test_color_decorator_colors_headers_and_names():
    menu = ColorHelpDecorator(
        CommandsHelpDecorator(BaseHelpMenu("T"), {"undo": "Undo it"}),
        ColorOutput(enabled=True),
    )
    lines = menu.render()
    header = Fore.MAGENTA + Style.BRIGHT
    assert lines[0] == f"{header}T{Style.RESET_ALL}"
    assert f"{header}Commands:{Style.RESET_ALL}" in lines
    assert f"  {Fore.CYAN}undo{Style.RESET_ALL}  Undo it" in lines


def test_color_decorator_leaves_usage_lines_plain():
    menu = ColorHelpDecorator(OperationsHelpDecorator(BaseHelpMenu()), ColorOutput(enabled=True))
    usage = [line for line in menu.render() if "Usage" in line or "prompted" in line]
    assert usage and all("\x1b" not in line for line in usage)


def test_color_decorator_disabled_matches_plain_menu():
    plain = CommandsHelpDecorator(OperationsHelpDecorator(BaseHelpMenu()), {"a": "b"})
    colored = ColorHelpDecorator(plain, ColorOutput(enabled=False))
    assert colored.render() == plain.render()


def test_color_decorator_default_colors():
    assert isinstance(ColorHelpDecorator(BaseHelpMenu()).colors, ColorOutput)


def test_build_help_menu_includes_operations_and_commands():
    text = str(build_help_menu(describe_commands(), ColorOutput(enabled=False)))
    for word in ["add", "abs_diff", "history", "queue", "run", "exit"]:
        assert word in text
