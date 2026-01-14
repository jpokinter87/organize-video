"""Huey background tasks for video processing.

These tasks run asynchronously to handle long-running operations
like directory scanning, TMDB searches, and poster downloads.
"""

import logging
from huey.contrib.djhuey import task, periodic_task, db_task
from huey import crontab

logger = logging.getLogger(__name__)


@db_task()
def process_scan_job(job_id: int, auto_confirm: bool = False):
    """
    Process a scan job in the background.

    Args:
        job_id: ID of the ProcessingJob to execute.
        auto_confirm: If True, auto-accept first TMDB match.
    """
    from core.models import ProcessingJob, ProcessingLog
    from core.services import VideoProcessingService

    try:
        job = ProcessingJob.objects.get(id=job_id)
    except ProcessingJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return

    ProcessingLog.info(job=job, message="Starting background processing")

    service = VideoProcessingService()
    stats = service.run_job(job, auto_confirm=auto_confirm)

    ProcessingLog.info(
        job=job,
        message=f"Job completed: {stats['processed']}/{stats['total']} processed, "
                f"{stats['confirmed']} confirmed, {stats['skipped']} skipped"
    )

    return stats


@db_task()
def cache_poster(video_id: int):
    """
    Download and cache poster for a video.

    Args:
        video_id: ID of the Video to cache poster for.
    """
    from core.models import Video, ProcessingLog
    from core.services import TmdbService

    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Video {video_id} not found")
        return False

    if not video.poster_path:
        return False

    if video.poster_local:
        # Already cached
        return True

    service = TmdbService()
    success = service.cache_poster_for_video(video)

    if success:
        ProcessingLog.info(
            job=video.processing_job,
            video=video,
            message="Poster cached successfully"
        )

    return success


@db_task()
def search_tmdb_for_confirmation(confirmation_id: int, query: str = None):
    """
    Search TMDB for a pending confirmation.

    Args:
        confirmation_id: ID of the PendingConfirmation.
        query: Optional custom search query.
    """
    from core.models import PendingConfirmation, ProcessingLog
    from core.services import VideoProcessingService

    try:
        confirmation = PendingConfirmation.objects.select_related(
            'video', 'job'
        ).get(id=confirmation_id)
    except PendingConfirmation.DoesNotExist:
        logger.error(f"Confirmation {confirmation_id} not found")
        return

    video = confirmation.video
    if query:
        video.detected_title = query

    service = VideoProcessingService()
    candidates = service.search_tmdb_for_video(video)

    confirmation.tmdb_candidates = candidates
    confirmation.save()

    ProcessingLog.info(
        job=confirmation.job,
        video=video,
        message=f"TMDB search complete: {len(candidates)} candidates"
    )

    return len(candidates)


@db_task()
def complete_video_processing(video_id: int, dry_run: bool = False):
    """
    Complete processing for a confirmed video.

    Args:
        video_id: ID of the Video to process.
        dry_run: If True, don't actually move files.
    """
    from core.models import Video
    from core.services import VideoProcessingService

    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Video {video_id} not found")
        return False

    service = VideoProcessingService()
    return service.complete_processing(video, dry_run=dry_run)


@db_task()
def batch_cache_posters(video_ids: list):
    """
    Cache posters for multiple videos.

    Args:
        video_ids: List of Video IDs.
    """
    from core.models import Video
    from core.services import TmdbService

    service = TmdbService()
    success_count = 0

    for video_id in video_ids:
        try:
            video = Video.objects.get(id=video_id)
            if video.poster_path and not video.poster_local:
                if service.cache_poster_for_video(video):
                    success_count += 1
        except Video.DoesNotExist:
            continue

    return success_count


@periodic_task(crontab(hour='3', minute='0'))
def cleanup_old_logs():
    """
    Clean up old processing logs (runs daily at 3 AM).

    Keeps logs for 30 days.
    """
    from datetime import timedelta
    from django.utils import timezone
    from core.models import ProcessingLog

    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = ProcessingLog.objects.filter(created_at__lt=cutoff).delete()

    logger.info(f"Cleaned up {deleted} old log entries")
    return deleted


@periodic_task(crontab(hour='4', minute='0'))
def cleanup_orphan_posters():
    """
    Clean up orphaned poster files (runs daily at 4 AM).
    """
    import os
    from pathlib import Path
    from django.conf import settings
    from core.models import Video

    poster_dir = Path(settings.MEDIA_ROOT) / 'posters'
    if not poster_dir.exists():
        return 0

    # Get all poster filenames in use
    used_posters = set(
        Video.objects.exclude(poster_local='').values_list('poster_local', flat=True)
    )

    deleted = 0
    for poster_file in poster_dir.iterdir():
        relative_path = f"posters/{poster_file.name}"
        if relative_path not in used_posters:
            try:
                poster_file.unlink()
                deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {poster_file}: {e}")

    logger.info(f"Cleaned up {deleted} orphan poster files")
    return deleted


@task()
def test_tmdb_connection():
    """
    Test TMDB API connection.

    Returns:
        True if connection successful.
    """
    from core.services import TmdbService

    service = TmdbService()
    return service.test_connection()
