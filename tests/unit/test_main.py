"""Tests for the organize package entry point."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from organize.__main__ import (
    display_configuration,
    display_simulation_banner,
    display_statistics,
    main,
)
from organize.config import CLIArgs, ConfigurationManager
from organize.pipeline import ProcessingStats


class TestConfigurationManager:
    """Tests for ConfigurationManager class."""

    def test_setup_logging_default(self):
        """Sets up logging with default level."""
        manager = ConfigurationManager()
        with patch("organize.config.manager.logger") as mock_logger:
            manager.setup_logging(debug=False)
            mock_logger.remove.assert_called_once()
            assert mock_logger.add.call_count == 2

    def test_setup_logging_debug(self):
        """Sets up logging with debug level."""
        manager = ConfigurationManager()
        with patch("organize.config.manager.logger") as mock_logger:
            manager.setup_logging(debug=True)
            mock_logger.remove.assert_called_once()

    def test_parse_args_returns_cli_args(self):
        """parse_args returns CLIArgs instance."""
        manager = ConfigurationManager()
        args = manager.parse_args(["--dry-run"])
        assert isinstance(args, CLIArgs)
        assert args.dry_run is True

    def test_validate_input_directory_missing(self, tmp_path):
        """Returns invalid when directory doesn't exist."""
        manager = ConfigurationManager()
        manager.parse_args(["--input", str(tmp_path / "nonexistent")])
        result = manager.validate_input_directory()
        assert result.valid is False
        assert "does not exist" in result.error_message

    def test_validate_input_directory_exists(self, tmp_path):
        """Returns valid when directory exists."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        manager = ConfigurationManager()
        manager.parse_args(["--input", str(input_dir)])
        result = manager.validate_input_directory()
        assert result.valid is True


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


class TestDisplayStatistics:
    """Tests for display_statistics function."""

    def test_displays_stats(self):
        """Displays processing statistics."""
        stats = ProcessingStats(
            films=5,
            series=3,
            animation=2,
            docs=1,
            undetected=0,
            total=11
        )
        console = MagicMock()

        display_statistics(stats, dry_run=False, console=console)

        console.print_panel.assert_called_once()
        call_args = console.print_panel.call_args[0][0]
        assert "5" in call_args  # films count
        assert "11" in call_args  # total

    def test_displays_simulation_message(self):
        """Displays simulation message in dry run mode."""
        stats = ProcessingStats(total=5)
        console = MagicMock()

        display_statistics(stats, dry_run=True, console=console)

        # Check that simulation message was printed
        calls = [str(c) for c in console.print.call_args_list]
        assert any("simulation" in c.lower() for c in calls)


class TestMain:
    """Tests for main function."""

    def test_main_invalid_directory(self, tmp_path):
        """Returns error code for invalid directory."""
        with patch("organize.config.manager.parse_arguments") as mock_parse:
            mock_parse.return_value = MagicMock(
                all=False,
                day=0,
                dry_run=True,
                force=False,
                debug=False,
                tag="",
                legacy=False,
                input=str(tmp_path / "nonexistent"),
                output=str(tmp_path / "output"),
                symlinks=str(tmp_path / "symlinks"),
                storage=str(tmp_path / "storage"),
            )

            result = main()

            assert result == 1

    def test_main_success_dry_run(self, tmp_path):
        """Returns success for valid dry run with proper category structure."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # Create required category subdirectory
        (input_dir / "Films").mkdir()

        with patch("organize.config.manager.parse_arguments") as mock_parse, \
             patch("organize.config.manager.check_api_keys", return_value=True), \
             patch("organize.config.manager.test_api_connectivity", return_value=True):
            mock_parse.return_value = MagicMock(
                all=False,
                day=7,
                dry_run=True,
                force=False,
                debug=False,
                tag="",
                legacy=False,
                input=str(input_dir),
                output=str(tmp_path / "output"),
                symlinks=str(tmp_path / "symlinks"),
                storage=str(tmp_path / "storage"),
            )

            result = main()

            # Returns 0 even with no videos (empty category is valid)
            assert result == 0

    def test_main_with_debug_tag(self, tmp_path):
        """Handles debug mode with tag and proper category structure."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # Create required category subdirectory
        (input_dir / "Films").mkdir()

        with patch("organize.config.manager.parse_arguments") as mock_parse, \
             patch("organize.config.manager.check_api_keys", return_value=True), \
             patch("organize.config.manager.test_api_connectivity", return_value=True):
            mock_parse.return_value = MagicMock(
                all=False,
                day=7,
                dry_run=True,
                force=False,
                debug=True,
                tag="test_tag",
                legacy=False,
                input=str(input_dir),
                output=str(tmp_path / "output"),
                symlinks=str(tmp_path / "symlinks"),
                storage=str(tmp_path / "storage"),
            )

            result = main()

            assert result == 0
