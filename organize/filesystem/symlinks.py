"""Symlink operations for video organization."""

from pathlib import Path

from loguru import logger


def create_symlink(source: Path, destination: Path, dry_run: bool = False) -> None:
    """
    Create a symbolic link (or simulate if dry_run).

    Args:
        source: Source file path.
        destination: Destination symlink path.
        dry_run: If True, only simulate the operation.
    """
    if dry_run:
        logger.debug(f'SIMULATION - Symlink: {source} -> {destination}')
        return

    try:
        # Résoudre la source si c'est déjà un symlink
        if source.is_symlink():
            source = source.resolve()

        # Supprimer la destination existante
        if destination.exists() or destination.is_symlink():
            destination.unlink()

        destination.symlink_to(source)
        logger.debug(f'Symlink created: {source} -> {destination}')

    except OSError as e:
        logger.warning(f"Erreur lors de la création du symlink {source} -> {destination}: {e}")


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
