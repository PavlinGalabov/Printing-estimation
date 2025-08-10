"""
Jobs app URLs.
"""

from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.JobListView.as_view(), name='list'),
    path('create/', views.JobCreateView.as_view(), name='create'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.JobUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.JobDeleteView.as_view(), name='delete'),
    path('<int:pk>/change-status/', views.change_job_status, name='change_status'),
    path('<int:pk>/reorder-operations/', views.ReorderOperationsView.as_view(), name='reorder_operations'),
    path('<int:job_id>/add-operation/', views.add_operation_to_job, name='add_operation'),
    path('<int:job_id>/remove-operation/<int:operation_id>/', views.remove_operation_from_job, name='remove_operation'),
    path('templates/', views.TemplateListView.as_view(), name='templates'),
    
    # PDF Export URLs
    path('pdf-exports/', views.JobPDFExportListView.as_view(), name='pdf_export_list'),
    path('<int:pk>/pdf-generate/', views.JobPDFGenerateView.as_view(), name='pdf_generate'),
    path('pdf-exports/history/', views.JobPDFHistoryView.as_view(), name='pdf_export_history'),
    path('pdf-exports/<int:pk>/download/', views.JobPDFDownloadView.as_view(), name='pdf_download'),
    path('pdf-exports/<int:pk>/delete/', views.JobPDFDeleteView.as_view(), name='pdf_delete'),
]