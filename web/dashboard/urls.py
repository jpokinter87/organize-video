"""URL configuration for dashboard app."""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('logs/', views.logs, name='logs'),
]
