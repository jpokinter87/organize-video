"""Entry point for the organize video package.

This module provides the command-line entry point for the video organization tool.
Run with: python -m organize

Supports:
- Modern modular mode (default): Uses refactored modules with gap imports
- Legacy mode (--legacy flag): Delegates entirely to organize.py
"""

import sys
from pathlib import Path
from typing import Optional, Any, Callable

from loguru import logger

# ============================================================================
# MODULAR IMPORTS (Available Components)
# ============================================================================
from organize.config import (
    CLIArgs,
    parse_arguments,
    args_to_cli_args,
    validate_directories,
    CATEGORIES,
    PROCESS_ALL_FILES_DAYS,
)
from organize.config.context import execution_context
from organize.models import Video
from organize.api import CacheDB, validate_api_keys, test_api_connectivity
from organize.classification import media_info, format_undetected_filename
from organize.filesystem import (
    get_available_categories,
    count_videos,
    copy_tree,
    verify_symlinks,
    setup_working_directories,
    find_directory_for_video,
    find_symlink_and_sub_dir,
    find_similar_file,
    aplatir_repertoire_series,
    rename_video,
    move_file_new_nas,
    cleanup_directories,
    cleanup_work_directory,
)
from organize.ui import ConsoleUI

# ============================================================================
# GAP FUNCTIONS LOADER (Temporary - from organize.py)
# ============================================================================
# These will be removed progressively as modules are completed
_organize_module = None  # Lazy-loaded module reference


def _load_organize_module():
    """Lazy-load organize.py module for gap functions."""
    global _organize_module
    if _organize_module is None:
        import importlib.util
        organize_py = Path(__file__).parent.parent / "organize.py"
        if not organize_py.exists():
            raise FileNotFoundError(f"organize.py not found at {organize_py}")

        # Add parent directory to path for imports
        parent_dir = str(organize_py.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        spec = importlib.util.spec_from_file_location("organize_original", organize_py)
        _organize_module = importlib.util.module_from_spec(spec)
        # Register module in sys.modules so multiprocessing can pickle functions
        sys.modules["organize_original"] = _organize_module
        spec.loader.exec_module(_organize_module)
    return _organize_module


def _get_gap_function(name: str) -> Callable:
    """Get a gap function from organize.py."""
    module = _load_organize_module()
    func = getattr(module, name, None)
    if func is None:
        raise AttributeError(f"Function '{name}' not found in organize.py")
    return func


# ============================================================================
# GAP FUNCTION WRAPPERS
# These are temporary and will be replaced by modular implementations
# Each wrapper is marked with [GAP] to identify migration targets
# ============================================================================

# MIGRATED: validate_api_keys -> organize.api.validation
# MIGRATED: test_api_connectivity -> organize.api.validation
# MIGRATED: media_info -> organize.classification.media_info
# MIGRATED: find_directory_for_video -> organize.filesystem.paths
# MIGRATED: find_symlink_and_sub_dir -> organize.filesystem.paths
# MIGRATED: find_similar_file -> organize.filesystem.paths
# MIGRATED: aplatir_repertoire_series -> organize.filesystem.file_ops
# MIGRATED: rename_video -> organize.filesystem.file_ops
# MIGRATED: move_file_new_nas -> organize.filesystem.file_ops
# MIGRATED: cleanup_directories -> organize.filesystem.file_ops
# MIGRATED: cleanup_work_directory -> organize.filesystem.file_ops
# MIGRATED: format_undetected_filename -> organize.classification.text_processing
# MIGRATED: extract_title_from_filename -> organize.classification.text_processing
# MIGRATED: launch_video_player -> organize.ui.interactive
# MIGRATED: wait_for_user_after_viewing -> organize.ui.interactive
# MIGRATED: choose_genre_manually -> organize.ui.interactive
# MIGRATED: user_confirms_match -> organize.ui.interactive
# MIGRATED: handle_not_found_error -> organize.ui.interactive

def set_fr_title_and_category(video: Video) -> Video:
    """[GAP] Set French title and category."""
    return _get_gap_function("set_fr_title_and_category")(video)


def create_video_list(
    search_dir: Path,
    days_to_manage: float,
    temp_dir: Path,
    storage_dir: Path,
    force_mode: bool,
    dry_run: bool,
    use_multiprocessing: bool = True
) -> list:
    """[GAP] Create list of videos to process."""
    return _get_gap_function("create_video_list")(
        search_dir, days_to_manage, temp_dir, storage_dir,
        force_mode, dry_run, use_multiprocessing
    )


def process_video(video: Video, waiting_folder: Path, storage_dir: Path, symlinks_dir: Path):
    """[GAP] Process a single video for duplicates."""
    return _get_gap_function("process_video")(video, waiting_folder, storage_dir, symlinks_dir)


def add_episodes_titles(series_videos: list, work_dir: Path, dry_run: bool) -> None:
    """[GAP] Add episode titles for series."""
    return _get_gap_function("add_episodes_titles")(series_videos, work_dir, dry_run)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def setup_logging(debug: bool = False) -> None:
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


def display_configuration(cli_args: CLIArgs, console: ConsoleUI) -> None:
    """
    Display configuration panel in console.

    Args:
        cli_args: Parsed CLI arguments.
        console: Console UI instance.
    """
    # Build mode status
    mode_parts = []
    if cli_args.force_mode:
        mode_parts.append("[red]FORCE[/red]")
    if cli_args.dry_run:
        mode_parts.append("[yellow]SIMULATION[/yellow]")
    mode_status = " ".join(mode_parts) if mode_parts else "[green]Normal[/green]"

    # Build period display
    if cli_args.process_all:
        period = "Tous les fichiers"
    else:
        period = f"{cli_args.days_to_process} derniers jours"

    config_text = (
        f"[bold]Configuration du traitement[/bold]\n"
        f"Repertoire source: [cyan]{cli_args.search_dir}[/cyan]\n"
        f"Repertoire de stockage: [cyan]{cli_args.storage_dir}[/cyan]\n"
        f"Repertoire des symlinks: [cyan]{cli_args.symlinks_dir}[/cyan]\n"
        f"Repertoire temporaire: [cyan]{cli_args.output_dir}[/cyan]\n"
        f"Periode: {period}\n"
        f"Mode: {mode_status}"
    )

    console.print_panel(config_text, title="Organisateur de Videotheque")


def display_simulation_banner(console: ConsoleUI) -> None:
    """Display simulation mode banner."""
    console.print_panel(
        "[bold yellow]MODE SIMULATION ACTIVE[/bold yellow]\n\n"
        "- Aucune modification ne sera apportee aux fichiers\n"
        "- Toutes les operations seront simulees et loggees\n"
        "- Les fichiers originaux restent intacts\n"
        "- Parfait pour tester le comportement du script",
        title="Mode Test",
        border_style="yellow"
    )


# ============================================================================
# LEGACY MODE SUPPORT
# ============================================================================

def run_legacy_mode() -> int:
    """
    Run in legacy mode by delegating to organize.py main().

    Returns:
        Exit code from legacy main().
    """
    logger.info("Running in legacy mode (organize.py)")
    console = ConsoleUI()
    console.print("[yellow]Mode legacy active - utilisation de organize.py[/yellow]")

    try:
        organize_module = _load_organize_module()
        organize_module.main()
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interruption par l'utilisateur[/yellow]")
        return 130
    except Exception as e:
        logger.error(f"Legacy mode error: {e}")
        console.print(f"[red]Erreur mode legacy: {e}[/red]")
        return 1


def check_legacy_flag() -> bool:
    """Check if --legacy flag is in arguments."""
    return "--legacy" in sys.argv


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main() -> int:
    """
    Main entry point for the video organization tool.

    Supports two modes:
    - Modern mode (default): Uses modular components with gap imports
    - Legacy mode (--legacy): Delegates entirely to organize.py

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Check for legacy mode first (before parsing other arguments)
    if check_legacy_flag():
        # Remove --legacy from argv before delegating
        sys.argv = [arg for arg in sys.argv if arg != "--legacy"]
        return run_legacy_mode()

    try:
        # Parse arguments using modular parser
        namespace = parse_arguments()
        cli_args = args_to_cli_args(namespace)

        # Setup logging
        setup_logging(debug=cli_args.debug)

        # Validate input directory
        if not cli_args.search_dir.exists():
            logger.error(f"Input directory {cli_args.search_dir} does not exist")
            return 1

        # Create console UI
        console = ConsoleUI()

        # Display simulation banner if needed
        if cli_args.dry_run:
            display_simulation_banner(console)

        # Display configuration
        display_configuration(cli_args, console)

        # Validate API keys [MODULAR]
        if not validate_api_keys():
            console.print("[red]Erreur: Cles API manquantes (TMDB_API_KEY, TVDB_API_KEY)[/red]")
            return 1

        # Test API connectivity [MODULAR]
        if not test_api_connectivity():
            console.print("[red]Erreur: Impossible de se connecter aux APIs[/red]")
            return 1

        # Setup working directories [MODULAR]
        work_dir, temp_dir, original_dir, waiting_folder = setup_working_directories(
            cli_args.output_dir,
            cli_args.dry_run
        )

        # Validate category structure [MODULAR]
        available_categories = get_available_categories(cli_args.search_dir)
        if not available_categories:
            console.print(f"[red]Aucune categorie trouvee dans {cli_args.search_dir}[/red]")
            console.print(f"[yellow]Categories attendues: {', '.join(CATEGORIES)}[/yellow]")
            return 1

        console.print(f"[green]Categories detectees: {', '.join([cat.name for cat in available_categories])}[/green]")

        # Count videos [MODULAR]
        nb_videos = count_videos(cli_args.search_dir)
        if nb_videos == 0:
            console.print("[yellow]Aucune video a traiter[/yellow]")
            return 0

        console.print(f"\n[bold green]{nb_videos} videos detectees[/bold green]")

        # Flatten series directories [MODULAR]
        if not cli_args.dry_run:
            console.print("[blue]Aplatissement des repertoires series...[/blue]")
            aplatir_repertoire_series(cli_args.search_dir)
        else:
            console.print("[dim]SIMULATION - Aplatissement des repertoires ignore[/dim]")

        # Create video list [GAP]
        console.print("[blue]Analyse et creation des liens temporaires...[/blue]")
        list_of_videos = create_video_list(
            cli_args.search_dir,
            cli_args.days_to_process,
            temp_dir,
            cli_args.storage_dir,
            cli_args.force_mode,
            cli_args.dry_run,
            use_multiprocessing=(nb_videos > 50)
        )

        if not list_of_videos:
            if cli_args.force_mode:
                console.print("[yellow]Aucune video a traiter (meme en mode force)[/yellow]")
            else:
                console.print("[yellow]Aucune nouvelle video a traiter[/yellow]")
            return 0

        console.print(f"[green]{len(list_of_videos)} videos pretes pour le traitement[/green]")

        # Save original links
        if not cli_args.dry_run:
            logger.info("Sauvegarde des liens vers les fichiers originaux")
            copy_tree(temp_dir, original_dir, cli_args.dry_run)
            cleanup_directories(work_dir)
            work_dir.mkdir(exist_ok=True)
        else:
            console.print("[dim]SIMULATION - Sauvegarde et nettoyage ignores[/dim]")

        # Main video processing loop [GAP functions]
        console.print("[blue]Formatage des titres et organisation...[/blue]")
        dict_titles = {}

        from tqdm import tqdm
        with tqdm(list_of_videos, desc="Traitement des videos", unit="fichier") as pbar:
            for video in pbar:
                pbar.set_postfix_str(f"{video.complete_path_original.name[:30]}...")

                try:
                    # Process documentaries (simple path)
                    if video.type_file in {'Docs', 'Docs#1'}:
                        rename_video(video, dict_titles, video.type_file, work_dir, cli_args.dry_run)
                        move_file_new_nas(video, cli_args.storage_dir, cli_args.dry_run)
                        continue

                    # Check cache for repeated titles
                    cache_key = video.title
                    if cache_key in dict_titles:
                        (video.title_fr, video.date_film, video.genre,
                         video.complete_dir_symlinks, video.sub_directory, cached_spec) = dict_titles[cache_key]

                        if not video.spec or len(video.spec.split()) < 3:
                            video.spec = cached_spec

                        video.formatted_filename = video.format_name(video.title_fr)
                        logger.info(f"{video.formatted_filename} ({video.genre}) - formate (depuis cache)")
                    else:
                        # Full API processing [GAP]
                        original_spec = video.spec
                        video = set_fr_title_and_category(video)

                        # Handle undetected films
                        if (not video.title_fr or video.title_fr.strip() == '') and video.is_film_anim():
                            video.title_fr = ""
                            video.date_film = 0
                            video.genre = "Non detecte"
                            video.list_genres = ["Non detecte"]
                            video.spec = original_spec
                            video.formatted_filename = format_undetected_filename(video)
                            video.sub_directory = Path('Films/non detectes')
                            video.complete_dir_symlinks = find_directory_for_video(
                                video, cli_args.symlinks_dir / 'Films'
                            )
                        else:
                            # Normal processing
                            video.complete_dir_symlinks, video.sub_directory = find_symlink_and_sub_dir(
                                video, cli_args.symlinks_dir
                            )

                            # Enhance specs if needed [GAP]
                            if not video.spec or len(video.spec.split()) < 3:
                                media_spec = media_info(video)
                                if media_spec:
                                    video.spec = media_spec

                            video.formatted_filename = video.format_name(video.title_fr)

                        # Cache results
                        if video.title_fr and video.title:
                            dict_titles[cache_key] = (
                                video.title_fr, video.date_film, video.genre,
                                video.complete_dir_symlinks, video.sub_directory, video.spec
                            )

                    # Process video for duplicates [GAP]
                    processed_video = process_video(
                        video, waiting_folder, cli_args.storage_dir, cli_args.symlinks_dir
                    )
                    if processed_video:
                        rename_video(
                            processed_video, dict_titles,
                            str(processed_video.sub_directory), work_dir, cli_args.dry_run
                        )
                        move_file_new_nas(processed_video, cli_args.storage_dir, cli_args.dry_run)

                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {video.complete_path_original.name}: {e}")
                    continue

        # Process series episode titles [GAP]
        series_videos = [v for v in list_of_videos if v.is_serie() and v.title_fr]
        if series_videos:
            if not cli_args.dry_run:
                console.print(f"[blue]Recherche des titres d'episodes pour {len(series_videos)} series...[/blue]")
                cleanup_work_directory(work_dir)
            else:
                console.print(f"[yellow]SIMULATION - Recherche des titres d'episodes...[/yellow]")

            add_episodes_titles(series_videos, work_dir / 'Series/Series TV', cli_args.dry_run)

        # Final copy to destination [MODULAR]
        if work_dir.exists() and any(work_dir.iterdir()):
            console.print("[blue]Copie finale vers le repertoire de destination...[/blue]")
            copy_tree(work_dir, cli_args.output_dir, cli_args.dry_run)

            if not cli_args.dry_run:
                console.print("[blue]Verification de l'integrite des liens symboliques...[/blue]")
                verify_symlinks(cli_args.output_dir)

        # Display statistics
        # Calculate statistics
        films_count = sum(1 for v in list_of_videos if v.is_film())
        series_count = sum(1 for v in list_of_videos if v.is_serie() and v.title_fr)
        anim_count = sum(1 for v in list_of_videos if v.is_animation())
        docs_count = sum(1 for v in list_of_videos if v.type_file in {'Docs', 'Docs#1'})
        non_detectes = sum(1 for v in list_of_videos if v.is_film_anim() and (not v.title_fr or v.genre == "Non detecte"))

        console.print("\n")
        console.print_panel(
            f"[bold]Statistiques de traitement[/bold]\n\n"
            f"Films: [cyan]{films_count}[/cyan]\n"
            f"Series: [cyan]{series_count}[/cyan]\n"
            f"Animation: [cyan]{anim_count}[/cyan]\n"
            f"Documentaires: [cyan]{docs_count}[/cyan]\n"
            f"Non detectes: [yellow]{non_detectes}[/yellow]\n\n"
            f"Total traite: [green]{len(list_of_videos)}[/green]",
            title="Resume",
            border_style="green" if not cli_args.dry_run else "yellow"
        )

        if cli_args.dry_run:
            console.print("\n[yellow]Mode simulation - aucune modification effectuee[/yellow]")

        logger.info(f"Traitement termine: {len(list_of_videos)} videos traitees")
        return 0

    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur")
        print("\n[yellow]Interruption par l'utilisateur[/yellow]")
        return 130

    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        print(f"[red]Erreur fatale: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
