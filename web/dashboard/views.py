"""Dashboard views for statistics and logs."""

from django.shortcuts import render
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate

from core.models import Video, ProcessingJob, ProcessingLog, FileHash


def index(request):
    """Main dashboard with statistics."""
    # Video statistics
    video_stats = {
        'total': Video.objects.count(),
        'completed': Video.objects.filter(status='completed').count(),
        'pending': Video.objects.filter(status='pending').count(),
        'failed': Video.objects.filter(status='failed').count(),
    }

    # Category breakdown
    category_stats = Video.objects.filter(
        status='completed'
    ).values('category').annotate(count=Count('id')).order_by('-count')

    # Genre breakdown
    genre_stats = Video.objects.filter(
        status='completed'
    ).exclude(genre__isnull=True).exclude(genre='').values(
        'genre'
    ).annotate(count=Count('id')).order_by('-count')[:10]

    # Recent processing activity
    recent_activity = Video.objects.filter(
        status='completed'
    ).extra(
        select={'date': 'date(updated_at)'}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('-date')[:14]

    # Job statistics
    job_stats = {
        'total': ProcessingJob.objects.count(),
        'completed': ProcessingJob.objects.filter(status='completed').count(),
        'running': ProcessingJob.objects.filter(
            status__in=['pending', 'scanning', 'processing']
        ).count(),
    }

    # Storage statistics (from FileHash)
    hash_stats = {
        'total_files': FileHash.objects.count(),
        'total_size': FileHash.objects.aggregate(
            total=Sum('file_size')
        )['total'] or 0,
    }

    context = {
        'video_stats': video_stats,
        'category_stats': category_stats,
        'genre_stats': genre_stats,
        'recent_activity': recent_activity,
        'job_stats': job_stats,
        'hash_stats': hash_stats,
    }
    return render(request, 'dashboard/index.html', context)


def logs(request):
    """View processing logs."""
    level = request.GET.get('level')
    job_id = request.GET.get('job')

    logs = ProcessingLog.objects.all().select_related('job', 'video')

    if level:
        logs = logs.filter(level=level)
    if job_id:
        logs = logs.filter(job_id=job_id)

    logs = logs.order_by('-created_at')[:200]

    # Get filter options
    jobs = ProcessingJob.objects.all().order_by('-created_at')[:20]

    context = {
        'logs': logs,
        'jobs': jobs,
        'current_level': level,
        'current_job': job_id,
    }

    # HTMX partial
    if request.headers.get('HX-Request'):
        return render(request, 'dashboard/partials/log_list.html', context)

    return render(request, 'dashboard/logs.html', context)
