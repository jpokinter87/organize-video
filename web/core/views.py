"""Core views for Video Organizer web interface."""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .models import ConfigurationSetting, ProcessingJob, Video, PendingConfirmation


def home(request):
    """Home page with summary dashboard."""
    # Get recent statistics
    context = {
        'total_videos': Video.objects.count(),
        'pending_confirmations': PendingConfirmation.objects.filter(is_resolved=False).count(),
        'active_jobs': ProcessingJob.objects.filter(
            status__in=['pending', 'scanning', 'processing', 'awaiting_confirmation']
        ).count(),
        'recent_videos': Video.objects.filter(
            status='completed'
        ).order_by('-updated_at')[:6],
        'recent_jobs': ProcessingJob.objects.order_by('-created_at')[:5],
    }
    return render(request, 'core/home.html', context)


def settings(request):
    """Settings page for configuration."""
    # Group settings by category
    all_settings = ConfigurationSetting.objects.all().order_by('key')

    # Organize settings into groups
    settings_groups = {
        'directories': {
            'title': 'Repertoires',
            'icon': 'folder',
            'settings': [],
        },
        'api': {
            'title': 'API',
            'icon': 'cloud',
            'settings': [],
        },
        'processing': {
            'title': 'Traitement',
            'icon': 'cog',
            'settings': [],
        },
    }

    # Define which settings go in which group
    group_mapping = {
        'search_dir': 'directories',
        'storage_dir': 'directories',
        'symlinks_dir': 'directories',
        'temp_symlinks_dir': 'directories',
        'tmdb_api_key': 'api',
        'tvdb_api_key': 'api',
        'default_days': 'processing',
        'dry_run_default': 'processing',
    }

    for setting in all_settings:
        group_key = group_mapping.get(setting.key, 'processing')
        if group_key in settings_groups:
            settings_groups[group_key]['settings'].append(setting)

    context = {
        'settings_groups': settings_groups,
    }
    return render(request, 'core/settings.html', context)


@require_http_methods(["POST"])
def settings_update(request):
    """Update a configuration setting via HTMX."""
    key = request.POST.get('key')
    value = request.POST.get('value')

    if not key:
        messages.error(request, "Cle de configuration manquante")
        return redirect('core:settings')

    try:
        setting = ConfigurationSetting.objects.get(key=key)
        setting.value = value
        setting.save()
        messages.success(request, f"Parametre '{key}' mis a jour")
    except ConfigurationSetting.DoesNotExist:
        # Create new setting
        ConfigurationSetting.objects.create(
            key=key,
            value=value,
            value_type='string',
            description=f"Custom setting: {key}"
        )
        messages.success(request, f"Parametre '{key}' cree")

    # If HTMX request, return partial
    if request.headers.get('HX-Request'):
        setting = ConfigurationSetting.objects.get(key=key)
        return render(request, 'core/partials/setting_row.html', {'setting': setting})

    return redirect('core:settings')


def settings_directories(request):
    """Directory configuration page."""
    directory_settings = ConfigurationSetting.objects.filter(
        key__in=['search_dir', 'storage_dir', 'symlinks_dir', 'temp_symlinks_dir']
    )

    context = {
        'settings': {s.key: s for s in directory_settings},
    }
    return render(request, 'core/settings_directories.html', context)


def settings_hash_db(request):
    """Hash database management page."""
    from .models import FileHash

    # Get hash database statistics
    hash_stats = {
        'total': FileHash.objects.count(),
        'by_category': {},
    }

    for category in ['films', 'series', 'animation', 'docs']:
        count = FileHash.objects.filter(category=category).count()
        if count > 0:
            hash_stats['by_category'][category] = count

    recent_hashes = FileHash.objects.order_by('-created_at')[:20]

    context = {
        'hash_stats': hash_stats,
        'recent_hashes': recent_hashes,
    }
    return render(request, 'core/settings_hash_db.html', context)
