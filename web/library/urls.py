"""URL configuration for library app."""

from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.index, name='index'),
    path('films/', views.films, name='films'),
    path('series/', views.series, name='series'),
    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
]
