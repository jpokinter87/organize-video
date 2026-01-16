"""Composants d'interface utilisateur."""

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
from organize.ui.interactive import (
    launch_video_player,
    wait_for_user_after_viewing,
    choose_genre_manually,
    user_confirms_match,
    handle_not_found_error,
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
    "launch_video_player",
    "wait_for_user_after_viewing",
    "choose_genre_manually",
    "user_confirms_match",
    "handle_not_found_error",
]
