"""Filesystem operations for video organization."""

from organize.filesystem.discovery import (
    get_available_categories,
    get_files,
    count_videos,
)
from organize.filesystem.symlinks import (
    create_symlink,
    verify_symlinks,
    is_valid_symlink,
)
from organize.filesystem.file_ops import (
    move_file,
    copy_tree,
    ensure_unique_destination,
    setup_working_directories,
)
from organize.filesystem.paths import (
    in_range,
    inflate,
    find_matching_folder,
)

__all__ = [
    "get_available_categories",
    "get_files",
    "count_videos",
    "create_symlink",
    "verify_symlinks",
    "is_valid_symlink",
    "move_file",
    "copy_tree",
    "ensure_unique_destination",
    "setup_working_directories",
    "in_range",
    "inflate",
    "find_matching_folder",
]
