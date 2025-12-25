"""Series episode handling functions."""

import re
from pathlib import Path
from typing import Optional

from loguru import logger


def format_season_folder(season: int) -> str:
    """
    Format season number as folder name.

    Args:
        season: Season number.

    Returns:
        Formatted string like "Saison 01" or empty string for season 0.
    """
    if season == 0:
        return ""
    return f"Saison {season:02d}"


def find_series_folder(file_path: Path) -> Path:
    """
    Find the series root folder (the one ending with year).

    Walks up the path looking for a folder matching pattern "(YYYY)".

    Args:
        file_path: Path to the episode file.

    Returns:
        Path to the series folder, or immediate parent if not found.
    """
    current = file_path.parent

    while current.parent and current.parent != current:
        # Check if folder name ends with (YYYY)
        if re.search(r'\(\d{4}\)$', current.name):
            return current
        current = current.parent

    return file_path.parent


def build_episode_filename(
    series_title: str,
    year: int,
    sequence: str,
    episode_title: str,
    spec: str,
    extension: str
) -> str:
    """
    Build the complete episode filename.

    Args:
        series_title: Title of the series.
        year: Release year.
        sequence: Season/episode sequence like "- S01E05 -".
        episode_title: Title of the episode.
        spec: Technical specifications (language, codec, resolution).
        extension: File extension including dot.

    Returns:
        Formatted filename string.
    """
    parts = [f"{series_title} ({year})"]

    if sequence:
        parts.append(sequence)

    if episode_title:
        parts.append(episode_title)

    if spec:
        parts.append(f"- {spec}")

    filename = " ".join(parts)

    # Clean up multiple spaces
    filename = " ".join(filename.split())

    return f"{filename}{extension}"


def should_create_season_folder(current_path: Path, season: int) -> bool:
    """
    Check if a season folder needs to be created.

    Args:
        current_path: Current file path.
        season: Season number.

    Returns:
        True if season folder should be created.
    """
    if season == 0:
        return False

    season_folder = format_season_folder(season)
    parent_str = str(current_path.parent)

    # Check if we're already in the correct season folder
    return season_folder not in parent_str


def organize_episode_by_season(
    current_path: Path,
    formatted_filename: str,
    season: int,
    dry_run: bool = False
) -> Path:
    """
    Organize an episode file into the correct season folder.

    Args:
        current_path: Current path of the episode file.
        formatted_filename: New filename for the episode.
        season: Season number.
        dry_run: If True, simulate without making changes.

    Returns:
        New path for the episode file.
    """
    if season == 0:
        return current_path

    season_folder = format_season_folder(season)

    if not should_create_season_folder(current_path, season):
        # Already in correct season folder, just rename if needed
        new_path = current_path.parent / formatted_filename
        if new_path != current_path:
            if not dry_run and current_path.exists():
                current_path.rename(new_path)
                logger.debug(f"Episode renamed: {new_path}")
        return new_path

    # Need to create/move to season folder
    series_folder = find_series_folder(current_path)
    season_path = series_folder / season_folder
    new_path = season_path / formatted_filename

    if dry_run:
        logger.debug(f"SIMULATION - Create season folder: {season_path}")
        logger.debug(f"SIMULATION - Move episode to: {new_path}")
    else:
        season_path.mkdir(exist_ok=True)
        if current_path.exists():
            current_path.rename(new_path)
            logger.debug(f"Episode moved to season: {new_path}")

    return new_path
