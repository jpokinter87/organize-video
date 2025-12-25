"""File operations for moving, copying, and renaming files."""

import shutil
from pathlib import Path
from typing import Tuple

from loguru import logger


def move_file(source: Path, destination: Path, dry_run: bool = False) -> bool:
    """
    Move a file to destination with duplicate handling.

    Args:
        source: Source file path.
        destination: Destination file path.
        dry_run: If True, only simulate the operation.

    Returns:
        True if successful, False otherwise.
    """
    if dry_run:
        logger.info(f'SIMULATION - Move: {source.name} -> {destination}')
        return True

    if not source.exists():
        logger.warning(f'Source file not found: {source}')
        return False

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            logger.warning(f'Destination file exists: {destination}')
            if source.stat().st_size == destination.stat().st_size:
                logger.info(f'Identical file detected, removing source: {source}')
                source.unlink()
                return True
            else:
                destination = ensure_unique_destination(destination)
                logger.info(f'Renaming file to: {destination}')

        shutil.move(str(source), str(destination))
        logger.info(f'File moved: {destination}')
        return True

    except Exception as e:
        logger.error(f'Error moving {source}: {e}')
        return False


def copy_tree(source_dir: Path, dest_dir: Path, dry_run: bool = False) -> bool:
    """
    Copy directory tree to destination.

    Args:
        source_dir: Source directory path.
        dest_dir: Destination directory path.
        dry_run: If True, only simulate the operation.

    Returns:
        True if successful, False otherwise.
    """
    if not source_dir.exists() or not any(source_dir.iterdir()):
        logger.warning('No files to copy.')
        return False

    if dry_run:
        logger.info(f'SIMULATION - Copy tree: {source_dir} -> {dest_dir}')
        return True

    try:
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        shutil.copytree(source_dir, dest_dir, symlinks=True)
        logger.info(f"Tree copied: {source_dir} -> {dest_dir}")
        return True

    except Exception as e:
        logger.error(f"Error copying tree: {e}")
        return False


def ensure_unique_destination(destination: Path) -> Path:
    """
    Ensure destination path is unique by adding counter suffix.

    Args:
        destination: Desired destination path.

    Returns:
        Unique path (original if doesn't exist, or with counter suffix).
    """
    if not destination.exists():
        return destination

    counter = 1
    base_name = destination.stem
    extension = destination.suffix

    while destination.exists():
        destination = destination.parent / f"{base_name}_{counter}{extension}"
        counter += 1

    return destination


def setup_working_directories(
    destination_dir: Path,
    dry_run: bool = False
) -> Tuple[Path, Path, Path, Path]:
    """
    Configure working directories for video processing.

    Args:
        destination_dir: Base destination directory.
        dry_run: If True, only return paths without creating.

    Returns:
        Tuple of (work_dir, temp_dir, original_dir, waiting_folder).
    """
    parent = destination_dir.parent
    work_dir = parent / "work"
    temp_dir = parent / "tmp"
    original_dir = parent / "original"
    waiting_folder = parent / "_a_virer"

    if dry_run:
        logger.debug("SIMULATION - Setup working directories")
        return work_dir, temp_dir, original_dir, waiting_folder

    # Create directories if needed
    for dir_path in [work_dir, temp_dir, original_dir, waiting_folder]:
        dir_path.mkdir(parents=True, exist_ok=True)

    return work_dir, temp_dir, original_dir, waiting_folder
