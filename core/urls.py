"""
Core App - URL Configuration
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Super Admin Routes
    path('super-admin/', views.SuperAdminDashboardView.as_view(), name='super_admin_dashboard'),
    path('super-admin/user-management/', views.UserManagementView.as_view(), name='user_management'),
    path('super-admin/user-management/create/', views.SuperAdminUserCreateView.as_view(), name='super_admin_user_create'),
    path('super-admin/user-management/<int:pk>/update/', views.SuperAdminUserUpdateView.as_view(), name='super_admin_user_update'),
    path('super-admin/user-management/<int:pk>/delete/', views.SuperAdminUserDeleteView.as_view(), name='super_admin_user_delete'),
    path('super-admin/users/<int:pk>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('super-admin/materials/', views.MaterialsManagementView.as_view(), name='materials_management'),
    path('super-admin/departments/', views.DepartmentManagementView.as_view(), name='department_management'),
    path('super-admin/departments/create/', views.DepartmentCreateUpdateView.as_view(), name='department_create'),
    path('super-admin/departments/<int:pk>/update/', views.DepartmentCreateUpdateView.as_view(), name='department_update'),
    path('super-admin/departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),
    path('super-admin/upload-items/', views.upload_items_excel, name='upload_items_excel'),
    
    # User Management (Regular Admin - legacy, now also accessible by super admin)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    
    # Department Management (Regular Admin - legacy, now also accessible by super admin)
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/update/', views.DepartmentCreateView.as_view(), name='department_update'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
