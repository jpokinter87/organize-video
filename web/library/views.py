"""Library views for browsing organized videos."""

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q

from core.models import Video


def index(request):
    """Library main view with filters."""
    videos = Video.objects.filter(status='completed').order_by('-updated_at')

    # Apply filters
    category = request.GET.get('category')
    genre = request.GET.get('genre')
    search = request.GET.get('q')
    year = request.GET.get('year')

    if category:
        videos = videos.filter(category=category)
    if genre:
        videos = videos.filter(genre=genre)
    if year:
        videos = videos.filter(detected_year=year)
    if search:
        videos = videos.filter(
            Q(title_fr__icontains=search) |
            Q(title_original__icontains=search) |
            Q(detected_title__icontains=search)
        )

    # Pagination
    paginator = Paginator(videos, 24)
    page = request.GET.get('page', 1)
    videos_page = paginator.get_page(page)

    # Get filter options
    categories = Video.objects.filter(status='completed').values_list(
        'category', flat=True
    ).distinct()
    genres = Video.objects.filter(status='completed').exclude(
        genre__isnull=True
    ).exclude(genre='').values_list('genre', flat=True).distinct()
    years = Video.objects.filter(status='completed').exclude(
        detected_year__isnull=True
    ).values_list('detected_year', flat=True).distinct().order_by('-detected_year')

    context = {
        'videos': videos_page,
        'categories': categories,
        'genres': sorted(genres),
        'years': years,
        'current_category': category,
        'current_genre': genre,
        'current_year': year,
        'search_query': search,
    }

    # HTMX partial response
    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/video_grid.html', context)

    return render(request, 'library/index.html', context)


def films(request):
    """Films category view."""
    request.GET = request.GET.copy()
    request.GET['category'] = 'films'
    return index(request)


def series(request):
    """Series category view."""
    request.GET = request.GET.copy()
    request.GET['category'] = 'series'
    return index(request)


def video_detail(request, video_id):
    """Single video detail view."""
    video = get_object_or_404(Video, id=video_id)

    # Get similar videos (same genre)
    similar = []
    if video.genre:
        similar = Video.objects.filter(
            genre=video.genre, status='completed'
        ).exclude(id=video.id)[:6]

    context = {
        'video': video,
        'similar_videos': similar,
    }
    return render(request, 'library/video_detail.html', context)
