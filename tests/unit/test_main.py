"""Tests for the organize package entry point."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from organize.__main__ import (
    setup_logging,
    display_configuration,
    main,
)
from organize.config import CLIArgs, ExecutionContext


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self):
        """Sets up logging with default level."""
        with patch("organize.__main__.logger") as mock_logger:
            setup_logging(debug=False)
            mock_logger.remove.assert_called_once()
            assert mock_logger.add.call_count == 2

    def test_setup_logging_debug(self):
        """Sets up logging with debug level."""
        with patch("organize.__main__.logger") as mock_logger:
            setup_logging(debug=True)
            mock_logger.remove.assert_called_once()


class TestDisplayConfiguration:
    """Tests for display_configuration function."""

    def test_displays_normal_mode(self):
        """Displays configuration in normal mode."""
        cli_args = CLIArgs(
            days_to_process=7.0,
            dry_run=False,
            force_mode=False,
            search_dir=Path("/search"),
            output_dir=Path("/output"),
            symlinks_dir=Path("/symlinks"),
            storage_dir=Path("/storage"),
        )
        console = MagicMock()

        display_configuration(cli_args, console)

        console.print_panel.assert_called_once()
        call_args = console.print_panel.call_args[0][0]
        assert "Normal" in call_args or "green" in call_args

    def test_displays_simulation_mode(self):
        """Displays configuration in simulation mode."""
        cli_args = CLIArgs(
            days_to_process=7.0,
            dry_run=True,
            force_mode=False,
            search_dir=Path("/search"),
            output_dir=Path("/output"),
            symlinks_dir=Path("/symlinks"),
            storage_dir=Path("/storage"),
        )
        console = MagicMock()

        display_configuration(cli_args, console)

        call_args = console.print_panel.call_args[0][0]
        assert "SIMULATION" in call_args

    def test_displays_force_mode(self):
        """Displays configuration in force mode."""
        cli_args = CLIArgs(
            days_to_process=7.0,
            dry_run=False,
            force_mode=True,
            search_dir=Path("/search"),
            output_dir=Path("/output"),
            symlinks_dir=Path("/symlinks"),
            storage_dir=Path("/storage"),
        )
        console = MagicMock()

        display_configuration(cli_args, console)

        call_args = console.print_panel.call_args[0][0]
        assert "FORCE" in call_args

    def test_displays_all_files_mode(self):
        """Displays 'all files' when process_all is True."""
        cli_args = CLIArgs(
            days_to_process=100000000.0,  # This triggers process_all
            dry_run=False,
            force_mode=False,
            search_dir=Path("/search"),
            output_dir=Path("/output"),
            symlinks_dir=Path("/symlinks"),
            storage_dir=Path("/storage"),
        )
        console = MagicMock()

        display_configuration(cli_args, console)

        call_args = console.print_panel.call_args[0][0]
        assert "Tous les fichiers" in call_args


class TestMain:
    """Tests for main function."""

    def test_main_invalid_directory(self, tmp_path):
        """Returns error code for invalid directory."""
        with patch("organize.__main__.parse_arguments") as mock_parse:
            mock_parse.return_value = MagicMock(
                all=False,
                day=0,
                dry_run=True,
                force=False,
                debug=False,
                tag="",
                input=str(tmp_path / "nonexistent"),
                output=str(tmp_path / "output"),
                symlinks=str(tmp_path / "symlinks"),
                storage=str(tmp_path / "storage"),
            )

            result = main()

            assert result == 1

    def test_main_success_dry_run(self, tmp_path):
        """Returns success for valid dry run."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        with patch("organize.__main__.parse_arguments") as mock_parse:
            mock_parse.return_value = MagicMock(
                all=False,
                day=7,
                dry_run=True,
                force=False,
                debug=False,
                tag="",
                input=str(input_dir),
                output=str(tmp_path / "output"),
                symlinks=str(tmp_path / "symlinks"),
                storage=str(tmp_path / "storage"),
            )

            result = main()

            assert result == 0

    def test_main_with_debug_tag(self, tmp_path):
        """Handles debug mode with tag."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        with patch("organize.__main__.parse_arguments") as mock_parse:
            mock_parse.return_value = MagicMock(
                all=False,
                day=7,
                dry_run=True,
                force=False,
                debug=True,
                tag="test_tag",
                input=str(input_dir),
                output=str(tmp_path / "output"),
                symlinks=str(tmp_path / "symlinks"),
                storage=str(tmp_path / "storage"),
            )

            result = main()

            assert result == 0
