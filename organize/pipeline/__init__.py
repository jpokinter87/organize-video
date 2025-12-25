"""Video processing pipeline."""

from organize.pipeline.processor import (
    VideoProcessingResult,
    create_video_from_file,
    should_skip_duplicate,
    process_video_metadata,
    process_single_video_file,
)
from organize.pipeline.series_handler import (
    format_season_folder,
    find_series_folder,
    build_episode_filename,
    should_create_season_folder,
    organize_episode_by_season,
)

__all__ = [
    "VideoProcessingResult",
    "create_video_from_file",
    "should_skip_duplicate",
    "process_video_metadata",
    "process_single_video_file",
    "format_season_folder",
    "find_series_folder",
    "build_episode_filename",
    "should_create_season_folder",
    "organize_episode_by_season",
]
