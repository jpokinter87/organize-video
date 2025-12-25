"""Tests for CLI argument parsing."""

import pytest
from pathlib import Path
from unittest.mock import patch

from organize.config.cli import (
    create_parser,
    parse_arguments,
    validate_directories,
    CLIArgs,
)


class TestCreateParser:
    """Tests for create_parser function."""

    def test_creates_parser(self):
        """Creates an ArgumentParser."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "organize_video"

    def test_has_required_arguments(self):
        """Parser has all required arguments."""
        parser = create_parser()
        # Parse with defaults
        args = parser.parse_args([])

        assert hasattr(args, 'all')
        assert hasattr(args, 'day')
        assert hasattr(args, 'input')
        assert hasattr(args, 'output')
        assert hasattr(args, 'symlinks')
        assert hasattr(args, 'storage')
        assert hasattr(args, 'force')
        assert hasattr(args, 'dry_run')
        assert hasattr(args, 'debug')


class TestParseArguments:
    """Tests for parse_arguments function."""

    def test_default_values(self):
        """Returns correct default values."""
        args = parse_arguments([])

        assert args.all is False
        assert args.day == 0
        assert args.force is False
        assert args.dry_run is False
        assert args.debug is False

    def test_all_flag(self):
        """--all flag sets all to True."""
        args = parse_arguments(['--all'])
        assert args.all is True

    def test_day_argument(self):
        """--day sets day value."""
        args = parse_arguments(['--day', '7'])
        assert args.day == 7.0

    def test_force_flag(self):
        """--force flag sets force to True."""
        args = parse_arguments(['--force'])
        assert args.force is True

    def test_dry_run_flag(self):
        """--dry-run flag sets dry_run to True."""
        args = parse_arguments(['--dry-run'])
        assert args.dry_run is True

    def test_debug_flag(self):
        """--debug flag sets debug to True."""
        args = parse_arguments(['--debug'])
        assert args.debug is True

    def test_input_path(self):
        """--input sets input path."""
        args = parse_arguments(['--input', '/custom/input'])
        assert args.input == '/custom/input'

    def test_output_path(self):
        """--output sets output path."""
        args = parse_arguments(['--output', '/custom/output'])
        assert args.output == '/custom/output'

    def test_all_and_day_mutually_exclusive(self):
        """--all and --day are mutually exclusive."""
        with pytest.raises(SystemExit):
            parse_arguments(['--all', '--day', '7'])


class TestValidateDirectories:
    """Tests for validate_directories function."""

    def test_validates_existing_input(self, tmp_path):
        """Validates existing input directory."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        result = validate_directories(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            dry_run=True
        )

        assert result is True

    def test_fails_on_missing_input(self, tmp_path):
        """Fails when input directory doesn't exist."""
        result = validate_directories(
            input_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
            dry_run=True
        )

        assert result is False

    def test_creates_output_when_not_dry_run(self, tmp_path):
        """Creates output directory when not in dry run."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        validate_directories(
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=False
        )

        assert output_dir.exists()

    def test_skips_creation_in_dry_run(self, tmp_path):
        """Skips directory creation in dry run mode."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        validate_directories(
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=True
        )

        assert not output_dir.exists()


class TestCLIArgs:
    """Tests for CLIArgs dataclass."""

    def test_default_values(self):
        """Creates with default values."""
        args = CLIArgs()

        assert args.days_to_process == 0
        assert args.dry_run is False
        assert args.force_mode is False
        assert args.debug is False

    def test_custom_values(self):
        """Creates with custom values."""
        args = CLIArgs(
            days_to_process=7.0,
            dry_run=True,
            force_mode=True,
            search_dir=Path("/search"),
            storage_dir=Path("/storage"),
        )

        assert args.days_to_process == 7.0
        assert args.dry_run is True
        assert args.force_mode is True
        assert args.search_dir == Path("/search")

    def test_process_all_property(self):
        """process_all returns True for large day value."""
        args = CLIArgs(days_to_process=100000000.0)
        assert args.process_all is True

        args = CLIArgs(days_to_process=7.0)
        assert args.process_all is False
