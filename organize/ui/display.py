"""Display functions for video organization output."""

from typing import TYPE_CHECKING, Dict, List

from rich.tree import Tree
from rich.text import Text

from organize.ui.console import console

if TYPE_CHECKING:
    from organize.models.video import Video


def _extract_relative_path(video: "Video") -> str:
    """
    Extrait le chemin relatif de destination pour une vidéo.

    Essaie plusieurs sources dans l'ordre de priorité :
    1. sub_directory (chemin relatif explicite)
    2. complete_dir_symlinks (chemin complet des symlinks)
    3. complete_path_temp_links (chemin temporaire de travail)

    Pour les séries, ajoute le dossier série et saison si non présents.

    Args:
        video: Objet Video.

    Returns:
        Chemin relatif extrait ou chaîne vide si extraction impossible.
    """
    from pathlib import Path

    base_path = ""

    # 1. Utiliser sub_directory si défini (c'est le chemin relatif)
    if video.sub_directory and str(video.sub_directory).strip():
        sub_dir = str(video.sub_directory)
        if sub_dir and sub_dir != ".":
            base_path = sub_dir

    # 2. Extraire depuis complete_dir_symlinks
    if not base_path and isinstance(video.complete_dir_symlinks, Path) and video.complete_dir_symlinks.parts:
        parts = video.complete_dir_symlinks.parts
        # Chercher un pattern connu (Films, Séries, Animation, Docs)
        known_roots = {"Films", "Séries", "Animation", "Docs", "Docs#1"}
        for i, part in enumerate(parts):
            if part in known_roots:
                relative_parts = parts[i:]  # Du root connu jusqu'à la fin
                if relative_parts:
                    base_path = "/".join(relative_parts)
                    break

    # 3. Extraire depuis complete_path_temp_links
    if not base_path and isinstance(video.complete_path_temp_links, Path) and video.complete_path_temp_links.parts:
        parts = video.complete_path_temp_links.parts
        # Chercher le dossier "work" et prendre ce qui suit
        try:
            work_idx = parts.index("work")
            relative_parts = parts[work_idx + 1:-1]  # Exclure "work" et le nom de fichier
            if relative_parts:
                base_path = "/".join(relative_parts)
        except ValueError:
            pass

        # Fallback: chercher un pattern connu
        if not base_path:
            known_roots = {"Films", "Séries", "Animation", "Docs", "Docs#1"}
            for i, part in enumerate(parts):
                if part in known_roots:
                    relative_parts = parts[i:-1]  # Du root connu jusqu'au parent du fichier
                    if relative_parts:
                        base_path = "/".join(relative_parts)
                        break

    # Pour les séries, ajouter le dossier de la série et la saison si non présents
    if base_path and video.is_serie() and video.title_fr:
        # Construire le nom du dossier série
        series_folder = f"{video.title_fr} ({video.date_film})" if video.date_film else video.title_fr

        # Vérifier si le dossier série n'est pas déjà dans le chemin
        if series_folder not in base_path:
            base_path = f"{base_path}/{series_folder}"

        # Ajouter la saison si définie et non présente
        if video.season and video.season > 0:
            season_folder = f"Saison {video.season:02d}"
            if season_folder not in base_path:
                base_path = f"{base_path}/{season_folder}"

    return base_path


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

        # Extraire le chemin relatif depuis les différentes sources
        relative_path = _extract_relative_path(video)

        # Fallback basé sur le type et le genre
        if not relative_path:
            if video.is_film_anim():
                if video.genre == "Non détecté" or not video.genre:
                    relative_path = "Films/non détectés"
                else:
                    relative_path = f"Films/{video.genre}"
            elif video.is_serie():
                relative_path = "Séries/Séries TV"
            else:
                relative_path = video.type_file or "Autres"

        # Nettoyer le chemin
        relative_path = relative_path.strip("/") or "Racine"

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
