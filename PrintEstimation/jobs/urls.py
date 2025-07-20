"""
Jobs app URLs.
"""

from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # path('', views.JobListView.as_view(), name='list'),
    # path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    # path('create/', views.JobCreateView.as_view(), name='create'),
    # path('<int:pk>/', views.JobDetailView.as_view(), name='detail'),
    # path('<int:pk>/edit/', views.JobUpdateView.as_view(), name='edit'),
    # path('<int:pk>/delete/', views.JobDeleteView.as_view(), name='delete'),
    # path('<int:pk>/calculate/', views.JobCalculateView.as_view(), name='calculate'),
    # path('templates/', views.TemplateListView.as_view(), name='templates'),
]