"""Entry point for the organize video package.

This module provides the command-line entry point for the video organization tool.
Run with: python -m organize

Supports:
- Modern modular mode (default): Uses fully modular components
- Legacy mode (--legacy flag): Delegates entirely to organize.py
"""

import sys
from pathlib import Path

from loguru import logger

from organize.config import CLIArgs, ConfigurationManager
from organize.ui import ConsoleUI
from organize.pipeline import (
    PipelineContext,
    PipelineOrchestrator,
    ProcessingStats,
    create_video_list,
)
from organize.filesystem import copy_tree
from organize.config.settings import MULTIPROCESSING_VIDEO_THRESHOLD


# ============================================================================
# UI HELPER FUNCTIONS
# ============================================================================

def display_configuration(cli_args: CLIArgs, console: ConsoleUI) -> None:
    """
    Display configuration panel in console.

    Args:
        cli_args: Parsed CLI arguments.
        console: Console UI instance.
    """
    # Construction du statut du mode
    mode_parts = []
    if cli_args.force_mode:
        mode_parts.append("[red]FORCE[/red]")
    if cli_args.dry_run:
        mode_parts.append("[yellow]SIMULATION[/yellow]")
    mode_status = " ".join(mode_parts) if mode_parts else "[green]Normal[/green]"

    # Construction de l'affichage de la période
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


def display_statistics(stats: ProcessingStats, dry_run: bool, console: ConsoleUI) -> None:
    """Display processing statistics."""
    console.print("\n")
    console.print_panel(
        f"[bold]Statistiques de traitement[/bold]\n\n"
        f"Films: [cyan]{stats.films}[/cyan]\n"
        f"Series: [cyan]{stats.series}[/cyan]\n"
        f"Animation: [cyan]{stats.animation}[/cyan]\n"
        f"Documentaires: [cyan]{stats.docs}[/cyan]\n"
        f"Non detectes: [yellow]{stats.undetected}[/yellow]\n\n"
        f"Total traite: [green]{stats.total}[/green]",
        title="Resume",
        border_style="green" if not dry_run else "yellow"
    )

    if dry_run:
        console.print("\n[yellow]Mode simulation - aucune modification effectuee[/yellow]")


# ============================================================================
# LEGACY MODE SUPPORT
# ============================================================================

def run_legacy_mode() -> int:
    """
    Run in legacy mode by delegating to organize.py main().

    Returns:
        Exit code from legacy main().
    """
    import importlib.util

    logger.info("Running in legacy mode (organize.py)")
    console = ConsoleUI()
    console.print("[yellow]Mode legacy active - utilisation de organize.py[/yellow]")

    try:
        organize_py = Path(__file__).parent.parent / "organize.py"
        if not organize_py.exists():
            console.print("[red]organize.py non trouvé - mode legacy indisponible[/red]")
            return 1

        # Ajouter le répertoire parent au chemin pour les imports
        parent_dir = str(organize_py.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        spec = importlib.util.spec_from_file_location("organize_original", organize_py)
        organize_module = importlib.util.module_from_spec(spec)
        sys.modules["organize_original"] = organize_module
        spec.loader.exec_module(organize_module)
        organize_module.main()
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interruption par l'utilisateur[/yellow]")
        return 130
    except (OSError, ImportError, AttributeError) as e:
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
    - Modern mode (default): Uses modular components
    - Legacy mode (--legacy): Delegates entirely to organize.py

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Vérifier le mode legacy en premier (avant de parser les autres arguments)
    if check_legacy_flag():
        # Retirer --legacy de argv avant de déléguer
        sys.argv = [arg for arg in sys.argv if arg != "--legacy"]
        return run_legacy_mode()

    console = ConsoleUI()
    config_manager = ConfigurationManager()

    try:
        # Parser et valider la configuration
        cli_args = config_manager.parse_args()
        config_manager.setup_logging(debug=cli_args.debug)

        # Afficher les bannières
        if cli_args.dry_run:
            display_simulation_banner(console)
        display_configuration(cli_args, console)

        # Valider la configuration
        validation = config_manager.validate_input_directory()
        if not validation.valid:
            console.print(f"[red]Erreur: {validation.error_message}[/red]")
            return 1

        validation = config_manager.validate_api_keys()
        if not validation.valid:
            console.print(f"[red]Erreur: {validation.error_message}[/red]")
            return 1

        validation = config_manager.validate_api_connectivity()
        if not validation.valid:
            console.print(f"[red]Erreur: {validation.error_message}[/red]")
            return 1

        cat_validation, available_categories = config_manager.validate_categories()
        if not cat_validation.valid:
            console.print(f"[red]{cat_validation.error_message}[/red]")
            return 1

        console.print(f"[green]Categories detectees: {', '.join([cat.name for cat in available_categories])}[/green]")

        # Compter les vidéos
        nb_videos = config_manager.get_video_count()
        if nb_videos == 0:
            console.print("[yellow]Aucune video a traiter[/yellow]")
            return 0

        console.print(f"\n[bold green]{nb_videos} videos detectees[/bold green]")

        # Aplatir les répertoires de séries
        if not cli_args.dry_run:
            console.print("[blue]Aplatissement des repertoires series...[/blue]")
            config_manager.flatten_series_directories()
        else:
            console.print("[dim]SIMULATION - Aplatissement des repertoires ignore[/dim]")

        # Configurer les répertoires de travail
        work_dir, temp_dir, original_dir, waiting_folder = config_manager.setup_working_directories()

        # Créer la liste des vidéos
        console.print("[blue]Analyse et creation des liens temporaires...[/blue]")
        list_of_videos = create_video_list(
            cli_args.search_dir,
            cli_args.days_to_process,
            temp_dir,
            cli_args.storage_dir,
            cli_args.force_mode,
            cli_args.dry_run,
            use_multiprocessing=(nb_videos > MULTIPROCESSING_VIDEO_THRESHOLD)
        )

        if not list_of_videos:
            if cli_args.force_mode:
                console.print("[yellow]Aucune video a traiter (meme en mode force)[/yellow]")
            else:
                console.print("[yellow]Aucune nouvelle video a traiter[/yellow]")
            return 0

        console.print(f"[green]{len(list_of_videos)} videos pretes pour le traitement[/green]")

        # Sauvegarder les liens originaux
        if not cli_args.dry_run:
            logger.info("Sauvegarde des liens vers les fichiers originaux")
            from organize.filesystem import cleanup_directories
            copy_tree(temp_dir, original_dir, cli_args.dry_run)
            cleanup_directories(work_dir)
            work_dir.mkdir(exist_ok=True)
        else:
            console.print("[dim]SIMULATION - Sauvegarde et nettoyage ignores[/dim]")

        # Créer le contexte du pipeline et l'orchestrateur
        context = PipelineContext(
            search_dir=cli_args.search_dir,
            storage_dir=cli_args.storage_dir,
            symlinks_dir=cli_args.symlinks_dir,
            output_dir=cli_args.output_dir,
            work_dir=work_dir,
            temp_dir=temp_dir,
            original_dir=original_dir,
            waiting_folder=waiting_folder,
            dry_run=cli_args.dry_run,
            force_mode=cli_args.force_mode,
            days_to_process=cli_args.days_to_process,
        )
        orchestrator = PipelineOrchestrator(context)

        # Traiter les vidéos
        console.print("[blue]Formatage des titres et organisation...[/blue]")
        stats = orchestrator.process_videos(list_of_videos)

        # Traiter les titres des épisodes de séries
        if not cli_args.dry_run:
            series_count = sum(1 for v in list_of_videos if v.is_serie() and v.title_fr)
            if series_count > 0:
                console.print(f"[blue]Recherche des titres d'episodes pour {series_count} series...[/blue]")
        else:
            console.print("[yellow]SIMULATION - Recherche des titres d'episodes...[/yellow]")

        orchestrator.process_series_titles(list_of_videos)

        # Finaliser
        console.print("[blue]Copie finale vers le repertoire de destination...[/blue]")
        orchestrator.finalize()

        # Afficher les statistiques
        display_statistics(stats, cli_args.dry_run, console)

        logger.info(f"Traitement termine: {stats.total} videos traitees")
        return 0

    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur")
        console.print("\n[yellow]Interruption par l'utilisateur[/yellow]")
        return 130

    except OSError as e:
        # OSError inclut FileNotFoundError, PermissionError, etc.
        logger.error(f"Erreur systeme: {e}")
        console.print(f"[red]Erreur systeme: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
