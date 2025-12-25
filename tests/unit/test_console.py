"""Tests for console UI wrapper."""

import pytest
from unittest.mock import MagicMock, patch
from io import StringIO

from organize.ui.console import ConsoleUI


class TestConsoleUI:
    """Tests for ConsoleUI class."""

    def test_initialization(self):
        """ConsoleUI initializes with Rich Console."""
        ui = ConsoleUI()
        assert ui.console is not None

    def test_print_delegates_to_console(self):
        """print() delegates to Rich Console."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print("test message")
            mock_print.assert_called_once_with("test message")

    def test_rule_delegates_to_console(self):
        """rule() delegates to Rich Console."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'rule') as mock_rule:
            ui.rule("Test Rule")
            mock_rule.assert_called_once_with("Test Rule")

    def test_print_info(self):
        """print_info() prints with info styling."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print_info("Info message")
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "Info message" in args

    def test_print_warning(self):
        """print_warning() prints with warning styling."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print_warning("Warning message")
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "Warning message" in args

    def test_print_error(self):
        """print_error() prints with error styling."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print_error("Error message")
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "Error message" in args

    def test_print_success(self):
        """print_success() prints with success styling."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print_success("Success message")
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "Success message" in args

    def test_print_simulation(self):
        """print_simulation() prints with simulation styling."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print_simulation("Simulation message")
            mock_print.assert_called_once()
            args = mock_print.call_args[0][0]
            assert "Simulation message" in args
            assert "SIMULATION" in args


class TestConsoleUIPanel:
    """Tests for panel display methods."""

    def test_print_panel(self):
        """print_panel() creates Rich Panel."""
        ui = ConsoleUI()
        with patch.object(ui.console, 'print') as mock_print:
            ui.print_panel("Content", title="Title")
            mock_print.assert_called_once()


class TestConsoleUITable:
    """Tests for table display methods."""

    def test_create_table(self):
        """create_table() returns Rich Table."""
        ui = ConsoleUI()
        table = ui.create_table("Test Title", ["Col1", "Col2"])
        assert table.title == "Test Title"
        assert len(table.columns) == 2

    def test_create_table_no_columns(self):
        """create_table() works with no columns."""
        ui = ConsoleUI()
        table = ui.create_table("Title")
        assert table.title == "Title"
