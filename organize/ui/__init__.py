"""User interface components."""

from organize.ui.console import ConsoleUI, console
from organize.ui.display import (
    generate_tree_structure,
    display_tree,
    format_file_count,
    get_category_stats,
    display_statistics,
    display_summary,
)
from organize.ui.confirmations import (
    ConfirmationResult,
    parse_user_response,
    get_available_genres,
    validate_genre_selection,
    display_match_confirmation,
    display_genre_selection,
)

__all__ = [
    "ConsoleUI",
    "console",
    "generate_tree_structure",
    "display_tree",
    "format_file_count",
    "get_category_stats",
    "display_statistics",
    "display_summary",
    "ConfirmationResult",
    "parse_user_response",
    "get_available_genres",
    "validate_genre_selection",
    "display_match_confirmation",
    "display_genre_selection",
]
