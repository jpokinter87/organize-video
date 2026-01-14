"""Video processing pipeline."""

from organize.pipeline.processor import (
    VideoProcessingResult,
    create_video_from_file,
    should_skip_duplicate,
    process_video_metadata,
    process_single_video_file,
    create_paths,
    process_video,
)
from organize.pipeline.series_handler import (
    format_season_folder,
    find_series_folder,
    build_episode_filename,
    should_create_season_folder,
    organize_episode_by_season,
    add_episodes_titles,
)
from organize.pipeline.video_list import (
    load_last_exec,
    get_last_exec_readonly,
    process_single_video,
    create_video_list,
)

__all__ = [
    "VideoProcessingResult",
    "create_video_from_file",
    "should_skip_duplicate",
    "process_video_metadata",
    "process_single_video_file",
    "create_paths",
    "process_video",
    "format_season_folder",
    "find_series_folder",
    "build_episode_filename",
    "should_create_season_folder",
    "organize_episode_by_season",
    "add_episodes_titles",
    "load_last_exec",
    "get_last_exec_readonly",
    "process_single_video",
    "create_video_list",
]
