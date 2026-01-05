"""
Requisition App - URL Configuration
"""

from django.urls import path
from . import views

app_name = 'requisition'

urlpatterns = [
    # Dashboard views
    path('initiator/', views.InitiatorDashboardView.as_view(), name='initiator_dashboard'),
    path('hod/', views.HODDashboardView.as_view(), name='hod_dashboard'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Requisition CRUD
    path('', views.RequisitionListView.as_view(), name='list'),
    path('create/', views.RequisitionCreateView.as_view(), name='create'),
    path('api/create/', views.create_requisition_api, name='create_api'),
    path('<int:pk>/', views.RequisitionDetailView.as_view(), name='detail'),
    path('<int:pk>/print/', views.RequisitionPrintView.as_view(), name='print'),
    path('<int:pk>/update/', views.RequisitionUpdateView.as_view(), name='update'),
    path('<int:pk>/cancel/', views.cancel_requisition, name='cancel'),
    
    # HOD Workflow
    path('<int:pk>/hod-approval/', views.HODApprovalView.as_view(), name='hod_approval'),
    
    # Admin Workflow
    path('<int:pk>/issue/', views.IssueItemsView.as_view(), name='issue'),
    
    # API endpoints
    path('api/items/', views.get_item_suggestions, name='item_suggestions'),
    path('<int:pk>/api/update/', views.update_requisition_api, name='update_api'),
]
