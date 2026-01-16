"""File discovery functions for finding video files."""

from pathlib import Path
from typing import Generator, List

from loguru import logger

from organize.config.settings import CATEGORIES, ALL_EXTENSIONS


def get_available_categories(directory: Path) -> List[Path]:
    """
    Return list of available category directories.

    Args:
        directory: Root directory to search in.

    Returns:
        List of Path objects for existing category directories.
    """
    available_categories = []
    for category in CATEGORIES:
        category_path = directory / category
        if category_path.exists() and category_path.is_dir():
            available_categories.append(category_path)
    return available_categories


def get_files(directory: Path) -> Generator[Path, None, None]:
    """
    Generate all video files from authorized categories in directory.

    Args:
        directory: Root directory to search in.

    Yields:
        Path objects for each video file found.
    """
    available_categories = get_available_categories(directory)

    if not available_categories:
        logger.warning(f"No categories found in {directory}")
        return

    logger.info(f"Categories found: {[cat.name for cat in available_categories]}")

    try:
        for category_path in available_categories:
            logger.debug(f"Scanning: {category_path}")
            file_count = 0
            for file in category_path.rglob("*"):
                if file.is_file() and file.suffix.lower() in ALL_EXTENSIONS:
                    file_count += 1
                    yield file
            logger.debug(f"  → {file_count} files found in {category_path.name}")
    except OSError as e:
        logger.warning(f"Erreur d'accès au système de fichiers pour {directory}: {e}")


def count_videos(search_dir: Path) -> int:
    """
    Count number of video files to process in authorized categories.

    Args:
        search_dir: Root directory to count files in.

    Returns:
        Total count of video files.
    """
    available_categories = get_available_categories(search_dir)

    if not available_categories:
        return 0

    video_count = 0
    try:
        for category_path in available_categories:
            category_count = 0
            for file in category_path.rglob("*"):
                if file.is_file() and file.suffix.lower() in ALL_EXTENSIONS:
                    category_count += 1
            video_count += category_count
            logger.debug(f"{category_count} files in {category_path.name}")
    except OSError as e:
        logger.warning(f"Erreur lors du comptage des fichiers: {e}")

    return video_count
