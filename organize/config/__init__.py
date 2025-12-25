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
)
from organize.config.context import (
    ExecutionContext,
    get_context,
    set_context,
    execution_context,
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
    "ExecutionContext",
    "get_context",
    "set_context",
    "execution_context",
]
