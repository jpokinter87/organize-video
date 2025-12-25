"""User confirmation and input handling."""

from enum import Enum, auto
from typing import List, Optional

from rich.panel import Panel
from rich.columns import Columns

from organize.ui.console import console


class ConfirmationResult(Enum):
    """Result of a user confirmation prompt."""
    ACCEPT = auto()
    REJECT = auto()
    MANUAL = auto()
    VIEW = auto()
    UNKNOWN = auto()


def parse_user_response(response: str) -> ConfirmationResult:
    """
    Parse user response string into a ConfirmationResult.

    Args:
        response: Raw user input string.

    Returns:
        ConfirmationResult enum value.
    """
    response = response.strip().lower()

    # Accept responses
    if response in ('', 'y', 'yes', 'oui', 'o'):
        return ConfirmationResult.ACCEPT

    # Reject responses
    if response in ('n', 'no', 'non'):
        return ConfirmationResult.REJECT

    # Manual input responses
    if response in ('m', 'manual', 'manuel'):
        return ConfirmationResult.MANUAL

    # View video responses
    if response in ('v', 'view', 'visionner'):
        return ConfirmationResult.VIEW

    return ConfirmationResult.UNKNOWN


def get_available_genres() -> List[str]:
    """
    Get list of available genres for selection.

    Returns:
        List of genre strings.
    """
    return [
        "Action & Aventure",
        "Animation",
        "Comédie",
        "Comédie dramatique",
        "Policier",
        "Drame",
        "Films pour enfants",
        "Fantastique",
        "Historique",
        "Horreur",
        "SF",
        "Thriller",
        "Western",
        "Guerre & espionnage",
        "Non détecté",
    ]


def validate_genre_selection(selection: str, genres: List[str]) -> Optional[str]:
    """
    Validate a genre selection by number.

    Args:
        selection: User input (should be a number).
        genres: List of available genres.

    Returns:
        Selected genre string, or None if invalid.
    """
    try:
        index = int(selection)
        if 1 <= index <= len(genres):
            return genres[index - 1]
    except ValueError:
        pass
    return None


def display_match_confirmation(
    original_filename: str,
    matched_title: str,
    matched_year: Optional[int],
    genres: List[str],
    can_view: bool = False
) -> None:
    """
    Display match confirmation dialog.

    Args:
        original_filename: Original video filename.
        matched_title: Matched title from API.
        matched_year: Matched year.
        genres: List of matched genres.
        can_view: Whether video viewing is available.
    """
    console.rule("[bold blue]Match Verification[/bold blue]")

    # Original file panel
    console.print_panel(
        f"[yellow]{original_filename}[/yellow]",
        title="📁 Original file",
        border_style="yellow"
    )

    # Match found panel
    genres_str = ", ".join(genres) if genres else "No genre"
    console.print_panel(
        f"[green]🎬 Title:[/green] [bold]{matched_title}[/bold]\n"
        f"[blue]📅 Year:[/blue] [bold]{matched_year if matched_year else 'N/A'}[/bold]\n"
        f"[purple]🎭 Genres:[/purple] [italic]{genres_str}[/italic]",
        title="✅ Match found",
        border_style="green"
    )

    # Options
    console.print("\n[bold cyan]Is this match correct?[/bold cyan]")

    options_text = (
        "[bold green]Enter[/bold green] = [green]ACCEPT[/green]\n"
        "[bold yellow]m[/bold yellow] = [yellow]MANUAL INPUT[/yellow]\n"
    )

    if can_view:
        options_text += "[bold magenta]v[/bold magenta] = [magenta]VIEW VIDEO[/magenta]\n"

    options_text += "[bold red]n[/bold red] = [red]NO[/red] (try next match)"

    console.print_panel(options_text, title="🎛️  Options", border_style="cyan")


def display_genre_selection() -> None:
    """Display genre selection menu."""
    genres = get_available_genres()

    console.print("\n[bold cyan]📂 Genre selection:[/bold cyan]")

    genre_panels = []
    for i, genre in enumerate(genres, 1):
        color = "green" if genre != "Non détecté" else "yellow"
        genre_panels.append(
            Panel(f"[{color}]{i:2d}. {genre}[/{color}]", expand=False)
        )

    console.print(Columns(genre_panels, equal=False, expand=False))
