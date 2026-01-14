"""Path resolution functions for video organization."""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from organize.models.video import Video


class SubfolderCache:
    """Simple cache for subfolder lookups to avoid repeated filesystem traversals."""

    def __init__(self):
        self._cache: Dict[Tuple[str, str], Path] = {}

    def get(self, key: Tuple[str, str]) -> Optional[Path]:
        """Get cached path for a key."""
        return self._cache.get(key)

    def set(self, key: Tuple[str, str], value: Path) -> None:
        """Cache a path for a key."""
        self._cache[key] = value

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()


# Module-level caches
subfolder_cache = SubfolderCache()
series_subfolder_cache = SubfolderCache()


def in_range(value: str, start: str, end: str) -> bool:
    """
    Check if a value is in an alphabetical range.

    Args:
        value: Value to check.
        start: Start of range (inclusive).
        end: End of range (inclusive).

    Returns:
        True if value is within range.
    """
    return start <= value <= end


def inflate(start: str, end: str, length: int) -> Tuple[str, str]:
    """
    Extend strings to a given length for comparison.

    Pads start with 'a' and end with 'z' to fill to length.

    Args:
        start: Start string.
        end: End string.
        length: Target length.

    Returns:
        Tuple of (padded_start, padded_end).
    """
    return start.ljust(length, 'a'), end.ljust(length, 'z')


def find_matching_folder(root_folder: Path, title: str) -> Path:
    """
    Find the deepest matching folder for a title.

    Looks for folders with range patterns like "a-m" or "n-z"
    and finds the one that contains the title alphabetically.

    Args:
        root_folder: Root folder to search in.
        title: Title to match.

    Returns:
        Path to the deepest matching folder, or root_folder if no match.
    """
    title_lower = title.lower()
    inflated_ranges: Dict[str, Tuple[str, str]] = {}

    def find_deepest(current_folder: Path, remaining_title: str) -> Path:
        best_match = current_folder

        try:
            for item in current_folder.iterdir():
                if not item.is_dir():
                    continue

                item_name_lower = item.name.lower()

                # Check for range pattern like "a-m"
                if '-' in item_name_lower and ' - ' not in item_name_lower:
                    parts = item_name_lower.split('-', 1)
                    if len(parts) == 2:
                        start, end = parts
                        compare_length = max(len(start), len(end))

                        if item_name_lower not in inflated_ranges:
                            if compare_length > 1:
                                inflated_ranges[item_name_lower] = inflate(start, end, compare_length)
                            else:
                                inflated_ranges[item_name_lower] = (start, end)

                        range_start, range_end = inflated_ranges[item_name_lower]
                        if not in_range(remaining_title[:compare_length], range_start[:compare_length], range_end[:compare_length]):
                            continue

                        # Found a matching range folder, go deeper
                        deeper = find_deepest(item, remaining_title)
                        return deeper if deeper != item else item

        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Error accessing folder {current_folder}: {e}")

        return best_match

    return find_deepest(root_folder, title_lower)


def find_directory_for_video(video: "Video", root_folder: Path) -> Path:
    """
    Determine the appropriate subfolder for a video title.

    Uses alphabetical range matching to find the deepest matching folder.
    Results are cached to avoid repeated filesystem traversals.

    Args:
        video: Video object with title information.
        root_folder: Root folder to search in.

    Returns:
        Path to the appropriate subfolder.
    """
    cache_key = (str(video.complete_path_original), str(root_folder))
    cached_result = subfolder_cache.get(cache_key)
    if cached_result:
        return cached_result

    # Special case for undetected FILMS only
    if (not video.title_fr or video.title_fr.strip() == '') and video.is_film_anim():
        non_detectes_dir = root_folder / 'non détectés'
        subfolder_cache.set(cache_key, non_detectes_dir)
        return non_detectes_dir

    title = video.name_without_article
    inflated_ranges: Dict[str, Tuple[str, str]] = {}

    def find_deepest_matching_folder(current_folder: Path, remaining_title: str) -> Path:
        best_match = current_folder
        try:
            for item in current_folder.iterdir():
                if not item.is_dir():
                    continue

                item_name_lower = item.name.lower()
                if '-' in item_name_lower and not (' - ' in item_name_lower):
                    start, end = item_name_lower.split('-', 1)
                    compare_length = max(len(start), len(end))
                    if item_name_lower not in inflated_ranges:
                        if compare_length > 1:
                            inflated_ranges[item_name_lower] = inflate(start, end, compare_length)
                        else:
                            inflated_ranges[item_name_lower] = (start, end)
                    start, end = inflated_ranges[item_name_lower]
                    if not in_range(remaining_title[:compare_length], start[:compare_length], end[:compare_length]):
                        continue
                elif not remaining_title.startswith(item.name.lower()):
                    continue

                if video.type_file == 'Séries':
                    series_folder = item / remaining_title
                    if series_folder.exists() and series_folder.is_dir():
                        return series_folder

                deeper_match = find_deepest_matching_folder(item, remaining_title)
                return deeper_match if deeper_match != item else item
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Error accessing folder {current_folder}: {e}")

        return best_match

    result = find_deepest_matching_folder(root_folder, title)

    # For series without matching folder, use '#' folder
    if video.type_file == 'Séries' and result == root_folder:
        result = root_folder / '#'

    subfolder_cache.set(cache_key, result)
    return result


def find_symlink_and_sub_dir(video: "Video", symlinks_dir: Path) -> Tuple[Path, Path]:
    """
    Find the appropriate symlink directory and subdirectory for a video.

    Args:
        video: Video object with type and genre information.
        symlinks_dir: Base symlinks directory.

    Returns:
        Tuple of (complete_dir_symlinks, sub_directory).
    """
    if video.is_film_anim():
        target = symlinks_dir / 'Films' / video.genre
    else:
        target = symlinks_dir / video.extended_sub

    video.complete_dir_symlinks = find_directory_for_video(video, target)

    try:
        # Extract relative path from symlinks directory
        relative_path = video.complete_dir_symlinks.relative_to(symlinks_dir)
        video.sub_directory = relative_path
    except ValueError as e:
        logger.warning(f'Error extracting relative path: {e}')
        video.sub_directory = Path('')

    return video.complete_dir_symlinks, video.sub_directory


def find_similar_file(
    video: "Video",
    storage_dir: Path,
    similarity_threshold: int = 80,
    year_tolerance: int = 1
) -> Optional[Path]:
    """
    Search for a similar file in the storage directory structure.

    Args:
        video: Video to find similar file for.
        storage_dir: Root storage directory.
        similarity_threshold: Minimum similarity score (0-100).
        year_tolerance: Maximum year difference allowed.

    Returns:
        Path to similar file if found, None otherwise.
    """
    if video.is_animation():
        folder = storage_dir / 'Films'
    else:
        folder = storage_dir / video.type_file

    root_folders = [folder / genre for genre in video.list_genres if genre]

    for root_folder in root_folders:
        if not root_folder.exists():
            continue
        subfolder = find_directory_for_video(video, root_folder)
        similar_file = find_similar_file_in_folder(
            video, subfolder, similarity_threshold, year_tolerance
        )
        if similar_file:
            return similar_file
    return None


def find_similar_file_in_folder(
    video: "Video",
    sub_folder: Path,
    similarity_threshold: int = 80,
    year_tolerance: int = 1
) -> Optional[Path]:
    """
    Search for a similar file in a specific folder.

    Uses fuzzy string matching to find files with similar titles.

    Args:
        video: Video to find similar file for.
        sub_folder: Folder to search in.
        similarity_threshold: Minimum similarity score (0-100).
        year_tolerance: Maximum year difference allowed.

    Returns:
        Path to best matching file if found, None otherwise.
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not available, skipping similarity check")
        return None

    def extract_title_year(filename: Path) -> Tuple[Optional[str], Optional[int]]:
        """Extract title and year from filename like 'Title (2020).mkv'."""
        filename_str = filename.name
        match = re.match(r"(.+?)\s*\((\d{4})\)", filename_str)
        if match:
            title = match.group(1).strip()
            year = int(match.group(2))
            return title.lower(), year
        return None, None

    if not sub_folder.exists():
        return None

    best_match = None
    highest_similarity = 0
    video_title = video.title_fr.lower() if video.title_fr else ""

    if not video_title:
        return None

    try:
        for file in sub_folder.rglob('*'):
            if not file.is_file():
                continue

            file_title, file_year = extract_title_year(file)
            if not file_title or not file_year:
                continue

            similarity = fuzz.ratio(video_title, file_title)
            if similarity <= similarity_threshold or similarity <= highest_similarity:
                continue

            if abs(video.date_film - file_year) > year_tolerance:
                continue

            best_match = file
            highest_similarity = similarity
    except (FileNotFoundError, PermissionError) as e:
        logger.warning(f"Error accessing folder {sub_folder}: {e}")

    return best_match


def clear_caches() -> None:
    """Clear all path resolution caches."""
    subfolder_cache.clear()
    series_subfolder_cache.clear()