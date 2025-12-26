"""Video Processing Service for Django web interface.

Integrates with the organize package to scan directories,
extract metadata, and manage video processing workflow.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from core.models import (
    Video, ProcessingJob, PendingConfirmation,
    ProcessingLog, FileHash, ConfigurationSetting
)
from .tmdb_service import TmdbService

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """
    Service for processing video files.

    Handles directory scanning, metadata extraction,
    TMDB matching, and confirmation workflow.
    """

    # Supported video extensions
    VIDEO_EXTENSIONS = {
        '.mkv', '.avi', '.mp4', '.m4v', '.mov',
        '.wmv', '.flv', '.webm', '.ts', '.m2ts'
    }

    # Category directory mappings
    CATEGORY_DIRS = {
        'films': ['Films'],
        'series': ['Séries', 'Series'],
        'animation': ['Animation'],
        'docs': ['Docs', 'Docs#1'],
    }

    def __init__(self):
        """Initialize video processing service."""
        self.tmdb_service = TmdbService()
        self._guessit = None
        self._mediainfo = None

    @property
    def guessit(self):
        """Lazy load guessit."""
        if self._guessit is None:
            try:
                import guessit
                self._guessit = guessit.guessit
            except ImportError:
                logger.warning("guessit not installed")
                self._guessit = lambda x: {}
        return self._guessit

    def get_search_directory(self) -> Path:
        """Get configured search directory."""
        setting = ConfigurationSetting.objects.filter(key='search_dir').first()
        if setting and setting.value:
            return Path(setting.value)
        return getattr(settings, 'DEFAULT_SEARCH_DIR', Path('/media/NAS64/temp'))

    def get_storage_directory(self) -> Path:
        """Get configured storage directory."""
        setting = ConfigurationSetting.objects.filter(key='storage_dir').first()
        if setting and setting.value:
            return Path(setting.value)
        return getattr(settings, 'DEFAULT_STORAGE_DIR', Path('/media/NAS64'))

    def scan_directory(
        self,
        job: ProcessingJob,
        directory: Optional[Path] = None,
        categories: Optional[List[str]] = None,
        days_back: Optional[int] = None,
        process_all: bool = False
    ) -> List[Path]:
        """
        Scan directory for video files.

        Args:
            job: ProcessingJob instance to update.
            directory: Directory to scan (uses default if None).
            categories: List of categories to scan.
            days_back: Only include files modified within N days.
            process_all: If True, ignore days_back filter.

        Returns:
            List of video file paths found.
        """
        base_dir = directory or self.get_search_directory()
        if not base_dir.exists():
            ProcessingLog.error(
                job=job,
                message=f"Directory not found: {base_dir}"
            )
            return []

        categories = categories or list(self.CATEGORY_DIRS.keys())
        cutoff_time = None
        if not process_all and days_back:
            cutoff_time = datetime.now() - timedelta(days=days_back)

        video_files = []

        for category in categories:
            category_names = self.CATEGORY_DIRS.get(category, [category])

            for cat_name in category_names:
                cat_dir = base_dir / cat_name
                if not cat_dir.exists():
                    continue

                ProcessingLog.info(
                    job=job,
                    message=f"Scanning {cat_dir}"
                )

                for file_path in cat_dir.rglob('*'):
                    if not file_path.is_file():
                        continue
                    if file_path.suffix.lower() not in self.VIDEO_EXTENSIONS:
                        continue

                    # Check modification time
                    if cutoff_time:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime < cutoff_time:
                            continue

                    video_files.append(file_path)

        ProcessingLog.info(
            job=job,
            message=f"Found {len(video_files)} video files"
        )

        return video_files

    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from video filename using guessit.

        Args:
            file_path: Path to video file.

        Returns:
            Dictionary with extracted metadata.
        """
        guess = self.guessit(file_path.name)

        return {
            'detected_title': guess.get('title', file_path.stem),
            'detected_year': guess.get('year'),
            'detected_season': guess.get('season'),
            'detected_episode': guess.get('episode'),
            'video_codec': guess.get('video_codec'),
            'resolution': guess.get('screen_size'),
            'language': str(guess.get('language', '')),
            'release_group': guess.get('release_group'),
            'source': guess.get('source'),
        }

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of file (first 10MB).

        Args:
            file_path: Path to file.

        Returns:
            MD5 hash string.
        """
        hash_md5 = hashlib.md5()
        chunk_size = 10 * 1024 * 1024  # 10MB

        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(chunk_size)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation failed for {file_path}: {e}")
            return ''

    def check_duplicate(
        self,
        file_hash: str,
        category: str
    ) -> Optional[FileHash]:
        """
        Check if file hash already exists.

        Args:
            file_hash: MD5 hash to check.
            category: Category to check in.

        Returns:
            FileHash instance if duplicate found, None otherwise.
        """
        return FileHash.objects.filter(
            file_hash=file_hash,
            category=category
        ).first()

    def determine_category(self, file_path: Path) -> str:
        """
        Determine video category from path.

        Args:
            file_path: Path to video file.

        Returns:
            Category string (films, series, animation, docs).
        """
        path_parts = [p.lower() for p in file_path.parts]

        for category, dir_names in self.CATEGORY_DIRS.items():
            for dir_name in dir_names:
                if dir_name.lower() in path_parts:
                    return category

        # Default based on metadata
        metadata = self.extract_metadata(file_path)
        if metadata.get('detected_season') or metadata.get('detected_episode'):
            return 'series'

        return 'films'

    def process_video_file(
        self,
        job: ProcessingJob,
        file_path: Path,
        force_mode: bool = False
    ) -> Optional[Video]:
        """
        Process a single video file.

        Args:
            job: ProcessingJob instance.
            file_path: Path to video file.
            force_mode: If True, skip hash duplicate check.

        Returns:
            Video instance if processing started, None if skipped.
        """
        try:
            # Extract metadata
            metadata = self.extract_metadata(file_path)
            category = self.determine_category(file_path)

            # Calculate hash
            file_hash = self.calculate_file_hash(file_path)

            # Check for duplicates (unless force mode)
            if not force_mode and file_hash:
                existing = self.check_duplicate(file_hash, category)
                if existing:
                    ProcessingLog.info(
                        job=job,
                        message=f"Duplicate found: {file_path.name}",
                        details=f"Matches: {existing.filename}"
                    )
                    return None

            # Get file info
            stat = file_path.stat()

            # Create Video record
            video = Video.objects.create(
                job=job,
                original_path=str(file_path.parent),
                original_filename=file_path.name,
                file_hash=file_hash,
                file_size=stat.st_size,
                category=category,
                status='pending',
                **metadata
            )

            ProcessingLog.info(
                job=job,
                video=video,
                message=f"Processing: {file_path.name}"
            )

            return video

        except Exception as e:
            ProcessingLog.error(
                job=job,
                message=f"Error processing {file_path.name}: {e}"
            )
            return None

    def search_tmdb_for_video(
        self,
        video: Video
    ) -> List[Dict[str, Any]]:
        """
        Search TMDB for video matches.

        Args:
            video: Video instance to search for.

        Returns:
            List of candidate dictionaries.
        """
        query = video.detected_title
        year = video.detected_year
        content_type = video.category

        candidates = self.tmdb_service.search(query, content_type, year)

        # Enrich with director info
        candidates = self.tmdb_service.enrich_candidates_with_details(candidates)

        return [c.to_dict() for c in candidates]

    def create_confirmation(
        self,
        video: Video,
        job: ProcessingJob,
        confirmation_type: str = 'title_match'
    ) -> PendingConfirmation:
        """
        Create a pending confirmation for video.

        Args:
            video: Video requiring confirmation.
            job: Parent processing job.
            confirmation_type: Type of confirmation needed.

        Returns:
            PendingConfirmation instance.
        """
        # Search TMDB for candidates
        candidates = self.search_tmdb_for_video(video)

        confirmation = PendingConfirmation.objects.create(
            video=video,
            job=job,
            confirmation_type=confirmation_type,
            tmdb_candidates=candidates,
            is_resolved=False
        )

        video.status = 'awaiting_confirmation'
        video.save()

        ProcessingLog.info(
            job=job,
            video=video,
            message=f"Confirmation created: {len(candidates)} candidates"
        )

        return confirmation

    def resolve_confirmation(
        self,
        confirmation: PendingConfirmation,
        action: str,
        tmdb_id: Optional[int] = None,
        manual_title: Optional[str] = None
    ) -> bool:
        """
        Resolve a pending confirmation.

        Args:
            confirmation: Confirmation to resolve.
            action: 'accept', 'skip', or 'manual'.
            tmdb_id: Selected TMDB ID (for accept).
            manual_title: Manual title entry (for manual search).

        Returns:
            True if resolved successfully.
        """
        video = confirmation.video

        if action == 'accept' and tmdb_id:
            # Fetch full details from TMDB
            media_type = 'tv' if video.category == 'series' else 'movie'
            details = self.tmdb_service.get_details(tmdb_id, media_type)

            if details:
                video.tmdb_id = tmdb_id
                video.title_fr = details.get('title', '')
                video.title_original = details.get('original_title', '')
                video.overview = details.get('overview', '')
                video.poster_path = details.get('poster_path', '')
                video.vote_average = details.get('vote_average', 0)
                video.directors = details.get('directors', [])
                video.cast = details.get('cast', [])
                video.genres_list = details.get('genres', [])

                if video.genres_list:
                    video.genre = video.genres_list[0]

                video.status = 'confirmed'
                video.save()

                # Cache poster
                if video.poster_path:
                    self.tmdb_service.cache_poster_for_video(video)

                confirmation.selected_tmdb_id = tmdb_id
                confirmation.resolution = 'accepted'
                confirmation.is_resolved = True
                confirmation.save()

                ProcessingLog.success(
                    job=confirmation.job,
                    video=video,
                    message=f"Confirmed: {video.title_fr}"
                )
                return True

        elif action == 'skip':
            video.status = 'skipped'
            video.save()

            confirmation.resolution = 'skipped'
            confirmation.is_resolved = True
            confirmation.save()

            ProcessingLog.info(
                job=confirmation.job,
                video=video,
                message="Video skipped by user"
            )
            return True

        elif action == 'manual' and manual_title:
            # Search with manual title
            confirmation.manual_title = manual_title
            confirmation.save()

            # Get new candidates
            video.detected_title = manual_title
            video.save()

            candidates = self.search_tmdb_for_video(video)
            confirmation.tmdb_candidates = candidates
            confirmation.save()

            ProcessingLog.info(
                job=confirmation.job,
                video=video,
                message=f"Manual search: {manual_title} - {len(candidates)} results"
            )
            return True

        return False

    def complete_processing(
        self,
        video: Video,
        dry_run: bool = False
    ) -> bool:
        """
        Complete video processing (rename, move, create symlinks).

        Args:
            video: Confirmed video to process.
            dry_run: If True, don't actually move files.

        Returns:
            True if processing completed successfully.
        """
        if video.status != 'confirmed':
            return False

        try:
            # Generate formatted filename
            video.formatted_filename = self.generate_filename(video)

            if not dry_run:
                # TODO: Implement actual file operations
                # - Move to storage directory
                # - Create symlinks
                # - Update hash database
                pass

            video.status = 'completed'
            video.save()

            # Add to hash database
            if video.file_hash:
                FileHash.objects.get_or_create(
                    file_hash=video.file_hash,
                    defaults={
                        'filename': video.formatted_filename or video.original_filename,
                        'category': video.category,
                        'file_size': video.file_size,
                    }
                )

            ProcessingLog.success(
                job=video.job,
                video=video,
                message=f"Completed: {video.formatted_filename}"
            )
            return True

        except Exception as e:
            video.status = 'failed'
            video.save()

            ProcessingLog.error(
                job=video.job,
                video=video,
                message=f"Processing failed: {e}"
            )
            return False

    def generate_filename(self, video: Video) -> str:
        """
        Generate standardized filename for video.

        Args:
            video: Video instance.

        Returns:
            Formatted filename string.
        """
        parts = []

        # Title
        title = video.title_fr or video.detected_title or 'Unknown'
        title = title.replace('/', '-').replace(':', ' -')
        parts.append(title)

        # Year
        if video.detected_year:
            parts.append(f"({video.detected_year})")

        # Season/Episode for series
        if video.category == 'series':
            if video.detected_season:
                se = f"S{video.detected_season:02d}"
                if video.detected_episode:
                    se += f"E{video.detected_episode:02d}"
                parts.append(se)

        # Tech specs
        specs = []
        if video.resolution:
            specs.append(video.resolution)
        if video.video_codec:
            specs.append(video.video_codec)

        if specs:
            parts.append(f"[{' '.join(specs)}]")

        # Get original extension
        original_path = Path(video.original_filename)
        extension = original_path.suffix

        return ' '.join(parts) + extension

    def run_job(
        self,
        job: ProcessingJob,
        auto_confirm: bool = False
    ) -> Dict[str, int]:
        """
        Run a complete processing job.

        Args:
            job: ProcessingJob to execute.
            auto_confirm: If True, auto-accept first TMDB match.

        Returns:
            Dictionary with processing statistics.
        """
        stats = {
            'total': 0,
            'processed': 0,
            'confirmed': 0,
            'skipped': 0,
            'failed': 0,
        }

        try:
            job.status = 'scanning'
            job.started_at = timezone.now()
            job.save()

            # Scan for files
            directory = Path(job.source_directory) if job.source_directory else None
            files = self.scan_directory(
                job=job,
                directory=directory,
                categories=job.categories or None,
                days_back=job.days_back,
                process_all=job.process_all
            )

            stats['total'] = len(files)
            job.progress_total = len(files)
            job.status = 'processing'
            job.save()

            # Process each file
            for i, file_path in enumerate(files):
                job.current_file = file_path.name
                job.progress_processed = i + 1
                job.save()

                video = self.process_video_file(
                    job=job,
                    file_path=file_path,
                    force_mode=job.force_mode
                )

                if video:
                    stats['processed'] += 1

                    # Create confirmation
                    confirmation = self.create_confirmation(video, job)

                    if auto_confirm and confirmation.tmdb_candidates:
                        # Auto-accept first candidate
                        first = confirmation.tmdb_candidates[0]
                        self.resolve_confirmation(
                            confirmation,
                            'accept',
                            tmdb_id=first['id']
                        )
                        stats['confirmed'] += 1
                else:
                    stats['skipped'] += 1

            # Update job status
            pending_count = PendingConfirmation.objects.filter(
                job=job, is_resolved=False
            ).count()

            if pending_count > 0:
                job.status = 'awaiting_confirmation'
            else:
                job.status = 'completed'
                job.completed_at = timezone.now()

            job.progress_confirmed = stats['confirmed']
            job.progress_failed = stats['failed']
            job.current_file = ''
            job.save()

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()

            ProcessingLog.error(job=job, message=f"Job failed: {e}")
            logger.exception(f"Job {job.id} failed")

        return stats
