"""Symlink operations for video organization."""

from pathlib import Path
from typing import Optional, Set

from loguru import logger

# Répertoires système critiques où les symlinks ne doivent jamais pointer
_FORBIDDEN_PATHS: Set[str] = {
    '/', '/bin', '/sbin', '/usr', '/etc', '/var', '/root',
    '/boot', '/lib', '/lib64', '/proc', '/sys', '/dev'
}


def _is_path_safe(path: Path, context: str = "path") -> bool:
    """
    Vérifie qu'un chemin est sûr pour les opérations de symlink.

    Détecte les tentatives d'échappement de répertoire et les chemins
    vers des zones système critiques.

    Args:
        path: Chemin à vérifier.
        context: Description du contexte pour les logs (source/destination).

    Returns:
        True si le chemin est sûr, False sinon.
    """
    try:
        # Résoudre le chemin pour détecter les traversées (..)
        resolved = path.resolve()
        resolved_str = str(resolved)

        # Vérifier que le chemin ne pointe pas vers un répertoire système critique
        for forbidden in _FORBIDDEN_PATHS:
            if resolved_str == forbidden or resolved_str.startswith(forbidden + '/'):
                # Exception: permettre /var/log, /var/tmp, etc. pour les fichiers normaux
                if forbidden == '/var' and any(
                    resolved_str.startswith(f'/var/{allowed}')
                    for allowed in ['log', 'tmp', 'cache']
                ):
                    continue
                logger.warning(
                    f"Chemin {context} interdit (zone système): {resolved}"
                )
                return False

        # Vérifier la présence de patterns suspects dans le chemin original
        path_str = str(path)
        if '..' in path_str:
            logger.warning(
                f"Chemin {context} suspect (traversée de répertoire): {path}"
            )
            return False

        return True

    except (OSError, ValueError) as e:
        logger.warning(f"Impossible de valider le chemin {context}: {path} ({e})")
        return False


def create_symlink(
    source: Path,
    destination: Path,
    dry_run: bool = False,
    skip_validation: bool = False
) -> Optional[bool]:
    """
    Create a symbolic link (or simulate if dry_run).

    Includes security validation to prevent symlink escape attacks
    (creating symlinks to/from system directories).

    Args:
        source: Source file path.
        destination: Destination symlink path.
        dry_run: If True, only simulate the operation.
        skip_validation: If True, skip security validation (for tests only).

    Returns:
        True if successful, False if validation failed, None on error.
    """
    # Validation de sécurité des chemins
    if not skip_validation:
        if not _is_path_safe(source, "source"):
            logger.error(f"Création de symlink refusée: source non sécurisée {source}")
            return False
        if not _is_path_safe(destination, "destination"):
            logger.error(f"Création de symlink refusée: destination non sécurisée {destination}")
            return False

    if dry_run:
        logger.debug(f'SIMULATION - Symlink: {source} -> {destination}')
        return True

    try:
        # Résoudre la source si c'est déjà un symlink
        if source.is_symlink():
            source = source.resolve()

        # Supprimer la destination existante
        if destination.exists() or destination.is_symlink():
            destination.unlink()

        destination.symlink_to(source)
        logger.debug(f'Symlink created: {source} -> {destination}')
        return True

    except OSError as e:
        logger.warning(f"Erreur lors de la création du symlink {source} -> {destination}: {e}")
        return None


def verify_symlinks(directory: Path) -> None:
    """
    Verify symlink integrity and remove broken links.

    Args:
        directory: Directory to scan for symlinks.
    """
    broken_links = []

    for item in directory.rglob('*'):
        if item.is_symlink():
            try:
                # Essayer de résoudre le lien
                item.resolve(strict=True)
            except (FileNotFoundError, OSError):
                broken_links.append(item)

    if broken_links:
        logger.warning(f"Broken symlinks detected: {len(broken_links)}")
        for link in broken_links:
            logger.warning(f"Broken link: {link}")
            try:
                link.unlink()
                logger.info(f"Broken link removed: {link}")
            except OSError as e:
                logger.error(f"Impossible de supprimer le lien cassé {link}: {e}")
    else:
        logger.info("All symlinks are valid")


def is_valid_symlink(path: Path) -> bool:
    """
    Check if path is a valid, non-broken symlink.

    Args:
        path: Path to check.

    Returns:
        True if path is a valid symlink, False otherwise.
    """
    if not path.is_symlink():
        return False

    try:
        path.resolve(strict=True)
        return True
    except (FileNotFoundError, OSError):
        return False
