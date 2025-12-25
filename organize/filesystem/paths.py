"""Path resolution functions for video organization."""

from pathlib import Path
from typing import Dict, Tuple

from loguru import logger


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
