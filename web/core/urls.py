"""URL configuration for core app."""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('settings/', views.settings, name='settings'),
    path('settings/update/', views.settings_update, name='settings_update'),
    path('settings/directories/', views.settings_directories, name='settings_directories'),
    path('settings/hash-db/', views.settings_hash_db, name='settings_hash_db'),
]
