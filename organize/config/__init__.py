"""Configuration and CLI handling."""

from organize.config.settings import (
    EXT_VIDEO,
    ALL_EXTENSIONS,
    CATEGORIES,
    FILMANIM,
    FILMSERIE,
    NOT_DOC,
    GENRES,
    PRIORITY_GENRES,
    DEFAULT_SEARCH_DIR,
    DEFAULT_STORAGE_DIR,
    DEFAULT_SYMLINKS_DIR,
    DEFAULT_TEMP_SYMLINKS_DIR,
    PROCESS_ALL_FILES_DAYS,
)
from organize.config.context import (
    ExecutionContext,
    get_context,
    set_context,
    execution_context,
)
from organize.config.cli import (
    CLIArgs,
    create_parser,
    parse_arguments,
    validate_directories,
    args_to_cli_args,
)
from organize.config.manager import (
    ConfigurationManager,
    ValidationResult,
)

__all__ = [
    "EXT_VIDEO",
    "ALL_EXTENSIONS",
    "CATEGORIES",
    "FILMANIM",
    "FILMSERIE",
    "NOT_DOC",
    "GENRES",
    "PRIORITY_GENRES",
    "DEFAULT_SEARCH_DIR",
    "DEFAULT_STORAGE_DIR",
    "DEFAULT_SYMLINKS_DIR",
    "DEFAULT_TEMP_SYMLINKS_DIR",
    "PROCESS_ALL_FILES_DAYS",
    "ExecutionContext",
    "get_context",
    "set_context",
    "execution_context",
    "CLIArgs",
    "create_parser",
    "parse_arguments",
    "validate_directories",
    "args_to_cli_args",
    "ConfigurationManager",
    "ValidationResult",
]
