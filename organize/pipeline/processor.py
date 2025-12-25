"""Video processing functions."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from loguru import logger

from organize.models.video import Video
from organize.utils.hash import checksum_md5
from organize.classification.type_detector import type_of_video

if TYPE_CHECKING:
    pass


@dataclass
class VideoProcessingResult:
    """
    Result of processing a single video file.

    Attributes:
        success: Whether processing completed successfully.
        video: The processed Video object (if successful).
        error: Error message (if failed).
        skipped: Whether video was skipped (e.g., duplicate).
        skip_reason: Reason for skipping.
    """

    success: bool = False
    video: Optional[Video] = None
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


def create_video_from_file(file_path: Path) -> Video:
    """
    Create a Video object from a file path.

    Extracts basic metadata like hash and type.

    Args:
        file_path: Path to the video file.

    Returns:
        Video object with basic metadata set.
    """
    video = Video()
    video.complete_path_original = file_path
    video.hash = checksum_md5(file_path)
    video.type_file = type_of_video(file_path)

    # Set extended_sub for series
    if video.is_serie():
        video.extended_sub = Path(video.type_file) / "Séries TV"
    else:
        video.extended_sub = Path("")

    return video


def should_skip_duplicate(
    hash_value: str,
    force_mode: bool,
    dry_run: bool,
    hash_exists_fn: Callable[[str], bool]
) -> bool:
    """
    Check if video should be skipped due to being a duplicate.

    Args:
        hash_value: MD5 hash of the video file.
        force_mode: If True, never skip duplicates.
        dry_run: If True, don't check for duplicates.
        hash_exists_fn: Function to check if hash exists in database.

    Returns:
        True if video should be skipped.
    """
    # Never skip in force mode or dry run
    if force_mode or dry_run:
        if dry_run:
            logger.debug(f"SIMULATION - Hash check skipped")
        return False

    # Check if hash exists
    if hash_exists_fn(hash_value):
        logger.info(f"Hash already exists in database")
        return True

    return False


def process_video_metadata(video: Video) -> Video:
    """
    Process and extract metadata from video file.

    Uses guessit to extract title, year, season/episode info.

    Args:
        video: Video object with complete_path_original set.

    Returns:
        Video with metadata fields populated.
    """
    from organize.classification.type_detector import extract_file_infos

    (
        video.title,
        video.date_film,
        video.sequence,
        video.season,
        video.episode,
        video.spec
    ) = extract_file_infos(video)

    return video


def process_single_video_file(
    file_path: Path,
    force_mode: bool = False,
    dry_run: bool = False,
    hash_exists_fn: Optional[Callable[[str], bool]] = None,
    add_hash_fn: Optional[Callable[[str], None]] = None
) -> VideoProcessingResult:
    """
    Process a single video file.

    Args:
        file_path: Path to the video file.
        force_mode: If True, skip duplicate checks.
        dry_run: If True, simulate operations.
        hash_exists_fn: Function to check if hash exists.
        add_hash_fn: Function to add hash to database.

    Returns:
        VideoProcessingResult with processing outcome.
    """
    try:
        # Create video object with basic metadata
        video = create_video_from_file(file_path)

        # Check for duplicates
        if hash_exists_fn is not None:
            if should_skip_duplicate(video.hash, force_mode, dry_run, hash_exists_fn):
                return VideoProcessingResult(
                    success=True,
                    skipped=True,
                    skip_reason=f"Duplicate hash: {video.hash[:8]}..."
                )

        # Extract detailed metadata
        video = process_video_metadata(video)

        # Add hash to database if not dry run
        if add_hash_fn is not None and not dry_run and not force_mode:
            add_hash_fn(video.hash)
        elif dry_run:
            logger.debug(f"SIMULATION - Hash add skipped for {file_path.name}")

        return VideoProcessingResult(success=True, video=video)

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return VideoProcessingResult(success=False, error=str(e))
