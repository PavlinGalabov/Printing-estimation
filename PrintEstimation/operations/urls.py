"""
Operations app URLs.
"""

from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    # path('', views.OperationListView.as_view(), name='list'),
    # path('create/', views.OperationCreateView.as_view(), name='create'),
    # path('<int:pk>/', views.OperationDetailView.as_view(), name='detail'),
    # path('<int:pk>/edit/', views.OperationUpdateView.as_view(), name='edit'),
    # path('<int:pk>/delete/', views.OperationDeleteView.as_view(), name='delete'),
    # path('categories/', views.CategoryListView.as_view(), name='categories'),
    # path('paper-types/', views.PaperTypeListView.as_view(), name='paper_types'),
    # path('paper-sizes/', views.PaperSizeListView.as_view(), name='paper_sizes'),
    # path('machines/', views.MachineListView.as_view(), name='machines'),
]