"""Entry point for the organize video package.

This module provides the command-line entry point for the video organization tool.
Run with: python -m organize

Supports:
- Modern modular mode (default): Uses fully modular components
- Legacy mode (--legacy flag): Delegates entirely to organize.py
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from loguru import logger

# Charger les variables d'environnement depuis .env à la racine du projet
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

from organize.config import CLIArgs, ConfigurationManager
from organize.config.manager import ValidationResult
from organize.ui import ConsoleUI
from organize.ui.display import generate_tree_structure, display_tree
from organize.pipeline import (
    PipelineContext,
    PipelineOrchestrator,
    ProcessingStats,
    create_video_list,
)
from organize.filesystem import copy_tree, cleanup_directories
from organize.config.settings import MULTIPROCESSING_VIDEO_THRESHOLD
from organize.models.video import Video


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


def display_dry_run_tree(videos: List[Video], console: ConsoleUI) -> None:
    """
    Affiche l'arborescence des fichiers qui auraient été créés en mode simulation.

    Args:
        videos: Liste des objets Video traités.
        console: Instance ConsoleUI pour l'affichage.
    """
    # Filtrer les vidéos avec un nom formaté
    videos_with_paths = [v for v in videos if v.formatted_filename]

    if not videos_with_paths:
        console.print("[dim]Aucun fichier à afficher dans l'arborescence[/dim]")
        return

    console.print("\n")
    console.print_panel(
        "[bold]Arborescence des fichiers qui auraient été créés[/bold]\n"
        "[dim]Cette structure montre l'organisation finale des symlinks[/dim]",
        title="Structure de destination (simulation)",
        border_style="blue"
    )

    # Générer et afficher l'arborescence
    tree_structure = generate_tree_structure(videos_with_paths)
    display_tree(tree_structure, max_files_per_folder=10)


# ============================================================================
# LEGACY MODE SUPPORT
# ============================================================================

def _extract_legacy_flag(args: List[str]) -> Tuple[bool, List[str]]:
    """
    Extrait le flag --legacy des arguments sans modifier sys.argv.

    Args:
        args: Liste des arguments de ligne de commande.

    Returns:
        Tuple (is_legacy_mode, arguments_sans_legacy).
    """
    is_legacy = "--legacy" in args
    filtered_args = [arg for arg in args if arg != "--legacy"]
    return is_legacy, filtered_args


def run_legacy_mode(args: List[str]) -> int:
    """
    Run in legacy mode by delegating to organize.py main().

    Args:
        args: Command line arguments (without --legacy flag).

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

        # Sauvegarder sys.argv et le restaurer après
        original_argv = sys.argv
        try:
            sys.argv = args
            spec = importlib.util.spec_from_file_location("organize_original", organize_py)
            organize_module = importlib.util.module_from_spec(spec)
            sys.modules["organize_original"] = organize_module
            spec.loader.exec_module(organize_module)
            organize_module.main()
            return 0
        finally:
            sys.argv = original_argv

    except KeyboardInterrupt:
        console.print("\n[yellow]Interruption par l'utilisateur[/yellow]")
        return 130
    except (OSError, ImportError, AttributeError) as e:
        logger.error(f"Legacy mode error: {e}")
        console.print(f"[red]Erreur mode legacy: {e}[/red]")
        return 1


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def _validate_configuration(
    config_manager: ConfigurationManager,
    console: ConsoleUI
) -> Tuple[bool, Optional[list]]:
    """
    Valide toute la configuration avant le traitement.

    Args:
        config_manager: Gestionnaire de configuration.
        console: Interface console.

    Returns:
        Tuple (validation_ok, categories_disponibles).
        Si validation_ok est False, categories_disponibles est None.
    """
    # Valider le répertoire d'entrée
    validation = config_manager.validate_input_directory()
    if not validation.valid:
        console.print(f"[red]Erreur: {validation.error_message}[/red]")
        return False, None

    # Valider les clés API
    validation = config_manager.validate_api_keys()
    if not validation.valid:
        console.print(f"[red]Erreur: {validation.error_message}[/red]")
        return False, None

    # Valider la connectivité API
    validation = config_manager.validate_api_connectivity()
    if not validation.valid:
        console.print(f"[red]Erreur: {validation.error_message}[/red]")
        return False, None

    # Valider les catégories
    cat_validation, available_categories = config_manager.validate_categories()
    if not cat_validation.valid:
        console.print(f"[red]{cat_validation.error_message}[/red]")
        return False, None

    console.print(
        f"[green]Categories detectees: "
        f"{', '.join([cat.name for cat in available_categories])}[/green]"
    )
    return True, available_categories


def _prepare_videos(
    config_manager: ConfigurationManager,
    cli_args: CLIArgs,
    console: ConsoleUI
) -> Tuple[Optional[List[Video]], Path, Path, Path, Path]:
    """
    Prépare la liste des vidéos et les répertoires de travail.

    Args:
        config_manager: Gestionnaire de configuration.
        cli_args: Arguments CLI.
        console: Interface console.

    Returns:
        Tuple (liste_videos, work_dir, temp_dir, original_dir, waiting_folder).
        liste_videos est None si aucune vidéo à traiter.
    """
    # Compter les vidéos
    nb_videos = config_manager.get_video_count()
    if nb_videos == 0:
        console.print("[yellow]Aucune video a traiter[/yellow]")
        return None, Path(), Path(), Path(), Path()

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
        return None, work_dir, temp_dir, original_dir, waiting_folder

    console.print(f"[green]{len(list_of_videos)} videos pretes pour le traitement[/green]")
    return list_of_videos, work_dir, temp_dir, original_dir, waiting_folder


def _execute_pipeline(
    list_of_videos: List[Video],
    cli_args: CLIArgs,
    work_dir: Path,
    temp_dir: Path,
    original_dir: Path,
    waiting_folder: Path,
    console: ConsoleUI
) -> ProcessingStats:
    """
    Exécute le pipeline de traitement des vidéos.

    Args:
        list_of_videos: Liste des vidéos à traiter.
        cli_args: Arguments CLI.
        work_dir: Répertoire de travail.
        temp_dir: Répertoire temporaire.
        original_dir: Répertoire des originaux.
        waiting_folder: Dossier d'attente.
        console: Interface console.

    Returns:
        Statistiques de traitement.
    """
    # Sauvegarder les liens originaux
    if not cli_args.dry_run:
        logger.info("Sauvegarde des liens vers les fichiers originaux")
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
            console.print(
                f"[blue]Recherche des titres d'episodes pour {series_count} series...[/blue]"
            )
    else:
        console.print("[yellow]SIMULATION - Recherche des titres d'episodes...[/yellow]")

    orchestrator.process_series_titles(list_of_videos)

    # Finaliser
    console.print("[blue]Copie finale vers le repertoire de destination...[/blue]")
    orchestrator.finalize()

    return stats


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the video organization tool.

    Supports two modes:
    - Modern mode (default): Uses modular components
    - Legacy mode (--legacy): Delegates entirely to organize.py

    Args:
        args: Command line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    if args is None:
        args = sys.argv

    # Vérifier le mode legacy en premier (avant de parser les autres arguments)
    is_legacy, filtered_args = _extract_legacy_flag(args)
    if is_legacy:
        return run_legacy_mode(filtered_args)

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
        validation_ok, _ = _validate_configuration(config_manager, console)
        if not validation_ok:
            return 1

        # Préparer les vidéos
        list_of_videos, work_dir, temp_dir, original_dir, waiting_folder = _prepare_videos(
            config_manager, cli_args, console
        )

        if list_of_videos is None:
            return 0

        # Exécuter le pipeline
        stats = _execute_pipeline(
            list_of_videos, cli_args,
            work_dir, temp_dir, original_dir, waiting_folder,
            console
        )

        # Afficher les statistiques
        display_statistics(stats, cli_args.dry_run, console)

        # En mode dry-run, afficher l'arborescence des fichiers
        if cli_args.dry_run:
            display_dry_run_tree(list_of_videos, console)

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

    except ValueError as e:
        # Erreurs de configuration ou de validation
        logger.error(f"Erreur de configuration: {e}")
        console.print(f"[red]Erreur de configuration: {e}[/red]")
        return 1

    except (AttributeError, TypeError) as e:
        # Erreurs inattendues dans le code
        logger.error(f"Erreur inattendue: {e}")
        logger.opt(exception=True).debug("Traceback complet")
        console.print(f"[red]Erreur inattendue: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
