"""Pipeline orchestration for video organization."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from tqdm import tqdm

from organize.models.video import Video


@dataclass
class ProcessingStats:
    """Statistics from video processing."""

    films: int = 0
    series: int = 0
    animation: int = 0
    docs: int = 0
    undetected: int = 0
    total: int = 0

    @classmethod
    def from_videos(cls, videos: List[Video]) -> "ProcessingStats":
        """Calculate statistics from a list of videos."""
        return cls(
            films=sum(1 for v in videos if v.is_film()),
            series=sum(1 for v in videos if v.is_serie() and v.title_fr),
            animation=sum(1 for v in videos if v.is_animation()),
            docs=sum(1 for v in videos if v.type_file in {'Docs', 'Docs#1'}),
            undetected=sum(1 for v in videos if v.is_film_anim() and (not v.title_fr or v.genre == "Non detecte")),
            total=len(videos)
        )


@dataclass
class PipelineContext:
    """Context for pipeline execution."""

    search_dir: Path
    storage_dir: Path
    symlinks_dir: Path
    output_dir: Path
    work_dir: Path
    temp_dir: Path
    original_dir: Path
    waiting_folder: Path
    dry_run: bool = False
    force_mode: bool = False
    days_to_process: float = 0


class PipelineOrchestrator:
    """
    Orchestrates the video processing pipeline.

    Separates the main processing logic from CLI concerns,
    making it easier to test and maintain.
    """

    def __init__(self, context: PipelineContext):
        """
        Initialize the orchestrator.

        Args:
            context: Pipeline execution context with directories and flags.
        """
        self.context = context
        self._title_cache: Dict[str, Tuple] = {}

    def process_videos(self, videos: List[Video]) -> ProcessingStats:
        """
        Process a list of videos through the pipeline.

        Args:
            videos: List of Video objects to process.

        Returns:
            ProcessingStats with counts by type.
        """
        from organize.classification import media_info, format_undetected_filename
        from organize.filesystem import (
            find_directory_for_video,
            find_symlink_and_sub_dir,
            rename_video,
            move_file_new_nas,
        )
        from organize.pipeline import process_video, set_fr_title_and_category

        with tqdm(videos, desc="Traitement des videos", unit="fichier") as pbar:
            for video in pbar:
                pbar.set_postfix_str(f"{video.complete_path_original.name[:30]}...")

                try:
                    self._process_single_video(
                        video,
                        rename_video,
                        move_file_new_nas,
                        process_video,
                        set_fr_title_and_category,
                        find_directory_for_video,
                        find_symlink_and_sub_dir,
                        media_info,
                        format_undetected_filename,
                    )
                except (OSError, IOError, ValueError) as e:
                    logger.error(f"Erreur lors du traitement de {video.complete_path_original.name}: {e}")
                    continue

        return ProcessingStats.from_videos(videos)

    def _process_single_video(
        self,
        video: Video,
        rename_video_fn,
        move_file_fn,
        process_video_fn,
        set_fr_title_fn,
        find_directory_fn,
        find_symlink_fn,
        media_info_fn,
        format_undetected_fn,
    ) -> None:
        """Process a single video through the pipeline."""
        ctx = self.context

        # Process documentaries (simple path)
        if video.type_file in {'Docs', 'Docs#1'}:
            rename_video_fn(video, self._title_cache, video.type_file, ctx.work_dir, ctx.dry_run)
            move_file_fn(video, ctx.storage_dir, ctx.dry_run)
            return

        # Check cache for repeated titles
        cache_key = video.title
        if cache_key in self._title_cache:
            self._apply_cached_metadata(video, cache_key)
        else:
            self._process_new_video(
                video,
                set_fr_title_fn,
                find_directory_fn,
                find_symlink_fn,
                media_info_fn,
                format_undetected_fn,
            )

        # Process video for duplicates
        processed_video = process_video_fn(
            video, ctx.waiting_folder, ctx.storage_dir, ctx.symlinks_dir
        )
        if processed_video:
            rename_video_fn(
                processed_video, self._title_cache,
                str(processed_video.sub_directory), ctx.work_dir, ctx.dry_run
            )
            move_file_fn(processed_video, ctx.storage_dir, ctx.dry_run)

    def _apply_cached_metadata(self, video: Video, cache_key: str) -> None:
        """Apply cached metadata to video."""
        (video.title_fr, video.date_film, video.genre,
         video.complete_dir_symlinks, video.sub_directory, cached_spec) = self._title_cache[cache_key]

        if not video.spec or len(video.spec.split()) < 3:
            video.spec = cached_spec

        video.formatted_filename = video.format_name(video.title_fr)
        logger.info(f"{video.formatted_filename} ({video.genre}) - formate (depuis cache)")

    def _process_new_video(
        self,
        video: Video,
        set_fr_title_fn,
        find_directory_fn,
        find_symlink_fn,
        media_info_fn,
        format_undetected_fn,
    ) -> None:
        """Process a video that's not in cache."""
        ctx = self.context
        original_spec = video.spec
        video = set_fr_title_fn(video)

        # Handle undetected films
        if (not video.title_fr or video.title_fr.strip() == '') and video.is_film_anim():
            video.title_fr = ""
            video.date_film = 0
            video.genre = "Non detecte"
            video.list_genres = ["Non detecte"]
            video.spec = original_spec
            video.formatted_filename = format_undetected_fn(video)
            video.sub_directory = Path('Films/non detectes')
            video.complete_dir_symlinks = find_directory_fn(
                video, ctx.symlinks_dir / 'Films'
            )
        else:
            # Normal processing
            video.complete_dir_symlinks, video.sub_directory = find_symlink_fn(
                video, ctx.symlinks_dir
            )

            # Enhance specs if needed
            if not video.spec or len(video.spec.split()) < 3:
                media_spec = media_info_fn(video)
                if media_spec:
                    video.spec = media_spec

            video.formatted_filename = video.format_name(video.title_fr)

        # Cache results
        if video.title_fr and video.title:
            self._title_cache[video.title] = (
                video.title_fr, video.date_film, video.genre,
                video.complete_dir_symlinks, video.sub_directory, video.spec
            )

    def process_series_titles(self, videos: List[Video]) -> None:
        """
        Add episode titles to series videos.

        Args:
            videos: List of all processed videos.
        """
        from organize.pipeline import add_episodes_titles
        from organize.filesystem import cleanup_work_directory

        series_videos = [v for v in videos if v.is_serie() and v.title_fr]
        if not series_videos:
            return

        if not self.context.dry_run:
            cleanup_work_directory(self.context.work_dir)

        add_episodes_titles(
            series_videos,
            self.context.work_dir / 'Series/Series TV',
            self.context.dry_run
        )

    def finalize(self) -> None:
        """Perform final operations (copy to destination, verify symlinks)."""
        from organize.filesystem import copy_tree, verify_symlinks

        ctx = self.context
        if ctx.work_dir.exists() and any(ctx.work_dir.iterdir()):
            copy_tree(ctx.work_dir, ctx.output_dir, ctx.dry_run)

            if not ctx.dry_run:
                verify_symlinks(ctx.output_dir)
