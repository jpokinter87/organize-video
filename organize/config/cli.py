"""Command-line interface argument parsing."""

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger

from organize.config.settings import (
    DEFAULT_SEARCH_DIR,
    DEFAULT_STORAGE_DIR,
    DEFAULT_SYMLINKS_DIR,
    DEFAULT_TEMP_SYMLINKS_DIR,
    PROCESS_ALL_FILES_DAYS,
)


@dataclass
class CLIArgs:
    """
    Parsed command-line arguments.

    Attributes:
        days_to_process: Number of days of files to process (0 for default).
        dry_run: If True, simulate without making changes.
        force_mode: If True, skip duplicate checks.
        debug: If True, enable debug mode.
        tag: Debug tag to search for.
        search_dir: Directory to search for videos.
        output_dir: Temporary output directory.
        symlinks_dir: Final symlinks directory.
        storage_dir: Final storage directory.
    """

    days_to_process: float = 0
    dry_run: bool = False
    force_mode: bool = False
    debug: bool = False
    tag: str = ""
    legacy: bool = False
    search_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    symlinks_dir: Optional[Path] = None
    storage_dir: Optional[Path] = None

    @property
    def process_all(self) -> bool:
        """Check if processing all files (no date filter)."""
        return self.days_to_process >= PROCESS_ALL_FILES_DAYS


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog='organize_video',
        description="""
        Scans directory and organizes video files by creating symbolic links
        in a structure organized by genre and alphabetical order.
        """
    )

    # Groupe mutuellement exclusif jour/tous
    day_group = parser.add_mutually_exclusive_group()

    day_group.add_argument(
        '-a', '--all',
        action='store_true',
        help='process all files regardless of date'
    )

    day_group.add_argument(
        '-d', '--day',
        type=float,
        default=0,
        help='only process files less than DAY days old'
    )

    # Arguments de répertoire
    parser.add_argument(
        '-i', '--input',
        default=str(DEFAULT_SEARCH_DIR),
        help=f"source directory (default: {DEFAULT_SEARCH_DIR})"
    )

    parser.add_argument(
        '-o', '--output',
        default=str(DEFAULT_TEMP_SYMLINKS_DIR),
        help=f"temporary symlink destination (default: {DEFAULT_TEMP_SYMLINKS_DIR})"
    )

    parser.add_argument(
        '-s', '--symlinks',
        default=str(DEFAULT_SYMLINKS_DIR),
        help=f"final symlink destination (default: {DEFAULT_SYMLINKS_DIR})"
    )

    parser.add_argument(
        '--storage',
        default=str(DEFAULT_STORAGE_DIR),
        help=f"final file storage directory (default: {DEFAULT_STORAGE_DIR})"
    )

    # Drapeaux de mode
    parser.add_argument(
        '--force',
        action='store_true',
        help="skip hash verification (development mode)"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="simulation mode - no file modifications (recommended for testing)"
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help="enable debug mode"
    )

    parser.add_argument(
        '--tag',
        nargs='?',
        default='',
        help="tag to search for in debug mode"
    )

    parser.add_argument(
        '--legacy',
        action='store_true',
        help="utiliser le mode legacy (delegation complete vers organize.py)"
    )

    return parser


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings (None for sys.argv).

    Returns:
        Parsed Namespace object.
    """
    parser = create_parser()
    return parser.parse_args(args)


def validate_directories(
    input_dir: Path,
    output_dir: Path,
    symlinks_dir: Optional[Path] = None,
    storage_dir: Optional[Path] = None,
    dry_run: bool = False
) -> bool:
    """
    Validate and optionally create directories.

    Checks that:
    - Input directory exists and is readable
    - Output directories are writable (or can be created)

    Args:
        input_dir: Input directory (must exist).
        output_dir: Output directory.
        symlinks_dir: Symlinks directory.
        storage_dir: Storage directory.
        dry_run: If True, skip directory creation.

    Returns:
        True if validation passed, False otherwise.
    """
    # Le répertoire d'entrée doit exister
    if not input_dir.exists():
        logger.error(f"Répertoire d'entrée inexistant: {input_dir}")
        return False

    # Le répertoire d'entrée doit être lisible
    if not os.access(input_dir, os.R_OK):
        logger.error(f"Répertoire d'entrée non accessible en lecture: {input_dir}")
        return False

    # Préparer la liste des répertoires de sortie à valider
    dirs_to_validate = [output_dir]
    if symlinks_dir:
        dirs_to_validate.append(symlinks_dir)
    if storage_dir:
        dirs_to_validate.append(storage_dir)

    # Vérifier l'accès en écriture pour les répertoires existants, ou les parents pour les nouveaux
    for dir_path in dirs_to_validate:
        if dir_path.exists():
            if not os.access(dir_path, os.W_OK):
                logger.error(f"Répertoire non accessible en écriture: {dir_path}")
                return False
        else:
            # Vérifier si on peut créer le répertoire (le parent doit être accessible en écriture)
            parent = dir_path.parent
            while not parent.exists() and parent != parent.parent:
                parent = parent.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                logger.error(f"Impossible de créer le répertoire (parent non accessible en écriture): {dir_path}")
                return False

    # Créer les répertoires de sortie si pas en dry_run
    if not dry_run:
        for dir_path in dirs_to_validate:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(f"Impossible de créer le répertoire {dir_path}: {e}")
                return False

    return True


def _resolve_path(path_str: str, param_name: str) -> Path:
    """
    Résout un chemin en chemin absolu avec validation.

    Args:
        path_str: Chaîne représentant le chemin.
        param_name: Nom du paramètre (pour les messages d'erreur).

    Returns:
        Chemin absolu résolu.

    Raises:
        ValueError: Si le chemin est invalide ou dangereux.
    """
    # Chemins système dangereux à éviter
    DANGEROUS_PATHS = {'/', '/usr', '/bin', '/sbin', '/etc', '/var', '/tmp', '/root'}

    try:
        path = Path(path_str).expanduser().resolve()

        # Vérifier que le chemin n'est pas un répertoire système critique
        path_str_resolved = str(path)
        if path_str_resolved in DANGEROUS_PATHS:
            raise ValueError(f"Chemin système critique interdit pour {param_name}: {path}")

        # Vérifier que le chemin a au moins 2 niveaux de profondeur
        if len(path.parts) < 3 and path_str_resolved != str(Path.home()):
            logger.warning(f"Chemin très court pour {param_name}: {path} - vérifiez que c'est intentionnel")

        return path
    except (OSError, ValueError) as e:
        raise ValueError(f"Chemin invalide pour {param_name}: {path_str} ({e})")


def args_to_cli_args(namespace: argparse.Namespace) -> CLIArgs:
    """
    Convert argparse Namespace to CLIArgs dataclass.

    Les chemins sont résolus en chemins absolus pour éviter
    les problèmes de chemins relatifs.

    Args:
        namespace: Parsed argparse Namespace.

    Returns:
        CLIArgs instance.

    Raises:
        ValueError: Si un chemin est invalide.
    """
    # Déterminer le nombre de jours à traiter
    if namespace.all:
        days = PROCESS_ALL_FILES_DAYS
    elif namespace.day != 0:
        days = namespace.day
    else:
        days = 0

    # Résoudre tous les chemins en chemins absolus
    search_dir = _resolve_path(namespace.input, "input")
    output_dir = _resolve_path(namespace.output, "output")
    symlinks_dir = _resolve_path(namespace.symlinks, "symlinks")
    storage_dir = _resolve_path(namespace.storage, "storage")

    return CLIArgs(
        days_to_process=days,
        dry_run=namespace.dry_run,
        force_mode=namespace.force,
        debug=namespace.debug,
        tag=namespace.tag or "",
        legacy=getattr(namespace, 'legacy', False),
        search_dir=search_dir,
        output_dir=output_dir,
        symlinks_dir=symlinks_dir,
        storage_dir=storage_dir,
    )
