"""Display functions for video organization output."""

from typing import TYPE_CHECKING, Dict, List

from rich.tree import Tree
from rich.text import Text

from organize.ui.console import console

if TYPE_CHECKING:
    from organize.models.video import Video


def generate_tree_structure(videos: List["Video"]) -> Dict[str, List[str]]:
    """
    Generate a simulation of the tree structure to be created.

    Args:
        videos: List of Video objects to organize.

    Returns:
        Dict mapping folder paths to lists of filenames.
    """
    tree_structure: Dict[str, List[str]] = {}

    for video in videos:
        if not video.formatted_filename:
            continue

        # Construire le chemin relatif
        if video.sub_directory:
            relative_path = str(video.sub_directory)
        else:
            if video.is_film_anim():
                if video.genre == "Non détecté":
                    relative_path = "Films/non détectés"
                else:
                    relative_path = f"Films/{video.genre}"
            elif video.is_serie():
                relative_path = "Séries/Séries TV"
            else:
                relative_path = video.type_file

        # Ajouter à la structure
        if relative_path not in tree_structure:
            tree_structure[relative_path] = []
        tree_structure[relative_path].append(video.formatted_filename)

    return tree_structure


def display_tree(
    tree_structure: Dict[str, List[str]],
    max_files_per_folder: int = 5
) -> None:
    """
    Display a simulated tree structure elegantly.

    Args:
        tree_structure: Dict mapping folder paths to file lists.
        max_files_per_folder: Maximum files to show per folder.
    """
    root_tree = Tree("📁 [bold cyan]Simulated symlink structure[/bold cyan]")

    sorted_folders = sorted(tree_structure.keys())

    for folder_path in sorted_folders:
        files = tree_structure[folder_path]

        # Style du nœud de dossier
        folder_icon = "📁" if "non détectés" not in folder_path else "❓"
        folder_color = "yellow" if "non détectés" in folder_path else "cyan"

        folder_node = root_tree.add(
            f"{folder_icon} [bold {folder_color}]{folder_path}[/bold {folder_color}] "
            f"[dim]({format_file_count(len(files))})[/dim]"
        )

        # Ajouter les fichiers (limité pour éviter l'encombrement)
        displayed_files = files[:max_files_per_folder]

        for file in displayed_files:
            # Icône basée sur le type de fichier
            if file.endswith(('.mkv', '.avi', '.mp4')):
                if 'S0' in file and 'E0' in file:
                    icon = "📺"
                else:
                    icon = "🎬"
            else:
                icon = "📄"

            folder_node.add(f"{icon} [dim]{file}[/dim]")

        # Afficher le nombre restant si tronqué
        remaining = len(files) - max_files_per_folder
        if remaining > 0:
            folder_node.add(f"[dim]... et {remaining} autres fichiers[/dim]")

    console.print(root_tree)


def format_file_count(count: int) -> str:
    """
    Format file count with proper French pluralization.

    Args:
        count: Number of files.

    Returns:
        Formatted string like "5 fichiers" or "1 fichier".
    """
    return f"{count} fichier{'s' if count > 1 else ''}"


def get_category_stats(
    videos: List["Video"],
    by_genre: bool = False
) -> Dict[str, int]:
    """
    Get statistics by category or genre.

    Args:
        videos: List of Video objects.
        by_genre: If True, count by genre instead of type.

    Returns:
        Dict mapping category/genre to count.
    """
    stats: Dict[str, int] = {}

    for video in videos:
        key = video.genre if by_genre else video.type_file
        stats[key] = stats.get(key, 0) + 1

    return stats


def display_statistics(videos: List["Video"]) -> None:
    """
    Display processing statistics.

    Args:
        videos: List of processed Video objects.
    """
    if not videos:
        console.print_warning("No videos to display statistics for.")
        return

    console.rule("[bold blue]Processing Statistics[/bold blue]")

    # Statistiques par catégorie
    category_stats = get_category_stats(videos)
    table = console.create_table("By Category", ["Category", "Count"])
    for cat, count in sorted(category_stats.items()):
        table.add_row(cat, str(count))
    console.print_table(table)

    # Statistiques par genre
    genre_stats = get_category_stats(videos, by_genre=True)
    table = console.create_table("By Genre", ["Genre", "Count"])
    for genre, count in sorted(genre_stats.items(), key=lambda x: -x[1]):
        table.add_row(genre, str(count))
    console.print_table(table)


def display_summary(
    total_processed: int,
    successful: int,
    failed: int,
    dry_run: bool = False
) -> None:
    """
    Display final processing summary.

    Args:
        total_processed: Total videos processed.
        successful: Number of successful operations.
        failed: Number of failed operations.
        dry_run: Whether this was a dry run.
    """
    mode_text = "[dim](SIMULATION)[/dim]" if dry_run else ""

    console.rule(f"[bold green]Summary {mode_text}[/bold green]")
    console.print(f"[blue]Total processed:[/blue] {total_processed}")
    console.print(f"[green]Successful:[/green] {successful}")
    if failed > 0:
        console.print(f"[red]Failed:[/red] {failed}")
