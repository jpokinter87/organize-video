"""Processing views for scan jobs and confirmations."""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings

from core.models import ProcessingJob, Video, PendingConfirmation, ProcessingLog
from core.services import VideoProcessingService, TmdbService
from core.tasks import process_scan_job, cache_poster, search_tmdb_for_confirmation

logger = logging.getLogger(__name__)


def job_list(request):
    """List all processing jobs."""
    jobs = ProcessingJob.objects.all().order_by('-created_at')

    context = {
        'jobs': jobs,
        'pending_count': PendingConfirmation.objects.filter(is_resolved=False).count(),
    }
    return render(request, 'processing/job_list.html', context)


def job_create(request):
    """Create a new processing job."""
    if request.method == 'POST':
        job = ProcessingJob.objects.create(
            source_directory=request.POST.get('source_directory', ''),
            categories=request.POST.getlist('categories') or None,
            process_all=request.POST.get('process_all') == 'on',
            days_back=int(request.POST.get('days_back', 7)),
            force_mode=request.POST.get('force_mode') == 'on',
            dry_run=request.POST.get('dry_run') == 'on',
            status='pending',
        )

        # Trigger background task
        if settings.DEBUG:
            # In debug mode, Huey runs synchronously
            process_scan_job(job.id)
        else:
            process_scan_job(job.id)

        messages.success(request, f"Job #{job.id} lance")
        return redirect('processing:job_detail', job_id=job.id)

    # Get default directories
    service = VideoProcessingService()

    context = {
        'categories': ['films', 'series', 'animation', 'docs'],
        'default_directory': str(service.get_search_directory()),
    }
    return render(request, 'processing/job_create.html', context)


def job_detail(request, job_id):
    """View processing job details and progress."""
    job = get_object_or_404(ProcessingJob, id=job_id)
    videos = Video.objects.filter(job=job).order_by('-created_at')[:50]
    logs = ProcessingLog.objects.filter(job=job).order_by('-created_at')[:50]
    confirmations = PendingConfirmation.objects.filter(
        job=job, is_resolved=False
    )

    context = {
        'job': job,
        'videos': videos,
        'logs': logs,
        'confirmations': confirmations,
    }

    # HTMX partial for progress updates
    if request.headers.get('HX-Request'):
        return render(request, 'processing/partials/job_progress.html', context)

    return render(request, 'processing/job_detail.html', context)


def confirmations(request):
    """List all pending confirmations."""
    pending = PendingConfirmation.objects.filter(
        is_resolved=False
    ).select_related('video', 'job').order_by('created_at')

    # Check if we need to show modal for specific confirmation
    modal_id = request.GET.get('modal')
    modal_confirmation = None
    if modal_id:
        try:
            modal_confirmation = pending.get(id=modal_id)
        except PendingConfirmation.DoesNotExist:
            pass

    context = {
        'confirmations': pending,
        'modal_confirmation': modal_confirmation,
    }
    return render(request, 'processing/confirmations.html', context)


@require_POST
def resolve_confirmation(request, confirmation_id):
    """Resolve a pending confirmation."""
    confirmation = get_object_or_404(
        PendingConfirmation.objects.select_related('video', 'job'),
        id=confirmation_id
    )

    action = request.POST.get('action')
    service = VideoProcessingService()

    if action == 'accept':
        tmdb_id = request.POST.get('tmdb_id')
        if tmdb_id:
            success = service.resolve_confirmation(
                confirmation,
                action='accept',
                tmdb_id=int(tmdb_id)
            )
            if success:
                messages.success(request, f"Confirme: {confirmation.video.title_fr}")

                # Trigger poster caching
                if confirmation.video.poster_path:
                    cache_poster(confirmation.video.id)

    elif action == 'skip':
        service.resolve_confirmation(confirmation, action='skip')
        messages.info(request, "Video ignoree")

    elif action == 'manual':
        manual_title = request.POST.get('manual_title', '').strip()
        if manual_title:
            service.resolve_confirmation(
                confirmation,
                action='manual',
                manual_title=manual_title
            )
            messages.info(request, f"Recherche: {manual_title}")

            # HTMX: return updated confirmation with new candidates
            if request.headers.get('HX-Request'):
                confirmation.refresh_from_db()
                return render(request, 'components/confirmation_modal.html', {
                    'confirmation': confirmation
                })

    # HTMX response
    if request.headers.get('HX-Request'):
        # Return next confirmation or empty state
        next_conf = PendingConfirmation.objects.filter(
            is_resolved=False
        ).exclude(id=confirmation_id).select_related('video').first()

        if next_conf:
            return render(request, 'processing/partials/confirmation_card.html', {
                'confirmation': next_conf
            })
        return render(request, 'processing/partials/no_confirmations.html')

    return redirect('processing:confirmations')


def job_cancel(request, job_id):
    """Cancel a running job."""
    job = get_object_or_404(ProcessingJob, id=job_id)

    if job.status in ['pending', 'scanning', 'processing', 'awaiting_confirmation']:
        job.status = 'cancelled'
        job.save()

        ProcessingLog.warning(job=job, message="Job cancelled by user")
        messages.warning(request, f"Job #{job.id} annule")
    else:
        messages.error(request, "Ce job ne peut pas etre annule")

    return redirect('processing:job_detail', job_id=job.id)


def job_restart(request, job_id):
    """Restart a failed or cancelled job."""
    job = get_object_or_404(ProcessingJob, id=job_id)

    if job.status in ['failed', 'cancelled']:
        # Create a new job with same parameters
        new_job = ProcessingJob.objects.create(
            source_directory=job.source_directory,
            categories=job.categories,
            process_all=job.process_all,
            days_back=job.days_back,
            force_mode=job.force_mode,
            dry_run=job.dry_run,
            status='pending',
        )

        process_scan_job(new_job.id)
        messages.success(request, f"Nouveau job #{new_job.id} lance")
        return redirect('processing:job_detail', job_id=new_job.id)

    messages.error(request, "Ce job ne peut pas etre relance")
    return redirect('processing:job_detail', job_id=job.id)


def confirmation_detail(request, confirmation_id):
    """Get detailed view of a single confirmation (for modal)."""
    confirmation = get_object_or_404(
        PendingConfirmation.objects.select_related('video', 'job'),
        id=confirmation_id
    )

    context = {
        'confirmation': confirmation,
    }
    return render(request, 'components/confirmation_modal.html', context)


def test_tmdb_api(request):
    """Test TMDB API connection."""
    service = TmdbService()
    connected = service.test_connection()

    return JsonResponse({
        'connected': connected,
        'api_key_configured': bool(service.api_key),
    })
