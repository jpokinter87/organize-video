"""Command-line interface argument parsing."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger

from organize.config.settings import (
    DEFAULT_SEARCH_DIR,
    DEFAULT_STORAGE_DIR,
    DEFAULT_SYMLINKS_DIR,
    DEFAULT_TEMP_SYMLINKS_DIR,
    PROCESS_ALL_FILES_DAYS,
)


@dataclass
class CLIArgs:
    """
    Parsed command-line arguments.

    Attributes:
        days_to_process: Number of days of files to process (0 for default).
        dry_run: If True, simulate without making changes.
        force_mode: If True, skip duplicate checks.
        debug: If True, enable debug mode.
        tag: Debug tag to search for.
        search_dir: Directory to search for videos.
        output_dir: Temporary output directory.
        symlinks_dir: Final symlinks directory.
        storage_dir: Final storage directory.
    """

    days_to_process: float = 0
    dry_run: bool = False
    force_mode: bool = False
    debug: bool = False
    tag: str = ""
    search_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    symlinks_dir: Optional[Path] = None
    storage_dir: Optional[Path] = None

    @property
    def process_all(self) -> bool:
        """Check if processing all files (no date filter)."""
        return self.days_to_process >= PROCESS_ALL_FILES_DAYS


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog='organize_video',
        description="""
        Scans directory and organizes video files by creating symbolic links
        in a structure organized by genre and alphabetical order.
        """
    )

    # Day/all mutually exclusive group
    day_group = parser.add_mutually_exclusive_group()

    day_group.add_argument(
        '-a', '--all',
        action='store_true',
        help='process all files regardless of date'
    )

    day_group.add_argument(
        '-d', '--day',
        type=float,
        default=0,
        help='only process files less than DAY days old'
    )

    # Directory arguments
    parser.add_argument(
        '-i', '--input',
        default=str(DEFAULT_SEARCH_DIR),
        help=f"source directory (default: {DEFAULT_SEARCH_DIR})"
    )

    parser.add_argument(
        '-o', '--output',
        default=str(DEFAULT_TEMP_SYMLINKS_DIR),
        help=f"temporary symlink destination (default: {DEFAULT_TEMP_SYMLINKS_DIR})"
    )

    parser.add_argument(
        '-s', '--symlinks',
        default=str(DEFAULT_SYMLINKS_DIR),
        help=f"final symlink destination (default: {DEFAULT_SYMLINKS_DIR})"
    )

    parser.add_argument(
        '--storage',
        default=str(DEFAULT_STORAGE_DIR),
        help=f"final file storage directory (default: {DEFAULT_STORAGE_DIR})"
    )

    # Mode flags
    parser.add_argument(
        '--force',
        action='store_true',
        help="skip hash verification (development mode)"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="simulation mode - no file modifications (recommended for testing)"
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help="enable debug mode"
    )

    parser.add_argument(
        '--tag',
        nargs='?',
        default='',
        help="tag to search for in debug mode"
    )

    return parser


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings (None for sys.argv).

    Returns:
        Parsed Namespace object.
    """
    parser = create_parser()
    return parser.parse_args(args)


def validate_directories(
    input_dir: Path,
    output_dir: Path,
    symlinks_dir: Optional[Path] = None,
    storage_dir: Optional[Path] = None,
    dry_run: bool = False
) -> bool:
    """
    Validate and optionally create directories.

    Args:
        input_dir: Input directory (must exist).
        output_dir: Output directory.
        symlinks_dir: Symlinks directory.
        storage_dir: Storage directory.
        dry_run: If True, skip directory creation.

    Returns:
        True if validation passed, False otherwise.
    """
    # Input must exist
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return False

    # Create output directories if not dry run
    if not dry_run:
        dirs_to_create = [output_dir]
        if symlinks_dir:
            dirs_to_create.append(symlinks_dir)
        if storage_dir:
            dirs_to_create.append(storage_dir)

        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)

    return True


def args_to_cli_args(namespace: argparse.Namespace) -> CLIArgs:
    """
    Convert argparse Namespace to CLIArgs dataclass.

    Args:
        namespace: Parsed argparse Namespace.

    Returns:
        CLIArgs instance.
    """
    # Determine days to process
    if namespace.all:
        days = PROCESS_ALL_FILES_DAYS
    elif namespace.day != 0:
        days = namespace.day
    else:
        days = 0

    return CLIArgs(
        days_to_process=days,
        dry_run=namespace.dry_run,
        force_mode=namespace.force,
        debug=namespace.debug,
        tag=namespace.tag or "",
        search_dir=Path(namespace.input),
        output_dir=Path(namespace.output),
        symlinks_dir=Path(namespace.symlinks),
        storage_dir=Path(namespace.storage),
    )
