"""URL configuration for processing app."""

from django.urls import path
from . import views

app_name = 'processing'

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('new/', views.job_create, name='job_create'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('job/<int:job_id>/cancel/', views.job_cancel, name='job_cancel'),
    path('job/<int:job_id>/restart/', views.job_restart, name='job_restart'),
    path('confirmations/', views.confirmations, name='confirmations'),
    path('confirmations/<int:confirmation_id>/', views.confirmation_detail, name='confirmation_detail'),
    path('confirmations/<int:confirmation_id>/resolve/',
         views.resolve_confirmation, name='resolve_confirmation'),
    path('api/test-tmdb/', views.test_tmdb_api, name='test_tmdb_api'),
]
