"""
Operations app URLs.
"""

from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    path('', views.OperationListView.as_view(), name='list'),
    path('create/', views.OperationCreateView.as_view(), name='create'),
    path('<int:pk>/', views.OperationDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.OperationUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.OperationDeleteView.as_view(), name='delete'),
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    
    # Paper Type URLs
    path('paper-types/', views.PaperTypeListView.as_view(), name='paper_types'),
    path('paper-types/create/', views.PaperTypeCreateView.as_view(), name='paper_type_create'),
    path('paper-types/<int:pk>/edit/', views.PaperTypeUpdateView.as_view(), name='paper_type_edit'),
    path('paper-types/<int:pk>/delete/', views.PaperTypeDeleteView.as_view(), name='paper_type_delete'),
    
    # Paper Size URLs  
    path('paper-sizes/', views.PaperSizeListView.as_view(), name='paper_sizes'),
    path('paper-sizes/create/', views.PaperSizeCreateView.as_view(), name='paper_size_create'),
    path('paper-sizes/<int:pk>/edit/', views.PaperSizeUpdateView.as_view(), name='paper_size_edit'),
    path('paper-sizes/<int:pk>/delete/', views.PaperSizeDeleteView.as_view(), name='paper_size_delete'),
    
    # API endpoints
    path('paper-sizes/<int:pk>/parent-info/', views.paper_size_parent_info, name='paper_size_parent_info'),
    
    # path('machines/', views.MachineListView.as_view(), name='machines'),
]