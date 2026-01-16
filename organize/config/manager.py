"""Configuration management for video organization."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from organize.config.cli import CLIArgs, parse_arguments, args_to_cli_args
from organize.config.settings import CATEGORIES


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    error_message: Optional[str] = None


class ConfigurationManager:
    """
    Manages application configuration and validation.

    Centralizes configuration parsing, validation, and setup
    to reduce coupling in the main entry point.
    """

    def __init__(self):
        """Initialize configuration manager."""
        self._cli_args: Optional[CLIArgs] = None
        self._console = None

    @property
    def cli_args(self) -> CLIArgs:
        """Get parsed CLI arguments."""
        if self._cli_args is None:
            raise RuntimeError("Configuration not initialized. Call parse_args() first.")
        return self._cli_args

    def parse_args(self, args: Optional[list] = None) -> CLIArgs:
        """
        Parse command-line arguments.

        Args:
            args: Optional list of arguments (defaults to sys.argv).

        Returns:
            Parsed CLIArgs instance.
        """
        namespace = parse_arguments(args)
        self._cli_args = args_to_cli_args(namespace)
        return self._cli_args

    def setup_logging(self, debug: bool = False) -> None:
        """
        Configure logging with loguru.

        Args:
            debug: Enable debug level logging if True.
        """
        logger.remove()

        # File logging
        logger.add(
            "organize.log",
            rotation="100 MB",
            level="DEBUG" if debug else "INFO"
        )

        # Console logging
        logger.add(
            sys.stderr,
            level="DEBUG" if debug else "WARNING"
        )

    def validate_input_directory(self) -> ValidationResult:
        """
        Validate input directory exists.

        Returns:
            ValidationResult with status and optional error message.
        """
        if not self.cli_args.search_dir.exists():
            return ValidationResult(
                valid=False,
                error_message=f"Input directory {self.cli_args.search_dir} does not exist"
            )
        return ValidationResult(valid=True)

    def validate_api_keys(self) -> ValidationResult:
        """
        Validate API keys are present.

        Returns:
            ValidationResult with status and optional error message.
        """
        from organize.api import validate_api_keys as check_keys

        if not check_keys():
            return ValidationResult(
                valid=False,
                error_message="Cles API manquantes (TMDB_API_KEY, TVDB_API_KEY)"
            )
        return ValidationResult(valid=True)

    def validate_api_connectivity(self) -> ValidationResult:
        """
        Validate API connectivity.

        Returns:
            ValidationResult with status and optional error message.
        """
        from organize.api import test_api_connectivity

        if not test_api_connectivity():
            return ValidationResult(
                valid=False,
                error_message="Impossible de se connecter aux APIs"
            )
        return ValidationResult(valid=True)

    def validate_categories(self) -> Tuple[ValidationResult, list]:
        """
        Validate category structure in search directory.

        Returns:
            Tuple of (ValidationResult, list of available categories).
        """
        from organize.filesystem import get_available_categories

        available = get_available_categories(self.cli_args.search_dir)
        if not available:
            return (
                ValidationResult(
                    valid=False,
                    error_message=f"Aucune categorie trouvee dans {self.cli_args.search_dir}. "
                                  f"Categories attendues: {', '.join(CATEGORIES)}"
                ),
                []
            )
        return ValidationResult(valid=True), available

    def validate_all(self) -> ValidationResult:
        """
        Run all validations.

        Returns:
            ValidationResult with first failure or success.
        """
        validations = [
            self.validate_input_directory,
            self.validate_api_keys,
            self.validate_api_connectivity,
        ]

        for validation in validations:
            result = validation()
            if not result.valid:
                return result

        cat_result, _ = self.validate_categories()
        return cat_result

    def setup_working_directories(self) -> Tuple[Path, Path, Path, Path]:
        """
        Setup working directories for processing.

        Returns:
            Tuple of (work_dir, temp_dir, original_dir, waiting_folder).
        """
        from organize.filesystem import setup_working_directories

        return setup_working_directories(
            self.cli_args.output_dir,
            self.cli_args.dry_run
        )

    def get_video_count(self) -> int:
        """
        Count videos in search directory.

        Returns:
            Number of videos found.
        """
        from organize.filesystem import count_videos

        return count_videos(self.cli_args.search_dir)

    def flatten_series_directories(self) -> None:
        """Flatten series directories if not in dry run mode."""
        from organize.filesystem import aplatir_repertoire_series

        if not self.cli_args.dry_run:
            aplatir_repertoire_series(self.cli_args.search_dir)
